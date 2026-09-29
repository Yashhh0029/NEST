import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class EmbeddingResponse(BaseModel):
    embedding_id: uuid.UUID
    owner_type: str
    owner_id: uuid.UUID
    model_name: str
    dimension: int
    source_hash: str
    created_or_updated: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SemanticSearchQuery(BaseModel):
    query_text: str = Field(..., min_length=1, max_length=2000, description="Natural query text to search against helper profiles")
    limit: Optional[int] = Field(default=10, ge=1, le=50, description="Maximum number of matches to retrieve")
    min_similarity: Optional[float] = Field(default=0.0, ge=-1.0, le=1.0, description="Minimum cosine similarity cutoff")


class SemanticSearchResultItem(BaseModel):
    user_id: uuid.UUID
    similarity: float
    canonical_text: str


class SemanticSearchResponse(BaseModel):
    query: str
    total_matches: int
    results: List[SemanticSearchResultItem]
