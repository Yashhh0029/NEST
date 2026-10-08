import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
import uuid
from fastapi import HTTPException, WebSocket, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.location import Location
from app.models.notification import Notification, NotificationType
from app.models.request import Request
from app.models.request_location import RequestLocation
from app.models.user import User, UserRole
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
)
from app.services.google_maps_service import haversine_km
from app.services.safety_service import get_blocked_user_ids

logger = logging.getLogger(__name__)


class NotificationConnectionManager:
    """In-memory connection manager for real-time WebSocket notification delivery."""

    def __init__(self):
        self.active_connections: Dict[uuid.UUID, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: uuid.UUID):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        try:
            from app.services.presence_service import presence_service
            presence_service.record_user_connected(user_id, socket_ref=websocket)
        except Exception:
            pass

    def disconnect(self, websocket: WebSocket, user_id: uuid.UUID):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        try:
            from app.services.presence_service import presence_service
            presence_service.record_user_disconnected(user_id, socket_ref=websocket)
        except Exception:
            pass

    async def send_to_user(self, user_id: uuid.UUID, message_dict: dict):
        if user_id in self.active_connections:
            dead_sockets = []
            for ws in list(self.active_connections[user_id]):
                try:
                    await ws.send_text(json.dumps(message_dict))
                except Exception:
                    dead_sockets.append(ws)
            for ws in dead_sockets:
                self.disconnect(ws, user_id)


notification_manager = NotificationConnectionManager()

_test_online_overrides: Dict[uuid.UUID, bool] = {}


def set_user_online_override_for_testing(user_id: uuid.UUID, is_online: Optional[bool]) -> None:
    """Testing hook to explicitly simulate a user being online or offline."""
    if is_online is None:
        _test_online_overrides.pop(user_id, None)
    else:
        _test_online_overrides[user_id] = is_online
    from app.services.presence_service import presence_service
    presence_service.set_test_override(user_id, is_online)


def clear_test_online_overrides() -> None:
    """Clear all active testing presence overrides."""
    _test_online_overrides.clear()
    from app.services.presence_service import presence_service
    presence_service.clear_test_overrides()


def is_user_actively_online(user_id: uuid.UUID, conversation_id: Optional[uuid.UUID] = None) -> bool:
    """
    Determine if a user is currently actively present on the website or in a specific conversation room.
    If the user is active, in-app WebSocket messaging is used instead of email dispatch.
    """
    if user_id in _test_online_overrides:
        return _test_online_overrides[user_id]

    from app.services.presence_service import presence_service
    if conversation_id and presence_service.is_user_in_conversation(user_id, conversation_id):
        return True
    if presence_service.is_user_online(user_id):
        return True

    if user_id in notification_manager.active_connections and notification_manager.active_connections[user_id]:
        return True

    try:
        from app.api.ws_chat import manager as ws_chat_manager
        if conversation_id and ws_chat_manager.is_user_in_conversation(user_id, conversation_id):
            return True
        if ws_chat_manager.is_user_connected(user_id):
            return True
    except Exception:
        pass

    return False



