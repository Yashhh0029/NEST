from datetime import datetime
from enum import Enum
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ConnectionStatusEnum(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    CANCELLED = "CANCELLED"


class ConnectionCreate(BaseModel):
    request_id: uuid.UUID
    helper_id: uuid.UUID
    initial_message: Optional[str] = Field(None, max_length=1000)


class ConnectionStatusUpdate(BaseModel):
    action: str = Field(..., description="Action to take: 'accept', 'decline', or 'cancel'")


class ConnectionUserSummary(BaseModel):
    id: uuid.UUID
    name: str
    headline: Optional[str] = None
    city: Optional[str] = None
    area: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ConnectionRequestSummary(BaseModel):
    id: uuid.UUID
    raw_text: str
    city: Optional[str] = None
    area: Optional[str] = None
    intent: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ConnectionResponse(BaseModel):
    id: uuid.UUID
    request_id: uuid.UUID
    requester_id: uuid.UUID
    helper_id: uuid.UUID
    status: ConnectionStatusEnum
    initial_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    accepted_at: Optional[datetime] = None
    declined_at: Optional[datetime] = None
    requester: Optional[ConnectionUserSummary] = None
    helper: Optional[ConnectionUserSummary] = None
    request: Optional[ConnectionRequestSummary] = None

    model_config = ConfigDict(from_attributes=True)


class ConnectionListResponse(BaseModel):
    total: int
    connections: List[ConnectionResponse]
