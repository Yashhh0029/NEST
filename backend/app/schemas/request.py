import uuid
from datetime import date, datetime, time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.location import RequestLocationResponse
from app.services.request_parser import ExtractedRequest


class RequestCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="Raw natural-language request from newcomer")
    preferred_date: Optional[date] = Field(None, description="Preferred date for assistance")
    preferred_start_time: Optional[time] = Field(None, description="Earliest preferred time of day")
    preferred_end_time: Optional[time] = Field(None, description="Latest preferred time of day")
    requester_timezone: Optional[str] = Field("Asia/Kolkata", max_length=50, description="IANA timezone")
    is_time_flexible: Optional[bool] = Field(True, description="Whether timing is flexible")
    flexibility_window_days: Optional[int] = Field(3, ge=0, le=30, description="Flexibility margin in days")
    preferred_days_of_week: Optional[List[int]] = Field(default_factory=list, description="0=Monday ... 6=Sunday")
    # Target location override / explicit map selection
    target_city: Optional[str] = Field(None, max_length=100, description="Explicit target city where help is needed")
    target_area: Optional[str] = Field(None, max_length=100, description="Explicit target area/neighborhood")
    target_google_place_id: Optional[str] = Field(None, max_length=255, description="Google Place ID of target destination")
    target_latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Target destination latitude")
    target_longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Target destination longitude")
    target_formatted_address: Optional[str] = Field(None, max_length=500, description="Formatted address of target destination")


class RequestParse(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="Raw request text for preview/testing without persistence")


class RequestUpdate(BaseModel):
    text: Optional[str] = Field(None, min_length=1, max_length=2000, description="Updated raw request text (will trigger re-parse)")
    status: Optional[str] = Field(None, max_length=50, description="Request status e.g. OPEN, CLOSED, FULFILLED")
    preferred_date: Optional[date] = None
    preferred_start_time: Optional[time] = None
    preferred_end_time: Optional[time] = None
    requester_timezone: Optional[str] = None
    is_time_flexible: Optional[bool] = None
    flexibility_window_days: Optional[int] = None
    preferred_days_of_week: Optional[List[int]] = None
    is_independent_resolution: Optional[bool] = Field(False, description="Whether resolving independently without helper")
    resolution_summary: Optional[str] = Field(None, max_length=1000, description="Optional note or explanation")


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
    preferred_date: Optional[date] = None
    preferred_start_time: Optional[time] = None
    preferred_end_time: Optional[time] = None
    requester_timezone: str = "Asia/Kolkata"
    is_time_flexible: bool = True
    flexibility_window_days: Optional[int] = 3
    preferred_days_of_week: Optional[List[int]] = []
    extracted_requirements: Optional[Dict[str, Any]]
    preferences: Optional[List[str]]
    user_context: Optional[List[str]]
    extraction_method: str
    target_location: Optional[RequestLocationResponse] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RequestParseResponse(BaseModel):
    raw_text: str
    extracted: ExtractedRequest


class NearbyRequestItem(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    requester_name: str
    raw_text: str
    intent: Optional[str] = None
    status: str
    city: Optional[str] = None
    area: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    budget_amount: Optional[float] = None
    budget_currency: Optional[str] = None
    budget_period: Optional[str] = None
    preferred_date: Optional[date] = None
    preferred_start_time: Optional[time] = None
    preferred_end_time: Optional[time] = None
    requester_timezone: Optional[str] = None
    is_time_flexible: bool = True
    needs: List[str] = Field(default_factory=list)
    distance_km: Optional[float] = None
    match_reasons: List[str] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
