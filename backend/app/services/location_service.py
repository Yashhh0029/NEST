import logging
from typing import Optional
import uuid
from sqlalchemy.orm import Session
from app.models.location import Location
from app.models.request import Request
from app.models.request_location import RequestLocation
from app.models.user import User
from app.schemas.google_location import ResolvedLocation
from app.services.google_maps_service import google_maps_service

logger = logging.getLogger(__name__)


def resolve_and_upsert_request_location(
    db: Session,
    request_id: uuid.UUID,
    user: User,
    city_hint: Optional[str] = None,
    area_hint: Optional[str] = None,
    google_place_id: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    formatted_address: Optional[str] = None,
) -> Optional[RequestLocation]:
    """
    Resolve and persist the target location for a request.
    Strictly isolates request target location from user profile home location.
    
    1. If google_place_id provided: fetches canonical details from Google.
    2. Else if coordinates provided: reverse geocodes coordinates.
    3. Else if city_hint or area_hint provided: forward geocodes location query.
    4. If Google is unavailable: stores hints without fabricating coordinates.
    """
    req = db.query(Request).filter(Request.id == request_id).first()
    if not req:
        return None

    resolved: Optional[ResolvedLocation] = None

    if google_place_id:
        resolved = google_maps_service.get_place_details(google_place_id)

    if not resolved and latitude is not None and longitude is not None:
        resolved = google_maps_service.reverse_geocode(latitude, longitude)
        if not resolved:
            # When Google reverse geocoding is unavailable, preserve legitimate coordinates
            resolved = ResolvedLocation(
                latitude=latitude,
                longitude=longitude,
                city=city_hint,
                area=area_hint,
                formatted_address=formatted_address or ", ".join(filter(None, [area_hint, city_hint])),
                location_source="browser_geolocation",
                location_precision="rooftop",
            )

    if not resolved and (city_hint or area_hint):
        query = ", ".join(filter(None, [area_hint, city_hint, "India"]))
        resolved = google_maps_service.geocode_address(query)

    # Find or create RequestLocation
    existing_req_loc = db.query(RequestLocation).filter(RequestLocation.request_id == request_id).first()

    if resolved:
        if city_hint and resolved.city and area_hint and resolved.city.strip().lower() == area_hint.strip().lower():
            final_city = city_hint
            final_area = area_hint
        else:
            final_city = resolved.city or city_hint
            final_area = resolved.area or area_hint
        final_state = resolved.state
        final_country = resolved.country or "India"
        final_postal = resolved.postal_code
        final_lat = resolved.latitude
        final_lon = resolved.longitude
        final_place_id = resolved.google_place_id
        final_display_name = resolved.display_name or resolved.name
        final_formatted = resolved.formatted_address or formatted_address
        final_source = resolved.location_source
        final_precision = resolved.location_precision
    else:
        # Fallback when Google resolution is unavailable: preserve user hints, never fabricate coordinates
        final_city = city_hint
        final_area = area_hint
        final_state = None
        final_country = "India"
        final_postal = None
        final_lat = latitude
        final_lon = longitude
        final_place_id = google_place_id
        final_display_name = None
        final_formatted = formatted_address or ", ".join(filter(None, [area_hint, city_hint]))
        final_source = "nlp_unresolved"
        final_precision = "approximate"

    if existing_req_loc:
        existing_req_loc.google_place_id = final_place_id
        existing_req_loc.display_name = final_display_name
        existing_req_loc.formatted_address = final_formatted
        existing_req_loc.city = final_city
        existing_req_loc.area = final_area
        existing_req_loc.state = final_state
        existing_req_loc.country = final_country
        existing_req_loc.postal_code = final_postal
        existing_req_loc.latitude = final_lat
        existing_req_loc.longitude = final_lon
        existing_req_loc.location_source = final_source
        existing_req_loc.location_precision = final_precision
        db.commit()
        db.refresh(existing_req_loc)
        return existing_req_loc
    else:
        new_req_loc = RequestLocation(
            request_id=request_id,
            google_place_id=final_place_id,
            display_name=final_display_name,
            formatted_address=final_formatted,
            city=final_city,
            area=final_area,
            state=final_state,
            country=final_country,
            postal_code=final_postal,
            latitude=final_lat,
            longitude=final_lon,
            location_source=final_source,
            location_precision=final_precision,
        )
        db.add(new_req_loc)
        db.commit()
        db.refresh(new_req_loc)
        return new_req_loc


def get_request_target_location(db: Session, request_id: uuid.UUID) -> Optional[RequestLocation]:
    """Retrieve the dedicated target location for a request."""
    return db.query(RequestLocation).filter(RequestLocation.request_id == request_id).first()
