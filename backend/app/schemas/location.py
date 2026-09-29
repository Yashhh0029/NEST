import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class LocationBase(BaseModel):
    city: str = Field(..., min_length=1, max_length=100, description="City name")
    area: Optional[str] = Field(None, max_length=100, description="Neighborhood or area name")
    state: Optional[str] = Field(None, max_length=100, description="State or province")
    country: Optional[str] = Field(default="India", max_length=100, description="Country name")
    latitude: Optional[float] = Field(None, description="Geographic latitude in degrees [-90, 90]")
    longitude: Optional[float] = Field(None, description="Geographic longitude in degrees [-180, 180]")
    location_label: Optional[str] = Field(default="Primary", max_length=100, description="Label for this location")
    google_place_id: Optional[str] = Field(None, max_length=255, description="Google Place ID")
    formatted_address: Optional[str] = Field(None, max_length=500, description="Human readable address")
    postal_code: Optional[str] = Field(None, max_length=20, description="Postal / PIN code")
    location_source: Optional[str] = Field(default="manual", max_length=50, description="Source of coordinates")
    location_precision: Optional[str] = Field(default="locality", max_length=50, description="Precision level")

    @field_validator("city", "area", "state", "country", "location_label", "google_place_id", "formatted_address", "postal_code")
    @classmethod
    def clean_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_cleaned = v.strip()
            return v_cleaned if v_cleaned else None
        return v

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


class LocationCreate(LocationBase):
    pass


class LocationUpdate(LocationBase):
    pass


class LocationResponse(LocationBase):
    id: uuid.UUID
    user_id: uuid.UUID
    country: str
    location_label: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RequestLocationResponse(BaseModel):
    id: uuid.UUID
    request_id: uuid.UUID
    google_place_id: Optional[str] = None
    formatted_address: Optional[str] = None
    city: Optional[str] = None
    area: Optional[str] = None
    state: Optional[str] = None
    country: str = "India"
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_source: str = "nlp_resolved"
    location_precision: str = "approximate"
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