def notify_nearby_helpers_for_request(
    db: Session,
    request: Request,
    radius_km: Optional[float] = None,
) -> List[Notification]:
    """
    Find community members/helpers whose stored location is within default radius (5 KM)
    from the request's TARGET_LOCATION and dispatch in-app notifications.

    Rules:
    - If the request has an explicit TARGET_LOCATION, use that exact target coordinates.
    - Do NOT fall back to the newcomer's current location when a valid target location exists.
    - Eligible helpers: role helper or both, active, email verified, not requester, not blocked.
    - Privacy: NEVER expose anyone's private exact coordinates or full address in notification.
    - Duplicate prevention: exactly one notification per eligible member per request.
    """
    effective_radius = (
        radius_km
        if radius_km is not None
        else settings.NEARBY_COMMUNITY_NOTIFICATION_RADIUS_KM
    )

    # 1. Resolve center coordinates using request TARGET_LOCATION semantics
    req_loc = (
        db.query(RequestLocation)
        .filter(RequestLocation.request_id == request.id)
        .first()
    )

    target_lat: Optional[float] = None
    target_lon: Optional[float] = None
    coarse_city = request.city
    coarse_area = request.area

    if (
        req_loc
        and req_loc.latitude is not None
        and req_loc.longitude is not None
    ):
        target_lat = float(req_loc.latitude)
        target_lon = float(req_loc.longitude)
        coarse_city = req_loc.city or coarse_city
        coarse_area = req_loc.area or coarse_area
    else:
        # Fallback to newcomer's primary profile location ONLY when no explicit target coordinates exist
        requester_loc = (
            db.query(Location)
            .filter(
                Location.user_id == request.user_id,
                Location.location_label == "Primary",
            )
            .first()
        )
        if not requester_loc:
            requester_loc = (
                db.query(Location)
                .filter(Location.user_id == request.user_id)
                .first()
            )

        if (
            requester_loc
            and requester_loc.latitude is not None
            and requester_loc.longitude is not None
        ):
            target_lat = float(requester_loc.latitude)
            target_lon = float(requester_loc.longitude)
            coarse_city = requester_loc.city or coarse_city
            coarse_area = requester_loc.area or coarse_area

    if target_lat is None or target_lon is None:
        logger.info(
            "Cannot dispatch nearby community notifications for request %s: no coordinates found.",
            request.id,
        )
        return []

    # 2. Safety & block exclusions (bidirectional blocks)
    blocked_ids = get_blocked_user_ids(db, request.user_id)
    excluded_ids: Set[uuid.UUID] = set(blocked_ids)
    excluded_ids.add(request.user_id)

    # 3. Query candidate helpers with valid stored locations
    candidate_helpers = (
        db.query(User)
        .join(Location, Location.user_id == User.id)
        .filter(
            User.is_active == True,
            User.email_verified == True,
            User.role.in_([UserRole.HELPER, UserRole.BOTH]),
            ~User.id.in_(excluded_ids),
            Location.latitude.isnot(None),
            Location.longitude.isnot(None),
        )
        .distinct()
        .all()
    )

    # 4. Extract clean category/need for notification message
    category_name = "local guidance"
    if request.extracted_requirements and isinstance(request.extracted_requirements, dict):
        raw_needs = request.extracted_requirements.get("needs", [])
        if isinstance(raw_needs, list) and raw_needs:
            first_n = raw_needs[0]
            if isinstance(first_n, dict):
                category_name = first_n.get("category") or first_n.get("item") or category_name
            elif isinstance(first_n, str):
                category_name = first_n
    elif request.intent and request.intent != "newcomer_assistance":
        category_name = request.intent.replace("_", " ")

    created_notifications: List[Notification] = []

    for helper in candidate_helpers:
        # Evaluate all locations with valid coordinates for the helper and find the closest to target
        helper_locations = (
            db.query(Location)
            .filter(
                Location.user_id == helper.id,
                Location.latitude.isnot(None),
                Location.longitude.isnot(None),
            )
            .all()
        )
        if not helper_locations:
            continue

        best_loc = min(
            helper_locations,
            key=lambda l: haversine_km(target_lat, target_lon, float(l.latitude), float(l.longitude)),
        )
        dist_km = haversine_km(
            target_lat,
            target_lon,
            float(best_loc.latitude),
            float(best_loc.longitude),
        )

        # Exact radius boundary check (e.g. <= 5.0 KM)
        if dist_km > effective_radius:
            continue

        # Duplicate protection: ensure helper was not already notified for this request
        already_notified = (
            db.query(Notification)
            .filter(
                Notification.user_id == helper.id,
                Notification.request_id == request.id,
                Notification.notification_type == NotificationType.NEARBY_HELP_REQUEST.value,
            )
            .first()
        )
        if already_notified:
            continue

        notification = Notification(
            user_id=helper.id,
            request_id=request.id,
            notification_type=NotificationType.NEARBY_HELP_REQUEST.value,
            title="Someone needs help nearby",
            message=f"A newcomer needs help in your area with {category_name.lower()}.",
            is_read=False,
            metadata_payload={
                "request_id": str(request.id),
                "category": category_name,
                "city": coarse_city,
                "area": coarse_area,
                "distance_km": round(dist_km, 1),
            },
        )
        db.add(notification)
        created_notifications.append(notification)

    if created_notifications:
        try:
            db.commit()
            for notif in created_notifications:
                db.refresh(notif)
        except Exception as exc:
            db.rollback()
            logger.warning("Failed to commit nearby community notifications: %s", exc)
            return []

        # Deliver via real-time WebSocket if recipient is actively connected;
        # deliver email notification asynchronously if helper is offline
        for notif in created_notifications:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(
                        notification_manager.send_to_user(
                            notif.user_id,
                            {
                                "type": "NEW_NOTIFICATION",
                                "notification": {
                                    "id": str(notif.id),
                                    "request_id": str(notif.request_id),
                                    "notification_type": notif.notification_type,
                                    "title": notif.title,
                                    "message": notif.message,
                                    "is_read": False,
                                    "request_status": request.status,
                                    "created_at": notif.created_at.isoformat(),
                                    "metadata_payload": notif.metadata_payload,
                                },
                            },
                        )
                    )
            except Exception:
                pass

            # Asynchronous email delivery if helper is NOT actively present on website
            try:
                if not is_user_actively_online(notif.user_id):
                    helper_user = db.query(User).filter(User.id == notif.user_id).first()
                    if helper_user and helper_user.email and helper_user.email_verified and helper_user.is_active:
                        from app.services.email_service import dispatch_email_async, render_nearby_request_email
                        frontend_base = settings.FRONTEND_URL.rstrip("/")
                        req_url = f"{frontend_base}/requests/{request.id}"
                        coarse_loc = f"{coarse_area or ''}, {coarse_city or ''}".strip(", ") or "your local area"
                        html_body, text_body = render_nearby_request_email(
                            helper_name=helper_user.name or "Neighbor",
                            request_title=request.raw_text[:120] if request.raw_text else f"Help with {category_name}",
                            coarse_location=coarse_loc,
                            category=category_name,
                            request_url=req_url,
                        )
                        idempotency_key = f"nearby_req_{request.id}_{helper_user.id}"
                        dispatch_email_async(
                            to_email=helper_user.email,
                            subject="New request near you — NEST",
                            html_body=html_body,
                            text_body=text_body,
                            idempotency_key=idempotency_key,
                            recipient_id=helper_user.id,
                            notification_type="nearby_request",
                            metadata_payload={
                                "request_id": str(request.id),
                                "category": category_name,
                                "city": coarse_city,
                                "area": coarse_area,
                            },
                        )
            except Exception as e_err:
                logger.warning(f"Failed to dispatch offline email notification to user {notif.user_id}: {e_err}")

    return created_notifications


