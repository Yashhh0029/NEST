from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class PlaceAutocompletePrediction(BaseModel):
    place_id: str
    main_text: str
    secondary_text: Optional[str] = None
    description: str


class AutocompleteRequest(BaseModel):
    input_text: str = Field(..., min_length=1, max_length=200)
    session_token: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    radius_meters: Optional[float] = Field(None, ge=100.0, le=100000.0)


class AutocompleteResponse(BaseModel):
    predictions: List[PlaceAutocompletePrediction]


class ReverseGeocodeRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)


class ResolveTextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=255)


class ResolvedLocation(BaseModel):
    google_place_id: Optional[str] = None
    formatted_address: Optional[str] = None
    name: Optional[str] = None
    display_name: Optional[str] = None
    city: Optional[str] = None
    area: Optional[str] = None
    taluka: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    country: str = "India"
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_precision: str = "approximate"
    location_source: str = "google_places"
    road: Optional[str] = None
    neighborhood: Optional[str] = None
    suburb: Optional[str] = None

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (-90.0 <= v <= 90.0):
            raise ValueError("Latitude must be between -90.0 and 90.0 degrees")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (-180.0 <= v <= 180.0):
            raise ValueError("Longitude must be between -180.0 and 180.0 degrees")
        return v

    model_config = ConfigDict(from_attributes=True)


class TravelRouteInfo(BaseModel):
    straight_line_distance_km: float
    route_distance_km: Optional[float] = None
    estimated_travel_time_minutes: Optional[float] = None
    travel_mode: Optional[str] = "DRIVE"
