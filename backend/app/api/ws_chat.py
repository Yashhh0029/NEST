import json
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Set
import uuid
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session
from app.core.security import decode_access_token
from app.db.database import get_db
from app.models.user import User
from app.schemas.chat import MessageCreate
from app.services import chat_service
from app.services.safety_service import is_blocked_bidirectional

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket Chat"])


class ConnectionManager:
    def __init__(self):
        # Maps conversation_id -> set of active WebSockets
        self.rooms: Dict[uuid.UUID, Set[WebSocket]] = {}
        # Maps user_id -> set of active WebSockets
        self.user_sockets: Dict[uuid.UUID, Set[WebSocket]] = {}
        # Maps conversation_id -> set of active user_ids in this conversation
        self.conversation_users: Dict[uuid.UUID, Set[uuid.UUID]] = {}
        # Maps websocket -> (conversation_id, user_id)
        self.socket_meta: Dict[WebSocket, tuple[uuid.UUID, uuid.UUID]] = {}

    async def connect(self, websocket: WebSocket, conversation_id: uuid.UUID, user_id: Optional[uuid.UUID] = None):
        await websocket.accept()
        if conversation_id not in self.rooms:
            self.rooms[conversation_id] = set()
        self.rooms[conversation_id].add(websocket)

        if user_id:
            if user_id not in self.user_sockets:
                self.user_sockets[user_id] = set()
            self.user_sockets[user_id].add(websocket)

            if conversation_id not in self.conversation_users:
                self.conversation_users[conversation_id] = set()
            self.conversation_users[conversation_id].add(user_id)

            self.socket_meta[websocket] = (conversation_id, user_id)

    def disconnect(self, websocket: WebSocket, conversation_id: uuid.UUID):
        meta = self.socket_meta.pop(websocket, None)
        user_id = meta[1] if meta else None

        if conversation_id in self.rooms:
            self.rooms[conversation_id].discard(websocket)
            if not self.rooms[conversation_id]:
                del self.rooms[conversation_id]

        if user_id and user_id in self.user_sockets:
            self.user_sockets[user_id].discard(websocket)
            if not self.user_sockets[user_id]:
                del self.user_sockets[user_id]

        if conversation_id in self.conversation_users:
            active_uids = {self.socket_meta[ws][1] for ws in self.rooms.get(conversation_id, set()) if ws in self.socket_meta}
            if active_uids:
                self.conversation_users[conversation_id] = active_uids
            else:
                del self.conversation_users[conversation_id]

    def is_user_in_conversation(self, user_id: uuid.UUID, conversation_id: uuid.UUID) -> bool:
        return user_id in self.conversation_users.get(conversation_id, set())

    def is_user_connected(self, user_id: uuid.UUID) -> bool:
        return bool(self.user_sockets.get(user_id))

    async def broadcast(self, conversation_id: uuid.UUID, message_dict: dict, exclude: Optional[WebSocket] = None):
        if conversation_id in self.rooms:
            disconnected_sockets = set()
            for ws in self.rooms[conversation_id]:
                if exclude is not None and ws == exclude:
                    continue
                try:
                    await ws.send_text(json.dumps(message_dict))
                except Exception:
                    disconnected_sockets.add(ws)
            for ws in disconnected_sockets:
                self.disconnect(ws, conversation_id)


manager = ConnectionManager()


