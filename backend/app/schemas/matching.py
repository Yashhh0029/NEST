from enum import Enum
from typing import Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

from app.schemas.google_location import TravelRouteInfo


class DimensionStatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    UNAVAILABLE = "UNAVAILABLE"


class MatchWeightsInput(BaseModel):
    semantic: float = Field(0.40, ge=0.0, le=1.0)
    location: float = Field(0.25, ge=0.0, le=1.0)
    experience: float = Field(0.15, ge=0.0, le=1.0)
    reputation: float = Field(0.10, ge=0.0, le=1.0)
    availability: float = Field(0.10, ge=0.0, le=1.0)


class FindMatchesRequest(BaseModel):
    request_id: uuid.UUID
    limit: Optional[int] = Field(10, ge=1, le=50)
    weights: Optional[MatchWeightsInput] = None
    min_score: Optional[float] = Field(0.0, ge=0.0, le=1.0)


class MatchScores(BaseModel):
    semantic_score: float
    location_score: float
    experience_score: float
    reputation_score: Optional[float] = None
    availability_score: Optional[float] = None
    final_score: float


class DimensionStatuses(BaseModel):
    semantic: DimensionStatusEnum = DimensionStatusEnum.ACTIVE
    location: DimensionStatusEnum = DimensionStatusEnum.ACTIVE
    experience: DimensionStatusEnum = DimensionStatusEnum.ACTIVE
    reputation: DimensionStatusEnum = DimensionStatusEnum.UNAVAILABLE
    availability: DimensionStatusEnum = DimensionStatusEnum.UNAVAILABLE


class MatchReason(BaseModel):
    category: str  # "semantic" | "location" | "experience"
    title: str
    explanation: str


class HelperCandidate(BaseModel):
    user_id: uuid.UUID
    name: str
    headline: Optional[str] = None
    bio: Optional[str] = None
    city: Optional[str] = None
    area: Optional[str] = None
    distance_km: Optional[float] = None
    approximate_latitude: Optional[float] = None
    approximate_longitude: Optional[float] = None
    route_info: Optional[TravelRouteInfo] = None
    skills: List[str] = []
    scores: MatchScores
    dimension_statuses: DimensionStatuses
    reasons: List[MatchReason]
    is_available_for_help: Optional[bool] = None


class TargetLocationSummary(BaseModel):
    city: Optional[str] = None
    area: Optional[str] = None
    formatted_address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_source: Optional[str] = None


class WeightsSummary(BaseModel):
    raw: Dict[str, float]
    effective: Dict[str, float]


class MatchingResponse(BaseModel):
    request_id: uuid.UUID
    target_location: Optional[TargetLocationSummary] = None
    total_candidates_evaluated: int
    matches: List[HelperCandidate]
    weights_used: WeightsSummary
    generated_at: str