def get_user_notifications(
    db: Session,
    user: User,
    limit: int = 50,
    skip: int = 0,
) -> NotificationListResponse:
    """Retrieve notifications for the authenticated user with unread count and state-aware status."""
    total = db.query(Notification).filter(Notification.user_id == user.id).count()
    unread_count = (
        db.query(Notification)
        .filter(Notification.user_id == user.id, Notification.is_read == False)
        .count()
    )

    records = (
        db.query(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    items = []
    for r in records:
        req_status = r.request.status if r.request else None
        dist = (r.metadata_payload or {}).get("distance_km") if isinstance(r.metadata_payload, dict) else None
        item = NotificationResponse(
            id=r.id,
            user_id=r.user_id,
            request_id=r.request_id,
            notification_type=r.notification_type,
            title=r.title,
            message=r.message,
            is_read=r.is_read,
            read_at=r.read_at,
            metadata_payload=r.metadata_payload,
            distance_km=float(dist) if dist is not None else None,
            request_status=req_status,
            created_at=r.created_at,
        )
        items.append(item)

    return NotificationListResponse(
        items=items,
        total=total,
        unread_count=unread_count,
    )


def mark_notification_as_read(
    db: Session,
    user: User,
    notification_id: uuid.UUID,
) -> Notification:
    """Mark single notification as read, enforcing strict user ownership."""
    notif = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user.id)
        .first()
    )
    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )

    if not notif.is_read:
        notif.is_read = True
        notif.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notif)

    return notif


def mark_all_notifications_as_read(
    db: Session,
    user: User,
) -> int:
    """Mark all unread notifications as read for current user."""
    now = datetime.now(timezone.utc)
    updated = (
        db.query(Notification)
        .filter(Notification.user_id == user.id, Notification.is_read == False)
        .update({"is_read": True, "read_at": now}, synchronize_session=False)
    )
    db.commit()
    return updated


def get_user_unread_count(
    db: Session,
    user: User,
) -> int:
    """Get total unread notification count for badge indicator."""
    return (
        db.query(Notification)
        .filter(Notification.user_id == user.id, Notification.is_read == False)
        .count()
    )
