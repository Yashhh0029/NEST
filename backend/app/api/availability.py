from typing import List, Union
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.availability import (
    AvailabilityExceptionResponse,
    CapacityUpdatePayload,
    DetailedAvailabilityResponse,
    ExceptionCreatePayload,
    MyAvailabilityResponse,
    PublicAvailabilityResponse,
    SlotItem,
    SlotsUpdatePayload,
)
from app.services import availability_service

router = APIRouter(prefix="/availability", tags=["availability"])


@router.put("/slots", response_model=MyAvailabilityResponse)
@router.put("/slots/me", response_model=MyAvailabilityResponse)
def update_availability_slots(
    payload: Union[SlotsUpdatePayload, List[SlotItem]],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update the authenticated helper's recurring weekly availability slots.
    Replaces all active slots for the helper.
    Accepts both SlotsUpdatePayload {"slots": [...]} and raw list of slots [...].
    """
    if isinstance(payload, list):
        payload = SlotsUpdatePayload(slots=payload)
    return availability_service.update_helper_slots(db, current_user, payload)


@router.get("/my", response_model=MyAvailabilityResponse)
@router.get("/slots/me")
def get_my_availability(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve the authenticated user's complete availability schedule,
    including weekly slots, exceptions, and derived capacity.
    """
    return availability_service.get_my_availability(db, current_user)


@router.post("/exceptions", response_model=AvailabilityExceptionResponse, status_code=status.HTTP_201_CREATED)
def add_availability_exception(
    payload: ExceptionCreatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add or update a date exception (e.g. blackout date or holiday).
    """
    return availability_service.add_availability_exception(db, current_user, payload)


@router.delete("/exceptions/{exception_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_availability_exception(
    exception_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a specific availability exception.
    """
    availability_service.delete_availability_exception(db, current_user, exception_id)
    return None


@router.put("/capacity", response_model=MyAvailabilityResponse)
@router.put("/capacity/me", response_model=MyAvailabilityResponse)
def update_capacity_controls(
    payload: CapacityUpdatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update capacity controls: max weekly sessions, global accepting toggle, or timezone.
    """
    return availability_service.update_capacity_controls(db, current_user, payload)


@router.get("/capacity/me")
def get_my_capacity(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve helper's current capacity configuration and real-time status.
    """
    avail = availability_service.get_my_availability(db, current_user)
    badge = (
        "Available" if avail.capacity_status == "AVAILABLE"
        else "At Capacity" if avail.capacity_status == "AT_CAPACITY"
        else "Not Accepting"
    )
    return {
        "user_id": str(current_user.id),
        "helper_timezone": avail.helper_timezone,
        "timezone": avail.helper_timezone,
        "max_weekly_sessions": avail.max_weekly_sessions,
        "accepting_sessions": avail.accepting_sessions,
        "current_status": avail.capacity_status,
        "availability_badge": badge,
        "detailed_slots": [s.model_dump() for s in avail.slots],
    }


@router.get("/user/{user_id}", response_model=Union[DetailedAvailabilityResponse, PublicAvailabilityResponse])
def get_helper_availability(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve a helper's availability.
    Enforces Two-Tier Privacy:
    - If connected via accepted connection: returns DetailedAvailabilityResponse with slots.
    - Otherwise: returns coarse PublicAvailabilityResponse (zero routine leakage).
    """
    return availability_service.get_public_or_detailed_availability(db, user_id, current_user)
