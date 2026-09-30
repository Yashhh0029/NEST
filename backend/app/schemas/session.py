from datetime import datetime
from enum import Enum
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class SessionStatusEnum(str, Enum):
    PROPOSED = "PROPOSED"
    CONFIRMED = "CONFIRMED"
    RESCHEDULE_PROPOSED = "RESCHEDULE_PROPOSED"
    DECLINED = "DECLINED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class SessionModalityEnum(str, Enum):
    IN_PERSON = "IN_PERSON"
    REMOTE = "REMOTE"


class SessionCreatePayload(BaseModel):
    request_id: uuid.UUID
    recipient_id: uuid.UUID
    title: str = Field(..., min_length=3, max_length=255, description="Clear session title or goal")
    description: Optional[str] = Field(None, max_length=2000, description="Optional agenda or details")
    need_category: Optional[str] = Field(None, max_length=100, description="Optional linked Phase 13 need category")
    modality: SessionModalityEnum = Field(..., description="IN_PERSON or REMOTE")
    meeting_place_id: Optional[str] = Field(None, max_length=255, description="Google Place ID of eligible public venue (required for IN_PERSON)")
    meeting_url: Optional[str] = Field(None, max_length=500, description="HTTPS meeting link (for REMOTE)")
    scheduled_start: datetime = Field(..., description="Target start timestamp with timezone or in UTC")
    duration_minutes: int = Field(60, ge=15, le=480, description="Planned duration in minutes")
    session_timezone: Optional[str] = Field("Asia/Kolkata", max_length=50, description="Target location or session IANA timezone")


class SessionReschedulePayload(BaseModel):
    new_scheduled_start: datetime = Field(..., description="New proposed start timestamp")
    new_duration_minutes: Optional[int] = Field(None, ge=15, le=480, description="Optional new duration")
    reschedule_reason: Optional[str] = Field(None, max_length=500, description="Reason for proposing reschedule")


class SessionActionPayload(BaseModel):
    reason: Optional[str] = Field(None, max_length=500, description="Optional reason for decline/cancellation")


class AssistanceSessionResponse(BaseModel):
    id: uuid.UUID
    connection_id: uuid.UUID
    request_id: uuid.UUID
    proposer_id: uuid.UUID
    recipient_id: uuid.UUID
    title: str
    description: Optional[str] = None
    need_category: Optional[str] = None
    modality: str
    meeting_place_id: Optional[str] = None
    meeting_place_name: Optional[str] = None
    meeting_formatted_address: Optional[str] = None
    meeting_latitude: Optional[float] = None
    meeting_longitude: Optional[float] = None
    meeting_url: Optional[str] = None
    scheduled_start: datetime
    scheduled_end: datetime
    duration_minutes: int
    session_timezone: str
    status: str
    status_reason: Optional[str] = None
    previous_scheduled_start: Optional[datetime] = None
    previous_scheduled_end: Optional[datetime] = None
    reschedule_count: int = 0
    requester_completed_at: Optional[datetime] = None
    helper_completed_at: Optional[datetime] = None
    is_my_proposal: bool = False
    can_accept: bool = False
    can_reschedule: bool = False
    can_cancel: bool = False
    can_complete: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionListResponse(BaseModel):
    total: int
    sessions: List[AssistanceSessionResponse]
