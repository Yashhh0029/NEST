from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, List, Optional
import urllib.parse
import uuid

from fastapi import HTTPException, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.connection import Connection, ConnectionStatus
from app.models.profile import Profile
from app.models.request import Request
from app.models.session import AssistanceSession, SessionModality, SessionStatus
from app.models.user import User
from app.schemas.session import (
    AssistanceSessionResponse,
    SessionActionPayload,
    SessionCreatePayload,
    SessionListResponse,
    SessionModalityEnum,
    SessionReschedulePayload,
)
from app.services.availability_service import (
    get_derived_capacity_status,
    validate_iana_timezone,
)
from app.services.google_maps_service import google_maps_service
from app.services.matching_service import haversine_km
from app.services.safety_service import is_blocked_bidirectional

logger = logging.getLogger(__name__)

ALLOWED_PUBLIC_VENUE_TYPES = {
    "cafe",
    "coffee_shop",
    "library",
    "coworking_space",
    "book_store",
    "community_center",
    "transit_station",
    "subway_station",
    "train_station",
    "bus_station",
    "shopping_mall",
    "university",
    "college",
    "civic_center",
    "park",
    "restaurant",
    "bakery",
    "fast_food_restaurant",
}

DISALLOWED_VENUE_TYPES = {
    "lodging",
    "hotel",
    "motel",
    "bed_and_breakfast",
    "residence",
    "premise",
    "subpremise",
    "night_club",
    "bar",
    "liquor_store",
}


def validate_remote_url(url: Optional[str]) -> str:
    """
    Validates that a meeting URL uses secure HTTPS and does not target localhost/internal networks.
    """
    if not url or not url.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Valid HTTPS meeting URL is required for remote sessions.",
        )

    clean_url = url.strip()
    if not clean_url.startswith("https://"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Remote meeting URL must use a secure HTTPS protocol (e.g. https://meet.google.com/...).",
        )

    parsed = urllib.parse.urlparse(clean_url)
    hostname = (parsed.hostname or "").lower()

    disallowed_hosts = {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
        "169.254.169.254",
        "metadata.google.internal",
    }
    if (
        hostname in disallowed_hosts
        or hostname.startswith("192.168.")
        or hostname.startswith("10.")
        or hostname.startswith("172.16.")
        or hostname.startswith("172.17.")
        or hostname.startswith("172.18.")
        or hostname.startswith("172.19.")
        or hostname.startswith("172.2")
        or hostname.startswith("172.3")
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Localhost and internal private network URLs are prohibited for remote sessions.",
        )

    if not hostname or "." not in hostname:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid remote meeting URL hostname.",
        )

    return clean_url


