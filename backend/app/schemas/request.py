import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.services.request_parser import ExtractedRequest


class RequestCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="Raw natural-language request from newcomer")


class RequestParse(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="Raw request text for preview/testing without persistence")


class RequestUpdate(BaseModel):
    text: Optional[str] = Field(None, min_length=1, max_length=2000, description="Updated raw request text (will trigger re-parse)")
    status: Optional[str] = Field(None, max_length=50, description="Request status e.g. OPEN, CLOSED, FULFILLED")


class RequestResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    raw_text: str
    intent: Optional[str]
    status: str
    city: Optional[str]
    area: Optional[str]
    state: Optional[str]
    country: Optional[str]
    budget_amount: Optional[float]
    budget_currency: Optional[str]
    budget_period: Optional[str]
    budget_operator: Optional[str]
    extracted_requirements: Optional[Dict[str, Any]]
    preferences: Optional[List[str]]
    user_context: Optional[List[str]]
    extraction_method: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RequestParseResponse(BaseModel):
    raw_text: str
    extracted: ExtractedRequest
