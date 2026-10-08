import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set, Tuple
import uuid
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.chat import ConversationPresenceResponse

logger = logging.getLogger(__name__)

# Configurable server-side presence TTL
PRESENCE_TTL_SECONDS: int = 60


class PresenceService:
    """
    Real-time Presence Service for NEST users.
    Distinguishes actual user presence (online/offline/last_seen) from transport/socket state.
    Enforces server-side heartbeat TTL and maintains last_seen_at timestamps in database.
    """

    def __init__(self):
        # Maps user_id -> datetime of last received heartbeat/message
        self._last_heartbeat: Dict[uuid.UUID, datetime] = {}
        # Maps user_id -> set of active connection identifiers/sockets
        self._user_sockets: Dict[uuid.UUID, Set[Any]] = {}
        # Maps user_id -> set of active conversation_ids the user is currently viewing
        self._user_conversations: Dict[uuid.UUID, Set[uuid.UUID]] = {}
        # Test overrides for unit & E2E tests
        self._test_overrides: Dict[uuid.UUID, bool] = {}

    def set_test_override(self, user_id: uuid.UUID, is_online: Optional[bool]) -> None:
        """Testing hook to explicitly simulate a user being online or offline."""
        if is_online is None:
            self._test_overrides.pop(user_id, None)
        else:
            self._test_overrides[user_id] = is_online

    def clear_test_overrides(self) -> None:
        """Clear all active testing presence overrides."""
        self._test_overrides.clear()

    def record_user_connected(
        self,
        user_id: uuid.UUID,
        conversation_id: Optional[uuid.UUID] = None,
        socket_ref: Optional[Any] = None,
        db: Optional[Session] = None,
    ) -> None:
        """Record an active authenticated WebSocket connection."""
        now = datetime.now(timezone.utc)
        self._last_heartbeat[user_id] = now

        if user_id not in self._user_sockets:
            self._user_sockets[user_id] = set()
        if socket_ref is not None:
            self._user_sockets[user_id].add(socket_ref)
        else:
            # Fallback placeholder to track at least one active connection
            self._user_sockets[user_id].add(id(now))

        if conversation_id:
            if user_id not in self._user_conversations:
                self._user_conversations[user_id] = set()
            self._user_conversations[user_id].add(conversation_id)

        # Update last_seen_at in DB
        if db:
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    user.last_seen_at = now
                    db.commit()
            except Exception as e:
                logger.debug("Failed to update last_seen_at on connect for %s: %s", user_id, e)
                try:
                    db.rollback()
                except Exception:
                    pass

    def record_user_heartbeat(
        self,
        user_id: uuid.UUID,
        db: Optional[Session] = None,
    ) -> None:
        """Update last heartbeat timestamp on ping/activity."""
        now = datetime.now(timezone.utc)
        self._last_heartbeat[user_id] = now
        if db:
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    user.last_seen_at = now
                    db.commit()
            except Exception as e:
                logger.debug("Failed to update last_seen_at on heartbeat for %s: %s", user_id, e)
                try:
                    db.rollback()
                except Exception:
                    pass

    def record_user_disconnected(
        self,
        user_id: uuid.UUID,
        conversation_id: Optional[uuid.UUID] = None,
        socket_ref: Optional[Any] = None,
        db: Optional[Session] = None,
    ) -> None:
        """Record socket disconnection and clean up conversation membership."""
        now = datetime.now(timezone.utc)
        self._last_heartbeat[user_id] = now

        if user_id in self._user_sockets:
            if socket_ref is not None:
                self._user_sockets[user_id].discard(socket_ref)
            if not self._user_sockets[user_id] or socket_ref is None:
                self._user_sockets.pop(user_id, None)

        if conversation_id and user_id in self._user_conversations:
            self._user_conversations[user_id].discard(conversation_id)
            if not self._user_conversations[user_id]:
                self._user_conversations.pop(user_id, None)

        if db:
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    user.last_seen_at = now
                    db.commit()
            except Exception as e:
                logger.debug("Failed to update last_seen_at on disconnect for %s: %s", user_id, e)
                try:
                    db.rollback()
                except Exception:
                    pass

    def is_user_online(self, user_id: uuid.UUID) -> bool:
        """
        Check whether user is currently online.
        A user is online if and only if they have at least one active socket
        AND their last heartbeat was within PRESENCE_TTL_SECONDS.
        """
        if user_id in self._test_overrides:
            return self._test_overrides[user_id]

        active_sockets = self._user_sockets.get(user_id)
        if not active_sockets:
            return False

        last_beat = self._last_heartbeat.get(user_id)
        if not last_beat:
            return False

        now = datetime.now(timezone.utc)
        diff_seconds = (now - last_beat).total_seconds()
        return diff_seconds <= PRESENCE_TTL_SECONDS

    def is_user_in_conversation(self, user_id: uuid.UUID, conversation_id: uuid.UUID) -> bool:
        """Check whether user is online and currently actively viewing this specific conversation."""
        if user_id in self._test_overrides:
            return self._test_overrides[user_id]

        if not self.is_user_online(user_id):
            return False

        return conversation_id in self._user_conversations.get(user_id, set())

    def get_user_presence(
        self,
        user_id: uuid.UUID,
        db: Optional[Session] = None,
    ) -> Tuple[bool, Optional[datetime]]:
        """
        Get presence tuple: (is_online, last_seen_at).
        Returns exact timestamp when offline.
        """
        is_online = self.is_user_online(user_id)
        last_seen = self._last_heartbeat.get(user_id)

        if not last_seen and db:
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user and user.last_seen_at:
                    last_seen = user.last_seen_at
            except Exception:
                pass

        return is_online, last_seen

    def get_conversation_presence(
        self,
        db: Session,
        conversation_id: uuid.UUID,
        current_user_id: uuid.UUID,
    ) -> ConversationPresenceResponse:
        """
        Get the partner's presence for a conversation that current_user has access to.
        Enforces conversation membership security.
        """
        from app.services import chat_service
        conversation, connection = chat_service.verify_conversation_access(
            db, conversation_id, current_user_id
        )

        partner_id = (
            connection.helper_id
            if current_user_id == connection.requester_id
            else connection.requester_id
        )

        is_online, last_seen = self.get_user_presence(partner_id, db=db)

        return ConversationPresenceResponse(
            conversation_id=conversation.id,
            partner_id=partner_id,
            is_online=is_online,
            last_seen_at=last_seen,
        )


presence_service = PresenceService()