def validate_public_venue(
    place_id: str,
    request_obj: Optional[Request] = None,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Validates that a meeting place is an approved public venue using Google Places.
    Enforces category allowlist, rejects private/nightlife venues, and enforces the 25km radius rule.
    """
    if not place_id or not place_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="meeting_place_id is required for in-person sessions.",
        )

    venue = google_maps_service.get_venue_details(place_id.strip())
    if not venue:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Google Places verification is unavailable or invalid place ID. Please select remote session modality or retry.",
        )

    types = set(venue.get("types", []))
    primary_type = venue.get("primary_type")
    if primary_type:
        types.add(primary_type)

    if types & DISALLOWED_VENUE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Selected venue is not permitted (lodging, residential, or nightlife venue).",
        )

    if not (types & ALLOWED_PUBLIC_VENUE_TYPES):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Selected venue is not an approved public meeting location.",
        )

    # 25 km distance validation from request target location
    req_lat = None
    req_lon = None
    if request_obj and db:
        from app.models.request_location import RequestLocation
        loc_rec = db.query(RequestLocation).filter(RequestLocation.request_id == request_obj.id).first()
        if loc_rec:
            req_lat = loc_rec.latitude
            req_lon = loc_rec.longitude
    elif request_obj:
        if getattr(request_obj, "target_location", None):
            req_lat = request_obj.target_location.latitude
            req_lon = request_obj.target_location.longitude
        elif hasattr(request_obj, "latitude"):
            req_lat = getattr(request_obj, "latitude", None)
            req_lon = getattr(request_obj, "longitude", None)

    if req_lat is None and request_obj:
        if db:
            from app.models.location import Location
            user_loc = db.query(Location).filter(Location.user_id == request_obj.user_id, Location.location_label == "Primary").first()
            if user_loc and user_loc.latitude is not None:
                req_lat = user_loc.latitude
                req_lon = user_loc.longitude
        if req_lat is None and request_obj.city:
            c_low = request_obj.city.lower()
            if "bengaluru" in c_low or "bangalore" in c_low:
                req_lat, req_lon = 12.9716, 77.5946
            elif "pune" in c_low:
                req_lat, req_lon = 18.5204, 73.8567
            elif "mumbai" in c_low:
                req_lat, req_lon = 19.0760, 72.8777
            elif "delhi" in c_low:
                req_lat, req_lon = 28.6139, 77.2090

    if (
        req_lat is not None
        and req_lon is not None
        and venue.get("latitude") is not None
        and venue.get("longitude") is not None
    ):
        dist = haversine_km(
            req_lat,
            req_lon,
            venue["latitude"],
            venue["longitude"],
        )
        if dist > 25.0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Selected meeting venue is {dist:.1f} km away, exceeding the approved 25 km radius from the request target location.",
            )

    return venue


def check_session_conflicts(
    db: Session,
    user_ids: List[uuid.UUID],
    start_time: datetime,
    end_time: datetime,
    exclude_session_id: Optional[uuid.UUID] = None,
) -> None:
    """
    Checks for overlapping CONFIRMED or RESCHEDULE_PROPOSED sessions for any of the participants.
    Locks the User rows in sorted order to guarantee deterministic database-level concurrency protection.
    """
    sorted_user_strs = sorted(set(str(uid) for uid in user_ids))
    for u_str in sorted_user_strs:
        db.query(User).filter(User.id == uuid.UUID(u_str)).with_for_update().first()

    query = db.query(AssistanceSession).filter(
        AssistanceSession.status.in_([
            SessionStatus.CONFIRMED.value,
            SessionStatus.RESCHEDULE_PROPOSED.value,
        ]),
        or_(
            AssistanceSession.proposer_id.in_(user_ids),
            AssistanceSession.recipient_id.in_(user_ids),
        ),
        AssistanceSession.scheduled_start < end_time,
        AssistanceSession.scheduled_end > start_time,
    )

    if exclude_session_id:
        query = query.filter(AssistanceSession.id != exclude_session_id)

    conflict = query.first()
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Time slot conflicts with an existing confirmed session.",
        )


def format_session_response(
    session: AssistanceSession,
    current_user_id: uuid.UUID,
) -> AssistanceSessionResponse:
    """
    Hydrates an AssistanceSession into the response schema with user-specific permissions.
    Preserves remote URL privacy until session is confirmed.
    """
    is_my_proposal = session.proposer_id == current_user_id
    is_recipient = session.recipient_id == current_user_id
    is_participant = is_my_proposal or is_recipient

    can_accept = is_recipient and session.status in [
        SessionStatus.PROPOSED.value,
        SessionStatus.RESCHEDULE_PROPOSED.value,
    ]
    can_reschedule = is_participant and session.status in [
        SessionStatus.CONFIRMED.value,
        SessionStatus.PROPOSED.value,
    ]
    can_cancel = is_participant and session.status in [
        SessionStatus.PROPOSED.value,
        SessionStatus.RESCHEDULE_PROPOSED.value,
        SessionStatus.CONFIRMED.value,
    ]

    can_complete = False
    if session.status == SessionStatus.CONFIRMED.value and is_participant:
        conn = session.connection
        if conn:
            if current_user_id == conn.requester_id and not session.requester_completed_at:
                can_complete = True
            elif current_user_id == conn.helper_id and not session.helper_completed_at:
                can_complete = True

    # Remote meeting URL remains hidden from recipient until session is confirmed
    meeting_url_view = session.meeting_url
    if session.modality == SessionModality.REMOTE.value:
        if session.status == SessionStatus.PROPOSED.value and not is_my_proposal:
            meeting_url_view = None

    return AssistanceSessionResponse(
        id=session.id,
        connection_id=session.connection_id,
        request_id=session.request_id,
        proposer_id=session.proposer_id,
        recipient_id=session.recipient_id,
        title=session.title,
        description=session.description,
        need_category=session.need_category,
        modality=session.modality,
        meeting_place_id=session.meeting_place_id,
        meeting_place_name=session.meeting_place_name,
        meeting_formatted_address=session.meeting_formatted_address,
        meeting_latitude=session.meeting_latitude,
        meeting_longitude=session.meeting_longitude,
        meeting_url=meeting_url_view,
        scheduled_start=session.scheduled_start,
        scheduled_end=session.scheduled_end,
        duration_minutes=session.duration_minutes,
        session_timezone=session.session_timezone,
        status=session.status,
        status_reason=session.status_reason,
        previous_scheduled_start=session.previous_scheduled_start,
        previous_scheduled_end=session.previous_scheduled_end,
        reschedule_count=session.reschedule_count,
        requester_completed_at=session.requester_completed_at,
        helper_completed_at=session.helper_completed_at,
        is_my_proposal=is_my_proposal,
        can_accept=can_accept,
        can_reschedule=can_reschedule,
        can_cancel=can_cancel,
        can_complete=can_complete,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def propose_session(
    current_user: User,
    payload: SessionCreatePayload,
    db: Session,
) -> AssistanceSessionResponse:
    """
    Creates a new session proposal between accepted connection partners.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Suspended accounts cannot propose assistance sessions.",
        )

    if current_user.id == payload.recipient_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot propose a session to yourself.",
        )

    # 1. Block check
    if is_blocked_bidirectional(db, current_user.id, payload.recipient_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot schedule session with this user due to safety restrictions.",
        )

    # 2. Connection check with strict integrity
    connection = (
        db.query(Connection)
        .filter(
            Connection.request_id == payload.request_id,
            or_(
                and_(Connection.requester_id == current_user.id, Connection.helper_id == payload.recipient_id),
                and_(Connection.helper_id == current_user.id, Connection.requester_id == payload.recipient_id),
            ),
        )
        .first()
    )
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accepted connection between participants for this request was not found.",
        )

    if connection.status != ConnectionStatus.ACCEPTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assistance sessions can only be scheduled for accepted connections.",
        )

    # 3. Recipient active check
    recipient = db.query(User).filter(User.id == payload.recipient_id).first()
    if not recipient or not recipient.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Recipient account is inactive or suspended.",
        )

    # Timezone resolution: payload timezone overrides profile default
    tz = validate_iana_timezone(payload.session_timezone or "UTC")

    now_utc = datetime.now(timezone.utc)
    start_dt = payload.scheduled_start
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)

    if start_dt <= now_utc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scheduled start time must be in the future.",
        )

    end_dt = start_dt + timedelta(minutes=payload.duration_minutes)

    # 4. Canonical helper capacity check
    canonical_helper_id = connection.helper_id
    cap_status, active_count = get_derived_capacity_status(db, canonical_helper_id)
    if cap_status == "NOT_ACCEPTING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Helper is currently not accepting new assistance sessions.",
        )
    elif cap_status == "AT_CAPACITY":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Helper has reached their maximum weekly session capacity.",
        )

    # 5. Modality & Venue validation
    meeting_place_name = None
    meeting_formatted_address = None
    meeting_latitude = None
    meeting_longitude = None
    meeting_url = None

    if payload.modality == SessionModalityEnum.IN_PERSON:
        venue = validate_public_venue(payload.meeting_place_id, connection.request, db=db)
        meeting_place_name = venue.get("name")
        meeting_formatted_address = venue.get("formatted_address")
        meeting_latitude = venue.get("latitude")
        meeting_longitude = venue.get("longitude")
    else:
        meeting_url = validate_remote_url(payload.meeting_url)

    # 6. Concurrency & conflict check on both canonical participants
    check_session_conflicts(db, [connection.requester_id, connection.helper_id], start_dt, end_dt)

    session = AssistanceSession(
        id=uuid.uuid4(),
        connection_id=connection.id,
        request_id=payload.request_id,
        proposer_id=current_user.id,
        recipient_id=payload.recipient_id,
        title=payload.title.strip(),
        description=payload.description.strip() if payload.description else None,
        need_category=payload.need_category.strip() if payload.need_category else None,
        modality=payload.modality.value,
        meeting_place_id=payload.meeting_place_id.strip() if payload.meeting_place_id else None,
        meeting_place_name=meeting_place_name,
        meeting_formatted_address=meeting_formatted_address,
        meeting_latitude=meeting_latitude,
        meeting_longitude=meeting_longitude,
        meeting_url=meeting_url,
        scheduled_start=start_dt,
        scheduled_end=end_dt,
        duration_minutes=payload.duration_minutes,
        session_timezone=tz,
        status=SessionStatus.PROPOSED.value,
        reschedule_count=0,
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return format_session_response(session, current_user.id)


def accept_session(
    session_id: uuid.UUID,
    current_user: User,
    db: Session,
) -> AssistanceSessionResponse:
    """
    Accepts a proposed session. Only the designated recipient can accept.
    Anti-self-accept strictly enforced.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Suspended accounts cannot accept sessions.",
        )

    session = db.query(AssistanceSession).filter(AssistanceSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    if current_user.id != session.recipient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the recipient can accept this session proposal.",
        )

    if session.status not in [SessionStatus.PROPOSED.value, SessionStatus.RESCHEDULE_PROPOSED.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot accept session with status '{session.status}'.",
        )

    if is_blocked_bidirectional(db, session.proposer_id, session.recipient_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot accept session due to active safety restrictions.",
        )

    # Concurrency lock & conflict re-check before confirming
    conn = session.connection
    helper_id = conn.helper_id if conn else session.recipient_id
    requester_id = conn.requester_id if conn else session.proposer_id
    check_session_conflicts(
        db,
        [requester_id, helper_id],
        session.scheduled_start,
        session.scheduled_end,
        exclude_session_id=session.id,
    )

    # Re-verify helper capacity before confirming
    cap_status, _ = get_derived_capacity_status(db, helper_id)
    if cap_status == "NOT_ACCEPTING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Helper is currently not accepting new assistance sessions.",
        )
    elif cap_status == "AT_CAPACITY":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Helper has reached their maximum weekly session capacity.",
        )

    session.status = SessionStatus.CONFIRMED.value
    session.status_reason = None
    session.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(session)
    return format_session_response(session, current_user.id)


def decline_session(
    session_id: uuid.UUID,
    current_user: User,
    payload: SessionActionPayload,
    db: Session,
) -> AssistanceSessionResponse:
    """
    Declines a proposed session or reschedule proposal. Only the recipient can decline.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Suspended accounts cannot decline sessions.",
        )

    session = db.query(AssistanceSession).filter(AssistanceSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    if current_user.id != session.recipient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the recipient can decline this session proposal.",
        )

    if session.status not in [SessionStatus.PROPOSED.value, SessionStatus.RESCHEDULE_PROPOSED.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot decline session with status '{session.status}'.",
        )

    session.status = SessionStatus.DECLINED.value
    session.status_reason = payload.reason.strip() if payload.reason else "Declined by recipient"
    session.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(session)
    return format_session_response(session, current_user.id)


