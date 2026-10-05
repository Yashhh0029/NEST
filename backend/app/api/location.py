import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, get_db
from app.models.request import Request
from app.models.user import User
from app.schemas.google_location import (
    AutocompleteRequest,
    AutocompleteResponse,
    ResolveTextRequest,
    ResolvedLocation,
    ReverseGeocodeRequest,
)
from app.schemas.location import RequestLocationResponse
from app.services.google_maps_service import google_maps_service
from app.services.location_service import get_request_target_location

router = APIRouter()


@router.get(
    "/autocomplete",
    response_model=AutocompleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Search Indian places, cities, and localities via Google Places API (New) (GET)",
)
def autocomplete_places_get(
    input_text: str = Query(..., min_length=1, max_length=200),
    session_token: Optional[str] = Query(None),
    latitude: Optional[float] = Query(None, ge=-90.0, le=90.0),
    longitude: Optional[float] = Query(None, ge=-180.0, le=180.0),
    radius_meters: Optional[float] = Query(None, ge=100.0, le=100000.0),
) -> AutocompleteResponse:
    predictions = google_maps_service.autocomplete_places(
        input_text=input_text,
        session_token=session_token,
        latitude=latitude,
        longitude=longitude,
        radius_meters=radius_meters,
    )
    return AutocompleteResponse(predictions=predictions)


@router.post(
    "/autocomplete",
    response_model=AutocompleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Search Indian places, cities, and localities via Google Places API (New) (POST)",
)
def autocomplete_places(
    payload: AutocompleteRequest,
) -> AutocompleteResponse:
    """
    Search places and localities in India using Google Places API (New).
    Falls back gracefully to empty list if service is unconfigured or unreachable.
    """
    predictions = google_maps_service.autocomplete_places(
        input_text=payload.input_text,
        session_token=payload.session_token,
        latitude=payload.latitude,
        longitude=payload.longitude,
        radius_meters=payload.radius_meters,
    )
    return AutocompleteResponse(predictions=predictions)


@router.post(
    "/reverse-geocode",
    response_model=ResolvedLocation,
    status_code=status.HTTP_200_OK,
    summary="Reverse geocode GPS coordinates to city, area, and state",
)
def reverse_geocode(
    payload: ReverseGeocodeRequest,
) -> ResolvedLocation:
    """
    Convert browser GPS coordinates into structured locality, city, state, and country.
    """
    resolved = google_maps_service.reverse_geocode(
        latitude=payload.latitude,
        longitude=payload.longitude,
    )
    if not resolved:
        # Fallback response without fabricated coordinates
        return ResolvedLocation(
            latitude=payload.latitude,
            longitude=payload.longitude,
            city=None,
            area=None,
            country="India",
            location_source="browser_unresolved",
            location_precision="rooftop",
        )
    return resolved


@router.post(
    "/resolve",
    response_model=ResolvedLocation,
    status_code=status.HTTP_200_OK,
    summary="Resolve address or locality text into canonical Google Place with coordinates",
)
def resolve_address(
    payload: ResolveTextRequest,
) -> ResolvedLocation:
    """
    Forward geocode an address string (e.g. 'Baner, Pune' or 'Whitefield, Bengaluru') into a canonical place.
    """
    resolved = google_maps_service.geocode_address(payload.text)
    if not resolved:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not resolve location for '{payload.text}'. Please select from suggestions or enter manually.",
        )
    return resolved


@router.get(
    "/place/{place_id}",
    response_model=ResolvedLocation,
    status_code=status.HTTP_200_OK,
    summary="Fetch canonical place details using Google Place ID",
)
def get_place_details(
    place_id: str,
) -> ResolvedLocation:
    """
    Retrieve place coordinates and formatted address by Google Place ID.
    """
    resolved = google_maps_service.get_place_details(place_id)
    if not resolved:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Place details not found for ID '{place_id}'.",
        )
    return resolved


@router.get(
    "/request/{request_id}",
    response_model=RequestLocationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get dedicated target location for a request",
)
def get_target_location_for_request(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RequestLocationResponse:
    """
    Retrieve the independent target location where the request needs help.
    """
    req = db.query(Request).filter(Request.id == request_id).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")

    target_loc = get_request_target_location(db, request_id)
    if not target_loc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target location not set for this request.")

    return RequestLocationResponse.model_validate(target_loc)
