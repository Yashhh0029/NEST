from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ResourceCategory(BaseModel):
    id: str = Field(..., description="Unique category slug")
    display_name: str = Field(..., description="Human-readable category title")
    icon: str = Field(..., description="Lucide icon name identifier")
    description: str = Field(..., description="Description of services covered")
    default_query_terms: List[str] = Field(default_factory=list, description="Keywords used in query construction")

    model_config = ConfigDict(from_attributes=True)


class ResourceItem(BaseModel):
    id: str = Field(..., description="Google place identifier")
    name: str = Field(..., description="Official place display name")
    category: str = Field(..., description="Assigned NEST category slug")
    category_display_name: str = Field(..., description="Assigned NEST category title")
    formatted_address: Optional[str] = Field(None, description="Public street address")
    latitude: Optional[float] = Field(None, description="Public place latitude")
    longitude: Optional[float] = Field(None, description="Public place longitude")
    distance_km: Optional[float] = Field(None, description="Great-circle distance from search center in km")
    rating: Optional[float] = Field(None, description="Google Places star rating (1.0 to 5.0) or null if unrated")
    review_count: Optional[int] = Field(None, description="Number of user reviews or null if unavailable")
    price_level: Optional[str] = Field(None, description="Price tier (e.g. INEXPENSIVE, MODERATE, EXPENSIVE) or null")
    is_open_now: Optional[bool] = Field(None, description="Whether currently open or null if schedule unavailable")
    google_place_id: str = Field(..., description="Canonical Google Place ID")
    maps_url: Optional[str] = Field(None, description="Direct Google Maps URL")
    website_url: Optional[str] = Field(None, description="Official website URL")
    phone_number: Optional[str] = Field(None, description="Contact phone number")
    primary_type: Optional[str] = Field(None, description="Google place primary type")
    ranking_score: float = Field(0.0, description="Normalized transparent ranking score between 0.0 and 1.0")
    ranking_reasons: List[str] = Field(default_factory=list, description="Transparent explanations for result ordering")

    model_config = ConfigDict(from_attributes=True)


class SearchCenter(BaseModel):
    latitude: Optional[float] = Field(None, description="Search origin latitude")
    longitude: Optional[float] = Field(None, description="Search origin longitude")
    label: Optional[str] = Field(None, description="City / locality label for search center")

    model_config = ConfigDict(from_attributes=True)


class ResourceSearchResponse(BaseModel):
    status: str = Field(..., description="Status: SUCCESS, NO_RESULTS, or PROVIDER_UNAVAILABLE")
    total: int = Field(0, description="Total resources found")
    resources: List[ResourceItem] = Field(default_factory=list, description="Ranked list of real local places")
    search_center: Optional[SearchCenter] = Field(None, description="Resolved search center")
    category: Optional[str] = Field(None, description="Applied NEST category filter")
    query: str = Field("", description="Effective text query executed against provider")
    radius_meters: int = Field(5000, description="Search radius in meters")

    model_config = ConfigDict(from_attributes=True)


class ResourceCategoriesResponse(BaseModel):
    total: int = Field(..., description="Total available categories")
    categories: List[ResourceCategory] = Field(..., description="List of supported categories")

    model_config = ConfigDict(from_attributes=True)
