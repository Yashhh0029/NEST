from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.community import CommunitySearchItem
from app.schemas.matching import HelperCandidate
from app.schemas.resource import ResourceItem


class NeedStatusEnum(str, Enum):
    UNRESOLVED = "UNRESOLVED"
    EXPLORING = "EXPLORING"
    CONNECTED = "CONNECTED"
    RESOLUTION_PENDING = "RESOLUTION_PENDING"
    RESOLVED = "RESOLVED"


class ResolutionSourceEnum(str, Enum):
    CONNECTION = "connection"
    COMMUNITY_QUESTION = "community_question"
    SAVED_RESOURCE = "saved_resource"
    SESSION = "session"
    MANUAL = "manual"


class NeedProgressItem(BaseModel):
    category: str
    item: str
    status: NeedStatusEnum = NeedStatusEnum.UNRESOLVED
    resolved_via: Optional[ResolutionSourceEnum] = None
    resolved_entity_id: Optional[str] = None
    notes: Optional[str] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class NeedProgressUpdate(BaseModel):
    category: str = Field(..., description="Need category to update (e.g. accommodation, food, transport)")
    status: NeedStatusEnum = Field(..., description="Target status")
    resolved_via: Optional[ResolutionSourceEnum] = Field(None, description="Source proving progress/resolution")
    resolved_entity_id: Optional[str] = Field(None, description="Verified entity ID (connection_id, question_id, or place_id)")
    notes: Optional[str] = Field(None, max_length=500, description="Optional user note")


class RequestResolvePayload(BaseModel):
    resolution_summary: Optional[str] = Field(None, max_length=1000, description="Optional user summary of how the overall request was resolved")


class SavedResourceCreate(BaseModel):
    place_id: str = Field(..., max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=100)
    formatted_address: Optional[str] = None
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    # Public place coordinates only from Google Places (NEVER private home coordinates)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    notes: Optional[str] = Field(None, max_length=1000)


class SavedResourceResponse(BaseModel):
    id: uuid.UUID
    request_id: uuid.UUID
    user_id: uuid.UUID
    place_id: str
    name: str
    category: str
    formatted_address: Optional[str] = None
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActiveConnectionSummary(BaseModel):
    id: uuid.UUID
    helper_id: uuid.UUID
    helper_name: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    has_review: bool = False

    model_config = ConfigDict(from_attributes=True)


class NeedIntelligenceBundle(BaseModel):
    category: str
    item: str
    status: NeedStatusEnum
    resolved_via: Optional[str] = None
    resolved_entity_id: Optional[str] = None
    matched_helpers: List[HelperCandidate] = []
    community_questions: List[CommunitySearchItem] = []
    local_resources: List[ResourceItem] = []


class RequestIntelligenceResponse(BaseModel):
    request_id: uuid.UUID
    raw_text: str
    status: str
    city: Optional[str] = None
    area: Optional[str] = None
    budget: Optional[Dict[str, Any]] = None
    total_needs: int = 0
    resolved_needs: int = 0
    progress_percentage: float = 0.0
    action_plan: List[str] = []
    needs: List[NeedIntelligenceBundle] = []
    active_connections: List[ActiveConnectionSummary] = []
    saved_resources: List[SavedResourceResponse] = []
    resolution_summary: Optional[str] = None
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