@router.websocket("/ws/conversations/{conversation_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    conversation_id: uuid.UUID,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Real-time WebSocket endpoint for conversation messages.
    Authenticates via JWT token query parameter.
    Validates participant status and connection active state before allowing connection.
    Persists all messages to PostgreSQL before broadcasting.
    Never logs JWT tokens.
    """
    # 1. Authenticate token
    if not token:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Authentication token is required.",
        )
        return

    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid or expired authentication credentials.",
        )
        return

    try:
        user_id = uuid.UUID(payload.get("sub"))
    except (ValueError, TypeError):
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid user identifier.",
        )
        return

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="User account is inactive or not found.",
        )
        return

    # 2. Verify conversation authorization & ACTIVE connection status
    try:
        conversation, connection = chat_service.verify_conversation_access(
            db,
            conversation_id,
            user_id,
        )
    except Exception as exc:
        err_msg = getattr(exc, "detail", "Access to conversation denied.")
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason=err_msg,
        )
        return

    # Check bidirectional block at connection time
    if is_blocked_bidirectional(db, connection.requester_id, connection.helper_id):
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Action not permitted due to safety restrictions.",
        )
        return

    # 3. Accept socket connection
    await manager.connect(websocket, conversation.id, user_id)
    from app.services.presence_service import presence_service
    presence_service.record_user_connected(user_id, conversation_id=conversation.id, socket_ref=websocket, db=db)
    partner_id = connection.helper_id if user_id == connection.requester_id else connection.requester_id

    try:
        # Acknowledge connection
        await websocket.send_text(
            json.dumps({
                "type": "connected",
                "conversation_id": str(conversation.id),
                "user_id": str(user_id),
            })
        )

        # Dispatch real presence of the other conversation participant
        partner_is_online, partner_last_seen = presence_service.get_user_presence(partner_id, db=db)
        await websocket.send_text(
            json.dumps({
                "type": "presence",
                "user_id": str(partner_id),
                "is_online": partner_is_online,
                "last_seen_at": partner_last_seen.isoformat() if partner_last_seen else None,
            })
        )

        # Broadcast current user's presence to the room
        await manager.broadcast(
            conversation.id,
            {
                "type": "presence",
                "user_id": str(user_id),
                "is_online": True,
                "last_seen_at": datetime.now(timezone.utc).isoformat(),
            },
            exclude=websocket,
        )

        while True:
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)
            except Exception:
                await websocket.send_text(
                    json.dumps({"type": "error", "detail": "Invalid JSON format."})
                )
                continue

            msg_type = data.get("type", "message")
            if msg_type == "ping":
                presence_service.record_user_heartbeat(user_id, db=db)
                await websocket.send_text(json.dumps({"type": "pong"}))
                continue

            if msg_type == "message":
                presence_service.record_user_heartbeat(user_id, db=db)
                raw_content = data.get("content", "")
                if not isinstance(raw_content, str) or not raw_content.strip():
                    await websocket.send_text(
                        json.dumps({
                            "type": "error",
                            "detail": "Message content cannot be empty.",
                        })
                    )
                    continue

                if len(raw_content.strip()) > 2000:
                    await websocket.send_text(
                        json.dumps({
                            "type": "error",
                            "detail": "Message exceeds maximum length of 2000 characters.",
                        })
                    )
                    continue

                # 4. CHECK BLOCK RELATIONSHIP BEFORE ACCEPTING MESSAGE
                if is_blocked_bidirectional(db, connection.requester_id, connection.helper_id):
                    await websocket.send_text(
                        json.dumps({
                            "type": "error",
                            "detail": "Action not permitted due to safety restrictions.",
                        })
                    )
                    await websocket.close(
                        code=status.WS_1008_POLICY_VIOLATION,
                        reason="Action not permitted due to safety restrictions.",
                    )
                    break

                # 5. PERSIST TO DATABASE BEFORE BROADCAST
                try:
                    persisted_msg = chat_service.send_message(
                        db,
                        conversation.id,
                        user_id,
                        MessageCreate(content=raw_content.strip()),
                    )
                except Exception as exc:
                    err_detail = getattr(exc, "detail", "Failed to save message.")
                    await websocket.send_text(
                        json.dumps({"type": "error", "detail": err_detail})
                    )
                    continue

                # 5. Broadcast persisted message to conversation room
                msg_response = chat_service.format_message_response(persisted_msg)
                broadcast_payload = {
                    "type": "message",
                    "message": {
                        "id": str(msg_response.id),
                        "conversation_id": str(msg_response.conversation_id),
                        "sender_id": str(msg_response.sender_id),
                        "sender_name": msg_response.sender_name,
                        "content": msg_response.content,
                        "is_read": msg_response.is_read,
                        "created_at": msg_response.created_at.isoformat(),
                        "updated_at": msg_response.updated_at.isoformat(),
                        "edited_at": (
                            msg_response.edited_at.isoformat()
                            if msg_response.edited_at
                            else None
                        ),
                        "deleted_at": (
                            msg_response.deleted_at.isoformat()
                            if msg_response.deleted_at
                            else None
                        ),
                    },
                }
                await manager.broadcast(conversation.id, broadcast_payload)

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("WebSocket error for conversation %s: %s", conversation.id, str(exc))
    finally:
        manager.disconnect(websocket, conversation.id)
        presence_service.record_user_disconnected(user_id, conversation_id=conversation.id, socket_ref=websocket, db=db)
        is_still_online = presence_service.is_user_online(user_id)
        _, my_last_seen = presence_service.get_user_presence(user_id, db=db)
        await manager.broadcast(
            conversation.id,
            {
                "type": "presence",
                "user_id": str(user_id),
                "is_online": is_still_online,
                "last_seen_at": my_last_seen.isoformat() if my_last_seen else None,
            },
            exclude=websocket,
        )