def cancel_session(
    session_id: uuid.UUID,
    current_user: User,
    payload: SessionActionPayload,
    db: Session,
) -> AssistanceSessionResponse:
    """
    Cancels a session. Either participant can cancel if PROPOSED, RESCHEDULE_PROPOSED, or CONFIRMED.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Suspended accounts cannot cancel sessions.",
        )

    session = db.query(AssistanceSession).filter(AssistanceSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    if current_user.id not in [session.proposer_id, session.recipient_id]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only session participants can cancel this session.",
        )

    if session.status in [SessionStatus.CANCELLED.value, SessionStatus.DECLINED.value, SessionStatus.COMPLETED.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel session with status '{session.status}'.",
        )

    session.status = SessionStatus.CANCELLED.value
    session.status_reason = payload.reason.strip() if payload.reason else "Cancelled by participant"
    session.cancelled_by_id = current_user.id
    session.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(session)
    return format_session_response(session, current_user.id)


def reschedule_session(
    session_id: uuid.UUID,
    current_user: User,
    payload: SessionReschedulePayload,
    db: Session,
) -> AssistanceSessionResponse:
    """
    Proposes a new time for an existing session.
    Preserves historical scheduled start/end and flips proposer/recipient.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Suspended accounts cannot reschedule sessions.",
        )

    session = db.query(AssistanceSession).filter(AssistanceSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    if current_user.id not in [session.proposer_id, session.recipient_id]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only session participants can propose a reschedule.",
        )

    if session.status not in [SessionStatus.CONFIRMED.value, SessionStatus.PROPOSED.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reschedule session with status '{session.status}'.",
        )

    other_user_id = session.recipient_id if current_user.id == session.proposer_id else session.proposer_id
    if is_blocked_bidirectional(db, current_user.id, other_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot reschedule session due to active safety restrictions.",
        )

    now_utc = datetime.now(timezone.utc)
    new_start = payload.new_scheduled_start
    if new_start.tzinfo is None:
        new_start = new_start.replace(tzinfo=timezone.utc)

    if new_start <= now_utc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New scheduled start must be in the future.",
        )

    duration = payload.new_duration_minutes or session.duration_minutes
    new_end = new_start + timedelta(minutes=duration)

    conn = session.connection
    helper_id = conn.helper_id if conn else other_user_id
    requester_id = conn.requester_id if conn else current_user.id

    # Check conflicts for the new time window
    check_session_conflicts(
        db,
        [requester_id, helper_id],
        new_start,
        new_end,
        exclude_session_id=session.id,
    )

    session.previous_scheduled_start = session.scheduled_start
    session.previous_scheduled_end = session.scheduled_end
    session.scheduled_start = new_start
    session.scheduled_end = new_end
    session.duration_minutes = duration

    # Flip proposer and recipient so the other user must review & confirm
    session.proposer_id = current_user.id
    session.recipient_id = other_user_id

    session.status = SessionStatus.RESCHEDULE_PROPOSED.value
    session.status_reason = payload.reschedule_reason.strip() if payload.reschedule_reason else None
    session.reschedule_count += 1
    session.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(session)
    return format_session_response(session, current_user.id)


