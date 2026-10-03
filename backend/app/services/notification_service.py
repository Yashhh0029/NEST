import asyncio
import json
import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
import uuid
from fastapi import HTTPException, WebSocket, status
from sqlalchemy import or_
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
from app.services.safety_service import get_blocked_user_ids

logger = logging.getLogger(__name__)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on the Earth in kilometers."""
    r = 6371.0  # Earth's mean radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return r * c


class NotificationConnectionManager:
    """In-memory connection manager for real-time WebSocket notification delivery."""

    def __init__(self):
        self.active_connections: Dict[uuid.UUID, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: uuid.UUID):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: uuid.UUID):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

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
        # Pick helper's primary location or closest valid location
        helper_loc = (
            db.query(Location)
            .filter(Location.user_id == helper.id, Location.location_label == "Primary")
            .first()
        )
        if not helper_loc or helper_loc.latitude is None or helper_loc.longitude is None:
            helper_loc = (
                db.query(Location)
                .filter(
                    Location.user_id == helper.id,
                    Location.latitude.isnot(None),
                    Location.longitude.isnot(None),
                )
                .first()
            )

        if not helper_loc or helper_loc.latitude is None or helper_loc.longitude is None:
            continue

        dist_km = haversine_km(
            target_lat,
            target_lon,
            float(helper_loc.latitude),
            float(helper_loc.longitude),
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

        # Deliver via real-time WebSocket if recipient is actively connected
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
