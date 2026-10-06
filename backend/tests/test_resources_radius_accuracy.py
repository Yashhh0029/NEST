import uuid
from unittest.mock import MagicMock
import pytest
from app.services.google_maps_service import GoogleMapsService
from app.services.resource_service import (
    search_local_resources,
    rank_and_explain_resources,
    haversine_km,
)
from app.models.user import User


def test_resolve_indian_coordinates_generic_fallback():
    """Verify Indian coordinates fallback preserves exact coordinates without fabricating locality or defaulting to Kothrud."""
    loc = GoogleMapsService.resolve_indian_coordinates(18.57, 73.75)
    assert loc is not None
    assert loc.latitude == 18.57
    assert loc.longitude == 73.75
    assert loc.country == "India"
    assert loc.area is None
    assert loc.city is None
    assert loc.taluka is None
    assert loc.district is None
    assert loc.postal_code is None
    assert loc.formatted_address == "India"
    assert "Kothrud" not in (loc.formatted_address or "")



def test_strict_radius_enforcement_excludes_distant_places():
    """Verify that a 100 m search strictly excludes places beyond 100 m (including 9.4 km places)."""
    # Search origin: Mahalunge (18.57, 73.75)
    search_lat = 18.57
    search_lon = 73.75

    # 1. Place at ~50 meters
    place_50m = {
        "id": "place_close",
        "displayName": {"text": "Local PG Next Door"},
        "formattedAddress": "Mahalunge, Pune",
        "location": {"latitude": 18.5703, "longitude": 73.7503},
    }
    # 2. Place at ~917 meters
    place_900m = {
        "id": "place_medium",
        "displayName": {"text": "Balewadi Residency"},
        "formattedAddress": "Balewadi, Pune",
        "location": {"latitude": 18.578, "longitude": 73.753},
    }
    # 3. Place at ~9.4 km (Kothrud Shri Sai Boy's Hostel)
    place_9km = {
        "id": "place_far",
        "displayName": {"text": "Shri Sai Boy's Hostel"},
        "formattedAddress": "Kothrud, Pune",
        "location": {"latitude": 18.50, "longitude": 73.81},
    }

    mock_maps = MagicMock(spec=GoogleMapsService)
    mock_maps.is_configured = True
    # search_places_nearby returns all raw results
    mock_maps.search_places_nearby.return_value = [place_50m]
    # search_places_text returns raw text results including distant place
    mock_maps.search_places_text.return_value = [place_900m, place_9km]
    mock_maps.reverse_geocode.return_value = GoogleMapsService.resolve_indian_coordinates(search_lat, search_lon)

    mock_db = MagicMock()
    mock_user = MagicMock(spec=User)
    mock_user.id = uuid.uuid4()

    # Search with radius_meters=100
    res_100m = search_local_resources(
        db=mock_db,
        current_user=mock_user,
        latitude=search_lat,
        longitude=search_lon,
        radius_meters=100,
        maps_service=mock_maps,
    )

    assert res_100m.status == "SUCCESS"
    assert res_100m.total == 1
    # Only place_50m should be returned! place_900m and place_9km MUST be excluded!
    place_ids = [r.id for r in res_100m.resources]
    assert "place_close" in place_ids
    assert "place_medium" not in place_ids
    assert "place_far" not in place_ids
    assert res_100m.resources[0].distance_km is not None
    assert res_100m.resources[0].distance_km <= 0.100


def test_zero_results_when_none_within_radius():
    """Verify that when no places exist within radius, NO distant fallbacks are returned."""
    search_lat = 18.57
    search_lon = 73.75

    # Only a 9.4 km distant place returned by raw text search
    place_9km = {
        "id": "place_far",
        "displayName": {"text": "Shri Sai Boy's Hostel"},
        "formattedAddress": "Kothrud, Pune",
        "location": {"latitude": 18.50, "longitude": 73.81},
    }

    mock_maps = MagicMock(spec=GoogleMapsService)
    mock_maps.is_configured = True
    mock_maps.search_places_nearby.return_value = []
    mock_maps.search_places_text.return_value = [place_9km]
    mock_maps.reverse_geocode.return_value = GoogleMapsService.resolve_indian_coordinates(search_lat, search_lon)

    mock_db = MagicMock()
    mock_user = MagicMock(spec=User)
    mock_user.id = uuid.uuid4()

    res = search_local_resources(
        db=mock_db,
        current_user=mock_user,
        latitude=search_lat,
        longitude=search_lon,
        radius_meters=100,
        maps_service=mock_maps,
    )

    # Must be NO_RESULTS with 0 items, NEVER falling back to place_9km!
    assert res.status == "NO_RESULTS"
    assert res.total == 0
    assert len(res.resources) == 0


def test_rank_and_explain_resources_strict_filter():
    """Verify rank_and_explain_resources discards any place exceeding radius_km."""
    search_lat = 18.57
    search_lon = 73.75

    places = [
        {
            "id": "close_place",
            "displayName": {"text": "Close PG"},
            "location": {"latitude": 18.5705, "longitude": 73.7505},
        },
        {
            "id": "far_place",
            "displayName": {"text": "Far PG"},
            "location": {"latitude": 18.50, "longitude": 73.81},
        },
    ]

    ranked = rank_and_explain_resources(
        resources=places,
        search_lat=search_lat,
        search_lon=search_lon,
        radius_meters=200.0,
        category_id="accommodation",
        preferences=[],
    )

    assert len(ranked) == 1
    assert ranked[0].id == "close_place"
