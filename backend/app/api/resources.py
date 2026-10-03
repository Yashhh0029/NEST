from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.resource import (
    NearbyHelpersResponse,
    ResourceCategoriesResponse,
    ResourceSearchResponse,
)
from app.services import resource_service

router = APIRouter(prefix="/resources", tags=["Local Resources & Places"])



@router.get(
    "/categories",
    response_model=ResourceCategoriesResponse,
    status_code=status.HTTP_200_OK,
    summary="List all supported local resource categories",
)
def get_resource_categories() -> ResourceCategoriesResponse:
    """
    Retrieve all 15 supported NEST resource discovery categories with icons and descriptions.
    Public metadata endpoint.
    """
    return resource_service.get_all_categories()


@router.get(
    "/search",
    response_model=ResourceSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Discover and rank real local places and services",
)
def search_resources(
    request_id: Optional[uuid.UUID] = Query(None, description="Request ID to derive target location and requirements from"),
    category: Optional[str] = Query(None, description="Resource category filter (e.g. accommodation, food, hospitals)"),
    query: Optional[str] = Query(None, description="Custom search terms (e.g. vegetarian tiffin, ladies pg)"),
    latitude: Optional[float] = Query(None, ge=-90.0, le=90.0, description="Manual search origin latitude"),
    longitude: Optional[float] = Query(None, ge=-180.0, le=180.0, description="Manual search origin longitude"),
    radius_meters: Optional[int] = Query(None, ge=50, le=50000, description="Search radius in meters (100m, 250m, 500m, 1000m, etc.)"),
    min_lat: Optional[float] = Query(None, ge=-90.0, le=90.0, description="Viewport bounding box minimum latitude"),
    max_lat: Optional[float] = Query(None, ge=-90.0, le=90.0, description="Viewport bounding box maximum latitude"),
    min_lon: Optional[float] = Query(None, ge=-180.0, le=180.0, description="Viewport bounding box minimum longitude"),
    max_lon: Optional[float] = Query(None, ge=-180.0, le=180.0, description="Viewport bounding box maximum longitude"),
    provider: Optional[str] = Query(None, description="Preferred provider: 'google', 'osm', or 'auto'"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResourceSearchResponse:
    """
    Search and rank real local resources using Google Places API (New) or OpenStreetMap.
    - If request_id is provided, automatically uses the request's target location and extracted requirements.
    - Requires authentication to protect private request data.
    - Never exposes user's private home or device coordinates.
    - Returns real provider results with transparent ranking and strict nulls for missing fields.
    """
    return resource_service.search_local_resources(
        db=db,
        current_user=current_user,
        request_id=request_id,
        category=category,
        query=query,
        latitude=latitude,
        longitude=longitude,
        radius_meters=radius_meters,
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        provider=provider,
        limit=limit,
    )


@router.get(
    "/helpers",
    response_model=NearbyHelpersResponse,
    status_code=status.HTTP_200_OK,
    summary="Discover real verified NEST community helpers in the exploration area",
)
def get_nearby_helpers(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Center latitude of exploration area"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Center longitude of exploration area"),
    radius_km: float = Query(15.0, ge=1.0, le=50.0, description="Radius in kilometers"),
    request_id: Optional[uuid.UUID] = Query(None, description="Optional request ID context"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NearbyHelpersResponse:
    """
    Retrieve real, eligible, active NEST community helpers near coordinates.
    - NEVER fabricates fake helpers or placeholder data.
    - Returns empty list if no helpers are found.
    - Excludes requesting user and blocked/suspended users.
    - Applies privacy protection (approximate coordinates only).
    """
    return resource_service.get_nearby_helpers(
        db=db,
        current_user=current_user,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        request_id=request_id,
    )