def complete_session(
    session_id: uuid.UUID,
    current_user: User,
    db: Session,
) -> AssistanceSessionResponse:
    """
    Submits completion confirmation. When both requester and helper confirm,
    status transitions to COMPLETED.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Suspended accounts cannot complete sessions.",
        )

    session = db.query(AssistanceSession).filter(AssistanceSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    if session.status != SessionStatus.CONFIRMED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot complete session with status '{session.status}'. Must be CONFIRMED.",
        )

    conn = session.connection
    if not conn:
        raise HTTPException(status_code=500, detail="Linked connection missing.")

    now = datetime.now(timezone.utc)
    if current_user.id == conn.requester_id:
        session.requester_completed_at = now
    elif current_user.id == conn.helper_id:
        session.helper_completed_at = now
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only session participants (requester or helper) can confirm completion.",
        )

    # Dual-confirmation check
    if session.requester_completed_at is not None and session.helper_completed_at is not None:
        session.status = SessionStatus.COMPLETED.value

    session.updated_at = now
    db.commit()
    db.refresh(session)
    return format_session_response(session, current_user.id)


def get_session_by_id(
    session_id: uuid.UUID,
    current_user: User,
    db: Session,
) -> AssistanceSessionResponse:
    """
    Retrieves a single session. IDOR protection: only participants can view.
    """
    session = db.query(AssistanceSession).filter(AssistanceSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    if current_user.id not in [session.proposer_id, session.recipient_id]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to view this session.",
        )

    return format_session_response(session, current_user.id)


def list_user_sessions(
    current_user: User,
    status_filter: Optional[str],
    request_id: Optional[uuid.UUID],
    connection_id: Optional[uuid.UUID],
    db: Session,
) -> SessionListResponse:
    """
    Lists sessions involving the current user as either proposer or recipient.
    """
    query = db.query(AssistanceSession).filter(
        or_(
            AssistanceSession.proposer_id == current_user.id,
            AssistanceSession.recipient_id == current_user.id,
        )
    )

    if status_filter:
        query = query.filter(AssistanceSession.status == status_filter.upper())
    if request_id:
        query = query.filter(AssistanceSession.request_id == request_id)
    if connection_id:
        query = query.filter(AssistanceSession.connection_id == connection_id)

    sessions = query.order_by(AssistanceSession.scheduled_start.asc()).all()
    results = [format_session_response(s, current_user.id) for s in sessions]

    return SessionListResponse(total=len(results), sessions=results)


def generate_session_ics(
    session_id: uuid.UUID,
    current_user: User,
    db: Session,
) -> str:
    """
    Generates an RFC 5545 standard .ics calendar file for the session with 30-minute VALARM and ORGANIZER.
    """
    session = db.query(AssistanceSession).filter(AssistanceSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    if current_user.id not in [session.proposer_id, session.recipient_id]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to export calendar for this session.",
        )

    start_utc = session.scheduled_start.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    end_utc = session.scheduled_end.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    now_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    location = session.meeting_formatted_address or session.meeting_place_name or session.meeting_url or "Online"
    summary = session.title.replace("\n", " ").replace("\r", "")
    description = (session.description or f"NEST Assistance Session: {session.title}").replace("\n", "\\n").replace("\r", "")

    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//NEST Community//Assistance Sessions//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:session-{session.id}@nest.community",
        f"DTSTAMP:{now_utc}",
        f"DTSTART:{start_utc}",
        f"DTEND:{end_utc}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{description}",
        f"LOCATION:{location}",
        "ORGANIZER;CN=NEST Community:mailto:sessions@nest.community",
        f"STATUS:{'CONFIRMED' if session.status == SessionStatus.CONFIRMED.value else 'TENTATIVE'}",
        "BEGIN:VALARM",
        "TRIGGER:-PT30M",
        "ACTION:DISPLAY",
        "DESCRIPTION:Reminder: NEST Assistance Session starts in 30 minutes",
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(ics_lines) + "\r\n"


def cancel_future_sessions_for_block(
    db: Session,
    user_a_id: uuid.UUID,
    user_b_id: uuid.UUID,
    blocker_id: uuid.UUID,
) -> int:
    """
    Cancels any active or future uncompleted sessions between two users when a block occurs.
    """
    now_utc = datetime.now(timezone.utc)
    active_sessions = (
        db.query(AssistanceSession)
        .filter(
            or_(
                and_(AssistanceSession.proposer_id == user_a_id, AssistanceSession.recipient_id == user_b_id),
                and_(AssistanceSession.proposer_id == user_b_id, AssistanceSession.recipient_id == user_a_id),
            ),
            AssistanceSession.status.in_([
                SessionStatus.PROPOSED.value,
                SessionStatus.RESCHEDULE_PROPOSED.value,
                SessionStatus.CONFIRMED.value,
            ]),
            AssistanceSession.scheduled_end >= now_utc,
        )
        .all()
    )

    for s in active_sessions:
        s.status = SessionStatus.CANCELLED.value
        s.status_reason = "Cancelled due to user safety restriction"
        s.cancelled_by_id = blocker_id
        s.updated_at = now_utc

    if active_sessions:
        db.commit()

    return len(active_sessions)


def cancel_future_sessions_for_suspension(
    db: Session,
    user_id: uuid.UUID,
) -> int:
    """
    Cancels any active or future uncompleted sessions involving a suspended user.
    """
    now_utc = datetime.now(timezone.utc)
    active_sessions = (
        db.query(AssistanceSession)
        .filter(
            or_(
                AssistanceSession.proposer_id == user_id,
                AssistanceSession.recipient_id == user_id,
            ),
            AssistanceSession.status.in_([
                SessionStatus.PROPOSED.value,
                SessionStatus.RESCHEDULE_PROPOSED.value,
                SessionStatus.CONFIRMED.value,
            ]),
            AssistanceSession.scheduled_end >= now_utc,
        )
        .all()
    )

    for s in active_sessions:
        s.status = SessionStatus.CANCELLED.value
        s.status_reason = "Cancelled due to account suspension"
        s.cancelled_by_id = user_id
        s.updated_at = now_utc

    if active_sessions:
        db.commit()

    return len(active_sessions)
