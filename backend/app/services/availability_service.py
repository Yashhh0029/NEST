from datetime import date, datetime, time, timedelta, timezone
import logging
from typing import Dict, List, Optional, Set, Tuple
import uuid
from fastapi import HTTPException, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from app.models.availability import (
    HelperAvailabilityException,
    HelperAvailabilitySlot,
)
from app.models.connection import Connection, ConnectionStatus
from app.models.profile import Profile
from app.models.session import AssistanceSession, SessionStatus
from app.models.user import User
from app.schemas.availability import (
    AvailabilityExceptionResponse,
    AvailabilitySlotResponse,
    CapacityUpdatePayload,
    DetailedAvailabilityResponse,
    ExceptionCreatePayload,
    MyAvailabilityResponse,
    PublicAvailabilityResponse,
    SlotsUpdatePayload,
)

logger = logging.getLogger(__name__)


# Common IANA timezone validation helper
def validate_iana_timezone(tz_name: Optional[str]) -> str:
    if not tz_name:
        return "Asia/Kolkata"
    import zoneinfo
    try:
        zoneinfo.ZoneInfo(tz_name)
        return tz_name
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid IANA timezone: '{tz_name}'. Example valid timezones: 'Asia/Kolkata', 'Europe/London', 'America/New_York'.",
        )


def get_derived_capacity_status(
    db: Session,
    user_id: uuid.UUID,
    profile: Optional[Profile] = None,
) -> Tuple[str, int]:
    """
    Derives real capacity status from active database state.
    Returns: (capacity_status, active_confirmed_count)
    """
    if profile is None:
        profile = db.query(Profile).filter(Profile.user_id == user_id).first()

    accepting = profile.accepting_sessions if profile else True
    max_sessions = profile.max_weekly_sessions if profile else 3

    if not accepting:
        return "NOT_ACCEPTING", 0

    now_utc = datetime.now(timezone.utc)
    week_ahead = now_utc + timedelta(days=7)

    # Count confirmed sessions within next 7 days involving this user as either helper or recipient
    active_count = (
        db.query(AssistanceSession)
        .filter(
            AssistanceSession.status == SessionStatus.CONFIRMED.value,
            or_(
                AssistanceSession.proposer_id == user_id,
                AssistanceSession.recipient_id == user_id,
            ),
            AssistanceSession.scheduled_end >= now_utc,
            AssistanceSession.scheduled_start <= week_ahead,
        )
        .count()
    )

    if active_count >= max_sessions:
        return "AT_CAPACITY", active_count

    return "AVAILABLE", active_count


def update_helper_slots(
    db: Session,
    current_user: User,
    payload: SlotsUpdatePayload,
) -> List[AvailabilitySlotResponse]:
    """
    Replaces all recurring weekly slots for the authenticated user with validation.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Suspended accounts cannot manage availability.",
        )

    # Validate slots
    day_slots: Dict[int, List[Tuple[time, time]]] = {}
    for s in payload.slots:
        if s.start_time >= s.end_time:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Slot start time ({s.start_time}) must be earlier than end time ({s.end_time}).",
            )
        # Check collision on same day
        existing = day_slots.setdefault(s.day_of_week, [])
        for ex_start, ex_end in existing:
            # Overlap check
            if max(s.start_time, ex_start) < min(s.end_time, ex_end):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Overlapping slots detected on day {s.day_of_week} ({s.start_time}-{s.end_time} overlaps with {ex_start}-{ex_end}).",
                )
        existing.append((s.start_time, s.end_time))

    # Update timezone if provided
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        profile = Profile(user_id=current_user.id)
        db.add(profile)

    if payload.helper_timezone:
        profile.helper_timezone = validate_iana_timezone(payload.helper_timezone)

    # Replace existing slots
    db.query(HelperAvailabilitySlot).filter(HelperAvailabilitySlot.user_id == current_user.id).delete()

    created_slots = []
    for s in payload.slots:
        slot_obj = HelperAvailabilitySlot(
            user_id=current_user.id,
            day_of_week=s.day_of_week,
            start_time=s.start_time,
            end_time=s.end_time,
            is_active=True,
        )
        db.add(slot_obj)
        created_slots.append(slot_obj)

    db.commit()
    return get_my_availability(db, current_user)


def add_availability_exception(
    db: Session,
    current_user: User,
    payload: ExceptionCreatePayload,
) -> AvailabilityExceptionResponse:
    """
    Creates or updates a date exception (e.g. blackout date) for current user.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Suspended accounts cannot manage availability.",
        )

    # Check if exception exists for this date
    existing = (
        db.query(HelperAvailabilityException)
        .filter(
            HelperAvailabilityException.user_id == current_user.id,
            HelperAvailabilityException.exception_date == payload.exception_date,
        )
        .first()
    )

    if existing:
        existing.is_available = payload.is_available
        existing.reason = payload.reason
        db.commit()
        db.refresh(existing)
        return AvailabilityExceptionResponse.model_validate(existing)

    new_ex = HelperAvailabilityException(
        user_id=current_user.id,
        exception_date=payload.exception_date,
        is_available=payload.is_available,
        reason=payload.reason,
    )
    db.add(new_ex)
    db.commit()
    db.refresh(new_ex)
    return AvailabilityExceptionResponse.model_validate(new_ex)


