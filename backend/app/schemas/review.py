from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Integer rating between 1 and 5 stars")
    comment: Optional[str] = Field(None, max_length=1000, description="Optional review comment")

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: int) -> int:
        if isinstance(v, bool) or not isinstance(v, int):
            raise ValueError("Rating must be an integer between 1 and 5")
        if v < 1 or v > 5:
            raise ValueError("Rating must be an integer between 1 and 5")
        return v

    @field_validator("comment")
    @classmethod
    def validate_comment(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            stripped = v.strip()
            return stripped if stripped else None
        return None


class ReviewResponse(BaseModel):
    id: uuid.UUID
    connection_id: uuid.UUID
    reviewer_id: uuid.UUID
    reviewer_name: str
    reviewee_id: uuid.UUID
    reviewee_name: str
    rating: int
    comment: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReputationSummary(BaseModel):
    user_id: uuid.UUID
    average_rating: Optional[float] = None
    review_count: int = 0
    status: str = Field("UNAVAILABLE", description="'AVAILABLE' or 'UNAVAILABLE'")

    model_config = ConfigDict(from_attributes=True)


class ReviewListResponse(BaseModel):
    total: int
    reviews: List[ReviewResponse]
