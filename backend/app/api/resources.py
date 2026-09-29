from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.resource import ResourceCategoriesResponse, ResourceSearchResponse
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
    radius_meters: int = Query(5000, ge=500, le=25000, description="Search radius in meters"),
    limit: int = Query(10, ge=1, le=20, description="Maximum number of results to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResourceSearchResponse:
    """
    Search and rank real local resources using Google Places API (New).
    - If request_id is provided, automatically uses the request's target location and extracted requirements.
    - Requires authentication to protect private request data.
    - Never exposes user's private home or device coordinates.
    - Returns real Google Places results with transparent ranking and strict nulls for missing provider fields.
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
        limit=limit,
    )
