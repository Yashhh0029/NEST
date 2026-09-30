from datetime import date, datetime, time
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class SlotItem(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6, description="0=Monday, 6=Sunday")
    start_time: time = Field(..., description="Start time of recurring slot")
    end_time: time = Field(..., description="End time of recurring slot")


class SlotsUpdatePayload(BaseModel):
    slots: List[SlotItem] = Field(..., max_length=50, description="List of weekly recurring availability slots")
    helper_timezone: Optional[str] = Field(None, max_length=50, description="Optional IANA timezone to update")


class ExceptionCreatePayload(BaseModel):
    exception_date: date = Field(..., description="Date of exception/override")
    is_available: bool = Field(False, description="False=blackout date, True=custom open date")
    reason: Optional[str] = Field(None, max_length=255, description="Optional reason (e.g. Vacation, Holiday)")


class CapacityUpdatePayload(BaseModel):
    max_weekly_sessions: Optional[int] = Field(None, ge=1, le=20, description="Maximum confirmed sessions per rolling 7 days")
    accepting_sessions: Optional[bool] = Field(None, description="Global toggle to accept new sessions")
    helper_timezone: Optional[str] = Field(None, max_length=50, description="IANA timezone")


class AvailabilitySlotResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    day_of_week: int
    start_time: time
    end_time: time
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class AvailabilityExceptionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    exception_date: date
    is_available: bool
    reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MyAvailabilityResponse(BaseModel):
    helper_timezone: str
    accepting_sessions: bool
    max_weekly_sessions: int
    active_confirmed_sessions_count: int
    capacity_status: str  # "AVAILABLE", "AT_CAPACITY", "NOT_ACCEPTING"
    slots: List[AvailabilitySlotResponse]
    exceptions: List[AvailabilityExceptionResponse]


class PublicAvailabilityResponse(BaseModel):
    user_id: uuid.UUID
    helper_timezone: str
    capacity_status: str  # "AVAILABLE", "AT_CAPACITY", "NOT_ACCEPTING", "UNAVAILABLE"
    has_schedule_configured: bool
    next_available_date: Optional[date] = None
    coarse_windows: List[str] = []
    active_slots_count: int


class DetailedAvailabilityResponse(PublicAvailabilityResponse):
    slots: List[AvailabilitySlotResponse] = []
    exceptions: List[AvailabilityExceptionResponse] = []
