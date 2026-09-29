from datetime import datetime
import enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ReportReasonEnum(str, enum.Enum):
    HARASSMENT = "HARASSMENT"
    SPAM = "SPAM"
    SCAM = "SCAM"
    THREAT = "THREAT"
    INAPPROPRIATE_CONTENT = "INAPPROPRIATE_CONTENT"
    FAKE_PROFILE = "FAKE_PROFILE"
    SAFETY_CONCERN = "SAFETY_CONCERN"
    OTHER = "OTHER"


class ReportStatusEnum(str, enum.Enum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class ModerationActionTypeEnum(str, enum.Enum):
    REPORT_REVIEWED = "REPORT_REVIEWED"
    REPORT_RESOLVED = "REPORT_RESOLVED"
    REPORT_DISMISSED = "REPORT_DISMISSED"
    USER_SUSPENDED = "USER_SUSPENDED"
    USER_REACTIVATED = "USER_REACTIVATED"


# Block Schemas
class BlockUserSummary(BaseModel):
    id: uuid.UUID
    name: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class BlockResponse(BaseModel):
    id: uuid.UUID
    blocker_id: uuid.UUID
    blocked_id: uuid.UUID
    created_at: datetime
    blocked_user: Optional[BlockUserSummary] = None

    model_config = ConfigDict(from_attributes=True)


class BlockListResponse(BaseModel):
    total: int
    blocks: List[BlockResponse]


# Report Schemas
class ReportCreate(BaseModel):
    reported_user_id: uuid.UUID
    connection_id: Optional[uuid.UUID] = None
    message_id: Optional[uuid.UUID] = None
    question_id: Optional[uuid.UUID] = None
    answer_id: Optional[uuid.UUID] = None
    reason: ReportReasonEnum
    description: Optional[str] = Field(None, max_length=2000)


class ReportUserSummary(BaseModel):
    id: uuid.UUID
    name: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class ReportResponse(BaseModel):
    id: uuid.UUID
    reporter_id: uuid.UUID
    reported_user_id: uuid.UUID
    connection_id: Optional[uuid.UUID] = None
    message_id: Optional[uuid.UUID] = None
    question_id: Optional[uuid.UUID] = None
    answer_id: Optional[uuid.UUID] = None
    reason: ReportReasonEnum
    description: Optional[str] = None
    status: ReportStatusEnum
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ReportDetailResponse(ReportResponse):
    reporter: Optional[ReportUserSummary] = None
    reported_user: Optional[ReportUserSummary] = None
    resolved_by_user: Optional[ReportUserSummary] = None
    message_snippet: Optional[str] = None
    connection_summary: Optional[str] = None
    question_title: Optional[str] = None
    answer_snippet: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ReportListResponse(BaseModel):
    total: int
    reports: List[ReportDetailResponse]


class ReportUpdateStatus(BaseModel):
    status: ReportStatusEnum
    resolution_note: Optional[str] = Field(None, max_length=2000)


# Moderation Audit & User Suspension Schemas
class UserSuspensionRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=1000)


class ModerationActionResponse(BaseModel):
    id: uuid.UUID
    admin_id: uuid.UUID
    target_user_id: Optional[uuid.UUID] = None
    report_id: Optional[uuid.UUID] = None
    action: ModerationActionTypeEnum
    reason: str
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    admin_name: Optional[str] = None
    target_user_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ModerationActionListResponse(BaseModel):
    total: int
    actions: List[ModerationActionResponse]