def delete_availability_exception(
    db: Session,
    current_user: User,
    exception_id: uuid.UUID,
) -> None:
    """
    Deletes a date exception owned by current user.
    """
    ex = (
        db.query(HelperAvailabilityException)
        .filter(
            HelperAvailabilityException.id == exception_id,
            HelperAvailabilityException.user_id == current_user.id,
        )
        .first()
    )
    if not ex:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability exception not found.",
        )
    db.delete(ex)
    db.commit()


def update_capacity_controls(
    db: Session,
    current_user: User,
    payload: CapacityUpdatePayload,
) -> MyAvailabilityResponse:
    """
    Updates max weekly sessions, global accepting toggle, or timezone for current user.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Suspended accounts cannot manage availability.",
        )

    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        profile = Profile(user_id=current_user.id)
        db.add(profile)

    if payload.max_weekly_sessions is not None:
        profile.max_weekly_sessions = payload.max_weekly_sessions
    if payload.accepting_sessions is not None:
        profile.accepting_sessions = payload.accepting_sessions
    if payload.helper_timezone is not None:
        profile.helper_timezone = validate_iana_timezone(payload.helper_timezone)

    db.commit()
    return get_my_availability(db, current_user)


def get_my_availability(db: Session, current_user: User) -> MyAvailabilityResponse:
    """
    Returns full availability, slots, exceptions, and derived capacity for authenticated user.
    """
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    helper_tz = profile.helper_timezone if profile and profile.helper_timezone else "Asia/Kolkata"
    accepting = profile.accepting_sessions if profile else True
    max_sessions = profile.max_weekly_sessions if profile else 3

    cap_status, active_count = get_derived_capacity_status(db, current_user.id, profile)

    slots = (
        db.query(HelperAvailabilitySlot)
        .filter(
            HelperAvailabilitySlot.user_id == current_user.id,
            HelperAvailabilitySlot.is_active == True,
        )
        .order_by(HelperAvailabilitySlot.day_of_week.asc(), HelperAvailabilitySlot.start_time.asc())
        .all()
    )

    exceptions = (
        db.query(HelperAvailabilityException)
        .filter(HelperAvailabilityException.user_id == current_user.id)
        .order_by(HelperAvailabilityException.exception_date.asc())
        .all()
    )

    return MyAvailabilityResponse(
        helper_timezone=helper_tz,
        accepting_sessions=accepting,
        max_weekly_sessions=max_sessions,
        active_confirmed_sessions_count=active_count,
        capacity_status=cap_status,
        slots=[AvailabilitySlotResponse.model_validate(s) for s in slots],
        exceptions=[AvailabilityExceptionResponse.model_validate(e) for e in exceptions],
    )


def get_public_or_detailed_availability(
    db: Session,
    target_user_id: uuid.UUID,
    viewer: User,
) -> PublicAvailabilityResponse:
    """
    Returns availability for target user.
    Enforces the Two-Tier Privacy Model:
    - Tier 1: Public Discovery -> Coarse status, next open day, no detailed routine.
    - Tier 2: Authorized Connection -> If viewer has an ACCEPTED connection with target user,
      returns DetailedAvailabilityResponse with slots for coordination.
    """
    target_user = db.query(User).filter(User.id == target_user_id).first()
    if not target_user or not target_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Helper not found or inactive.",
        )

    profile = db.query(Profile).filter(Profile.user_id == target_user_id).first()
    helper_tz = profile.helper_timezone if profile and profile.helper_timezone else "Asia/Kolkata"
    cap_status, _ = get_derived_capacity_status(db, target_user_id, profile)

    slots = (
        db.query(HelperAvailabilitySlot)
        .filter(
            HelperAvailabilitySlot.user_id == target_user_id,
            HelperAvailabilitySlot.is_active == True,
        )
        .order_by(HelperAvailabilitySlot.day_of_week.asc(), HelperAvailabilitySlot.start_time.asc())
        .all()
    )

    has_schedule = len(slots) > 0
    if not has_schedule:
        cap_status = "UNAVAILABLE"

    # Derive coarse windows without leaking exact routine
    coarse_windows: Set[str] = set()
    for s in slots:
        is_weekend = s.day_of_week in (5, 6)
        if is_weekend:
            if s.start_time < time(13, 0):
                coarse_windows.add("Weekend Mornings")
            else:
                coarse_windows.add("Weekend Afternoons")
        else:
            if s.start_time >= time(17, 0):
                coarse_windows.add("Weekday Evenings")
            elif s.start_time < time(12, 0):
                coarse_windows.add("Weekday Mornings")
            else:
                coarse_windows.add("Weekday Afternoons")

    # Find next available date in next 14 days
    today = date.today()
    blackouts = set(
        e.exception_date
        for e in db.query(HelperAvailabilityException)
        .filter(
            HelperAvailabilityException.user_id == target_user_id,
            HelperAvailabilityException.is_available == False,
        )
        .all()
    )

    next_date: Optional[date] = None
    if has_schedule and cap_status == "AVAILABLE":
        active_days = set(s.day_of_week for s in slots)
        for offset in range(1, 15):
            candidate_d = today + timedelta(days=offset)
            if candidate_d.weekday() in active_days and candidate_d not in blackouts:
                next_date = candidate_d
                break

    # Check if viewer has an active connection with target
    has_active_conn = False
    if viewer:
        if viewer.id == target_user_id:
            has_active_conn = True
        else:
            conn = (
                db.query(Connection)
                .filter(
                    Connection.status == ConnectionStatus.ACCEPTED.value,
                    or_(
                        and_(Connection.requester_id == viewer.id, Connection.helper_id == target_user_id),
                        and_(Connection.requester_id == target_user_id, Connection.helper_id == viewer.id),
                    ),
                )
                .first()
            )
            if conn:
                has_active_conn = True

    if has_active_conn:
        # Tier 2: Return detailed slots for coordination
        exceptions = (
            db.query(HelperAvailabilityException)
            .filter(HelperAvailabilityException.user_id == target_user_id)
            .all()
        )
        return DetailedAvailabilityResponse(
            user_id=target_user_id,
            helper_timezone=helper_tz,
            capacity_status=cap_status,
            has_schedule_configured=has_schedule,
            next_available_date=next_date,
            coarse_windows=sorted(list(coarse_windows)),
            active_slots_count=len(slots),
            slots=[AvailabilitySlotResponse.model_validate(s) for s in slots],
            exceptions=[AvailabilityExceptionResponse.model_validate(e) for e in exceptions],
        )

    # Tier 1: Public Discovery only
    return PublicAvailabilityResponse(
        user_id=target_user_id,
        helper_timezone=helper_tz,
        capacity_status=cap_status,
        has_schedule_configured=has_schedule,
        next_available_date=next_date,
        coarse_windows=sorted(list(coarse_windows)),
        active_slots_count=len(slots),
    )
