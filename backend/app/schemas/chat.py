from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas.connection import ConnectionRequestSummary, ConnectionUserSummary


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000, description="Message text content")

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Message content cannot be empty or only whitespace")
        return stripped


class MessageUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000, description="Updated message text content")

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Message content cannot be empty or only whitespace")
        return stripped


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    sender_name: str
    content: str
    is_read: bool
    is_mine: Optional[bool] = None
    created_at: datetime
    updated_at: datetime
    edited_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ConversationCreate(BaseModel):
    connection_id: uuid.UUID


class ConversationResponse(BaseModel):
    id: uuid.UUID
    connection_id: uuid.UUID
    partner: ConnectionUserSummary
    request: Optional[ConnectionRequestSummary] = None
    created_at: datetime
    updated_at: datetime
    last_message: Optional[MessageResponse] = None
    unread_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class ConversationListResponse(BaseModel):
    total: int
    conversations: List[ConversationResponse]


class MessageListResponse(BaseModel):
    total: int
    has_more: bool
    messages: List[MessageResponse]
