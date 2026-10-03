import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
    UnreadCountResponse,
)
from app.services.notification_service import (
    get_user_notifications,
    get_user_unread_count,
    mark_all_notifications_as_read,
    mark_notification_as_read,
    notification_manager,
)

router = APIRouter(prefix="/notifications", tags=["In-App Notifications"])


@router.get(
    "",
    response_model=NotificationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List notifications for authenticated user",
    description="Returns notifications in descending chronological order, with live request status and unread count.",
)
def list_notifications(
    limit: int = Query(50, ge=1, le=100, description="Max notifications to retrieve"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationListResponse:
    """Retrieve user notifications."""
    return get_user_notifications(db, current_user, limit=limit, skip=skip)


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    status_code=status.HTTP_200_OK,
    summary="Get unread notification count",
    description="Returns total unread notifications for badge counter in UI.",
)
def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UnreadCountResponse:
    """Return total unread count."""
    count = get_user_unread_count(db, current_user)
    return UnreadCountResponse(unread_count=count)


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark single notification as read",
    description="Updates is_read=True and records read_at timestamp.",
)
def mark_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationResponse:
    """Mark a notification as read."""
    notif = mark_notification_as_read(db, current_user, notification_id)
    dist = (notif.metadata_payload or {}).get("distance_km") if isinstance(notif.metadata_payload, dict) else None
    return NotificationResponse(
        id=notif.id,
        user_id=notif.user_id,
        request_id=notif.request_id,
        notification_type=notif.notification_type,
        title=notif.title,
        message=notif.message,
        is_read=notif.is_read,
        read_at=notif.read_at,
        metadata_payload=notif.metadata_payload,
        distance_km=float(dist) if dist is not None else None,
        request_status=notif.request.status if notif.request else None,
        created_at=notif.created_at,
    )


@router.post(
    "/mark-all-read",
    status_code=status.HTTP_200_OK,
    summary="Mark all user notifications as read",
    description="Marks all unread notifications for current user as read.",
)
def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Mark all notifications as read."""
    updated = mark_all_notifications_as_read(db, current_user)
    return {"message": "All notifications marked as read.", "count": updated, "marked_count": updated}


@router.websocket("/ws")
async def notifications_websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Real-time WebSocket endpoint for instant in-app notification delivery.
    Authenticates client using bearer JWT token passed via query parameter.
    """
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id_str = payload.get("sub")
    if not user_id_str:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        user_id = uuid.UUID(user_id_str)
    except (ValueError, TypeError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active or not user.email_verified:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await notification_manager.connect(websocket, user.id)
    try:
        # Keep socket open and reply to heartbeat pings
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        notification_manager.disconnect(websocket, user.id)
    except Exception:
        notification_manager.disconnect(websocket, user.id)
