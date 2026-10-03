import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    request_id: Optional[uuid.UUID] = None
    notification_type: str
    title: str
    message: str
    is_read: bool
    read_at: Optional[datetime] = None
    metadata_payload: Optional[Dict[str, Any]] = None
    distance_km: Optional[float] = None
    request_status: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int
