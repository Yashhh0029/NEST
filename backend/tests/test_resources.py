import uuid
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from app.services.google_maps_service import GoogleMapsService
from app.services.resource_service import CATEGORIES_REGISTRY, resolve_category_from_need
from tests.conftest import create_authenticated_user


def test_resource_categories_endpoint(client: TestClient):
    """GET /api/resources/categories returns all 15 functional categories."""
    resp = client.get("/api/resources/categories")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 15
    assert len(data["categories"]) == 15

    cat_ids = {c["id"] for c in data["categories"]}
    expected_categories = {
        "accommodation",
        "food",
        "restaurants",
        "hospitals",
        "clinics",
        "pharmacies",
        "banks",
        "atms",
        "grocery",
        "public_transport",
        "gyms",
        "coworking",
        "education",
        "government_services",
        "repairs",
    }
    assert expected_categories.issubset(cat_ids)

    # Verify every category has query terms and functional definition
    for cat in data["categories"]:
        assert len(cat["default_query_terms"]) > 0
        assert cat["display_name"]
        assert cat["icon"]
        assert cat["description"]


def test_category_mapping_from_needs():
    """Verify Phase 3 need categories map correctly to NEST resource categories."""
    assert resolve_category_from_need("accommodation") == "accommodation"
    assert resolve_category_from_need("food") in ["food", "restaurants", "grocery"]
    assert resolve_category_from_need("transport") == "public_transport"
    assert resolve_category_from_need("healthcare") in ["hospitals", "clinics", "pharmacies"]
    assert resolve_category_from_need("education") == "education"
    assert resolve_category_from_need("documentation") in ["banks", "atms", "government_services"]
    assert resolve_category_from_need("jobs") == "coworking"
    assert resolve_category_from_need("unknown_need_xyz") is None


def test_resource_search_requires_authentication(client: TestClient):
    """Unauthenticated search attempts return 401."""
    resp = client.get("/api/resources/search")
    assert resp.status_code == 401


def test_resource_search_request_authorization(client: TestClient):
    """Cannot search resources using another user's private request ID."""
    user1 = create_authenticated_user(client, "Req Owner", "req_owner_p10@example.test")
    user2 = create_authenticated_user(client, "Req Intruder", "req_intruder_p10@example.test")

    req_resp = client.post(
        "/api/requests",
        headers=user1["headers"],
        json={"text": "Looking for 1BHK in Hinjewadi Phase 1"},
    )
    request_id = req_resp.json()["id"]

    # Intruder tries to search with User 1's request_id
    resp = client.get(
        f"/api/resources/search?request_id={request_id}",
        headers=user2["headers"],
    )
    assert resp.status_code == 403
    assert "permission" in resp.json()["detail"].lower()

    # Nonexistent request returns 404
    fake_id = str(uuid.uuid4())
    resp404 = client.get(
        f"/api/resources/search?request_id={fake_id}",
        headers=user1["headers"],
    )
    assert resp404.status_code == 404


@patch.object(GoogleMapsService, "search_places_text")
@patch.object(GoogleMapsService, "is_configured", True)
def test_resource_normalization_and_strict_nulls(mock_search: MagicMock, client: TestClient):
    """Verify Google Places response normalization preserves nulls for missing provider fields."""
    user = create_authenticated_user(client, "Search User", "search_user_p10@example.test")

    # Mock provider returning 2 places: 1 with full details, 1 with missing ratings/hours/prices
    mock_search.return_value = [
        {
            "id": "places/ChIJ123456",
            "displayName": {"text": "Sunrise Executive PG"},
            "formattedAddress": "Hinjewadi Phase 1, Pune, Maharashtra",
            "location": {"latitude": 18.5913, "longitude": 73.7389},
            "rating": 4.3,
            "userRatingCount": 85,
            "priceLevel": "PRICE_LEVEL_INEXPENSIVE",
            "regularOpeningHours": {"openNow": True},
            "googleMapsUri": "https://maps.google.com/?cid=123",
            "websiteUri": "https://sunrisepg.example",
            "nationalPhoneNumber": "+91 98765 43210",
            "primaryType": "lodging",
            "types": ["lodging", "point_of_interest"],
        },
        {
            "id": "places/ChIJ789012",
            "displayName": {"text": "Local Homestay Tiffin"},
            "formattedAddress": "Near Rajiv Gandhi Infotech Park, Hinjewadi",
            "location": {"latitude": 18.5950, "longitude": 73.7400},
            # Missing rating, userRatingCount, priceLevel, regularOpeningHours, website, phone
            "rating": None,
            "userRatingCount": None,
            "priceLevel": None,
            "regularOpeningHours": None,
            "googleMapsUri": "https://maps.google.com/?cid=456",
            "websiteUri": None,
            "nationalPhoneNumber": None,
            "primaryType": "restaurant",
            "types": ["restaurant"],
        },
    ]

    with patch.object(GoogleMapsService, "search_places_nearby", return_value=[]):
        resp = client.get(
            "/api/resources/search?category=accommodation&latitude=18.5913&longitude=73.7389&radius_meters=5000",
            headers=user["headers"],
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["total"] == 2
    items = data["resources"]

    # 1. Place with full data
    p1 = items[0]
    assert p1["name"] == "Sunrise Executive PG"
    assert p1["rating"] == 4.3
    assert p1["review_count"] == 85
    assert p1["price_level"] == "INEXPENSIVE"
    assert p1["is_open_now"] is True
    assert p1["distance_km"] == 0.0  # Exact match with search coords
    assert p1["ranking_score"] > 0.0
    assert len(p1["ranking_reasons"]) > 0

    # 2. Place with missing fields: MUST remain null, never fabricated
    p2 = items[1]
    assert p2["name"] == "Local Homestay Tiffin"
    assert p2["rating"] is None
    assert p2["review_count"] is None
    assert p2["price_level"] is None
    assert p2["is_open_now"] is None
    assert p2["website_url"] is None
    assert p2["phone_number"] is None
    # Unrated place must still have a valid ranking score without being crashed or treated as 0
    assert p2["ranking_score"] > 0.0


@patch.object(GoogleMapsService, "search_places_text")
@patch.object(GoogleMapsService, "is_configured", True)
def test_ranking_review_volume_does_not_overpower_distance(mock_search: MagicMock, client: TestClient):
    """
    Adjustment 1: Review volume is strictly a confidence factor (5%) and must
    not overpower closer distance or relevance.
    """
    user = create_authenticated_user(client, "Rank User", "rank_user_p10@example.test")

    # Place A: Very close (0.2 km), moderate reviews (20 reviews, rating 4.5)
    # Place B: Far away (4.8 km), viral reviews (2000 reviews, rating 4.5)
    mock_search.return_value = [
        {
            "id": "place_b_far",
            "displayName": {"text": "Famous Far Away PG"},
            "formattedAddress": "Far outskirts",
            "location": {"latitude": 18.5600, "longitude": 73.7200},  # ~4.0 km away (within 5 km radius)
            "rating": 4.5,
            "userRatingCount": 2000,
            "types": ["lodging"],
        },
        {
            "id": "place_a_close",
            "displayName": {"text": "Local Neighbor PG"},
            "formattedAddress": "Next door",
            "location": {"latitude": 18.5910, "longitude": 73.7380},  # ~0.1 km away
            "rating": 4.5,
            "userRatingCount": 20,
            "types": ["lodging"],
        },
    ]

    with patch.object(GoogleMapsService, "search_places_nearby", return_value=[]):
        resp = client.get(
            "/api/resources/search?category=accommodation&latitude=18.5913&longitude=73.7389&radius_meters=5000",
            headers=user["headers"],
        )
    assert resp.status_code == 200
    items = resp.json()["resources"]

    # Place A (close) should rank higher than Place B (far away) despite Place B having 2000 reviews
    assert items[0]["id"] == "place_a_close"
    assert items[1]["id"] == "place_b_far"


@patch.object(GoogleMapsService, "search_places_text")
@patch.object(GoogleMapsService, "is_configured", True)
def test_unrated_place_is_not_penalized_with_zero(mock_search: MagicMock, client: TestClient):
    """
    Adjustment 2: Missing Google rating MUST remain unavailable/null.
    Never convert to 0 and never penalize unrated resources.
    """
    user = create_authenticated_user(client, "Rating User", "rating_user_p10@example.test")

    mock_search.return_value = [
        {
            "id": "unrated_place",
            "displayName": {"text": "New Clean PG"},
            "formattedAddress": "Hinjewadi Phase 1",
            "location": {"latitude": 18.5913, "longitude": 73.7389},
            "rating": None,  # Unrated
            "userRatingCount": None,
            "types": ["lodging"],
        },
    ]

    with patch.object(GoogleMapsService, "search_places_nearby", return_value=[]):
        resp = client.get(
            "/api/resources/search?category=accommodation&latitude=18.5913&longitude=73.7389",
            headers=user["headers"],
        )
    assert resp.status_code == 200
    item = resp.json()["resources"][0]
    assert item["rating"] is None
    # Neutral rating baseline (0.5) ensures unrated places get a healthy score based on distance
    assert item["ranking_score"] >= 0.5


def test_provider_unavailable_when_google_not_configured(client: TestClient):
    """
    Adjustment 10: When Google Places is unconfigured or unavailable,
    return an honest PROVIDER_UNAVAILABLE status. Never substitute fake businesses.
    """
    user = create_authenticated_user(client, "Fallback User", "fallback_user_p10@example.test")

    with patch.object(GoogleMapsService, "is_configured", False):
        resp = client.get(
            "/api/resources/search?category=food&latitude=18.5913&longitude=73.7389",
            headers=user["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "PROVIDER_UNAVAILABLE"
        assert data["total"] == 0
        assert data["resources"] == []


@patch.object(GoogleMapsService, "search_places_text")
@patch.object(GoogleMapsService, "is_configured", True)
def test_request_target_location_isolation(mock_search: MagicMock, client: TestClient):
    """
    Adjustment 6 & 7: Verify search uses the request target location,
    strictly isolating it from user home profile location and not exposing private coordinates.
    """
    user = create_authenticated_user(client, "Privacy User", "privacy_user_p10@example.test")

    # Set user's home location to Bengaluru Indiranagar
    client.post(
        "/api/profile/locations",
        headers=user["headers"],
        json={"city": "Bengaluru", "area": "Indiranagar", "latitude": 12.9784, "longitude": 77.6408},
    )

    # Create request targeting Pune Hinjewadi
    req_resp = client.post(
        "/api/requests",
        headers=user["headers"],
        json={"text": "Need vegetarian tiffin service in Pune Hinjewadi near office"},
    )
    request_id = req_resp.json()["id"]

    mock_search.return_value = [
        {
            "id": "tiffin_1",
            "displayName": {"text": "Annapurna Veg Tiffin"},
            "formattedAddress": "Hinjewadi Phase 2, Pune",
            "location": {"latitude": 18.5920, "longitude": 73.7350},
            "rating": 4.6,
            "userRatingCount": 35,
            "types": ["meal_delivery", "restaurant"],
        }
    ]

    resp = client.get(
        f"/api/resources/search?request_id={request_id}",
        headers=user["headers"],
    )
    assert resp.status_code == 200
    data = resp.json()

    # Verify search center is Pune Hinjewadi (request target location), NOT Bengaluru (user home)
    assert "pune" in data["search_center"]["label"].lower() or "hinjewadi" in data["search_center"]["label"].lower()
    assert mock_search.called
    call_args = mock_search.call_args[1]
    # Coordinates passed to Google should be Pune coordinates (~18.59), not Bengaluru (~12.97)
    assert call_args["latitude"] is not None and 18.0 <= call_args["latitude"] <= 19.0


def test_osm_provider_search_and_viewport(client: TestClient):
    """
    Verify OpenStreetMap provider operates without Google Maps API key,
    honestly preserving null ratings and returning real OSM verified entities.
    """
    user = create_authenticated_user(client, "OSM User", "osm_user_p10@example.test")

    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [
            {
                "place_id": 123456,
                "osm_type": "node",
                "osm_id": 987654,
                "lat": "10.0165",
                "lon": "76.3427",
                "name": "Kakkanad Ladies PG & Hostel",
                "display_name": "Kakkanad Ladies PG & Hostel, Infopark Road, Kakkanad, Kochi, Kerala",
                "type": "hostel",
                "address": {
                    "tourism": "Kakkanad Ladies PG & Hostel",
                    "road": "Infopark Road",
                    "suburb": "Kakkanad",
                    "city": "Kochi",
                },
            }
        ]

        resp = client.get(
            "/api/resources/search?category=accommodation&provider=osm&latitude=10.016&longitude=76.342&min_lat=10.00&max_lat=10.05&min_lon=76.30&max_lon=76.38",
            headers=user["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCESS"
        assert data["provider"] == "openstreetmap"
        assert data["total"] == 1
        place = data["resources"][0]
        assert place["name"] == "Kakkanad Ladies PG & Hostel"
        assert place["rating"] is None  # Strictly null: no fake ratings
        assert place["review_count"] is None
        assert "openstreetmap.org" in place["maps_url"]
        assert any("OpenStreetMap" in r for r in place["ranking_reasons"])


def test_nearby_helpers_real_data_and_eligibility_scenarios(client: TestClient):
    """
    Verify Real NEST Community Helper Eligibility Scenarios:
    - Scenario A: Kothrud with zero enrolled helpers returns total=0, helpers=[] (ZERO fake markers).
    - Scenario B: Genuinely eligible helper in Kothrud appears with privacy-protected coords.
    - Scenario C: Deactivating that test account immediately causes helper to disappear.
    """
    from app.db.database import SessionLocal
    from app.models.location import Location
    from app.models.profile import Profile
    from app.models.user import User, UserRole

    db = SessionLocal()
    try:
        requester = create_authenticated_user(client, "Seeking Newcomer", "newcomer_seeking@example.test")

        # 1. Scenario A: Zero eligible helpers in Kothrud, Pune (lat: 18.5074, lon: 73.8077)
        resp = client.get(
            "/api/resources/helpers?latitude=18.5074&longitude=73.8077&radius_km=15.0",
            headers=requester["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["helpers"] == []

        # 2. Scenario B: Create ONE real eligible helper in Kothrud
        helper_user = create_authenticated_user(client, "Rahul Kothrud Helper", "rahul_kothrud@example.test", role="helper")
        user_id_str = helper_user["user"]["id"]
        # Set role to helper, verified email, active
        user_db = db.query(User).filter(User.id == user_id_str).first()
        user_db.role = UserRole.HELPER
        user_db.email_verified = True
        user_db.is_active = True


        # Add Primary Location in Kothrud
        loc = Location(
            user_id=user_db.id,
            location_label="Primary",
            area="Kothrud",
            city="Pune",
            state="Maharashtra",
            country="India",
            latitude=18.5074,
            longitude=73.8077,
            location_source="manual",
        )
        db.add(loc)
        db.commit()

        # Query again: exactly ONE helper appears
        resp2 = client.get(
            "/api/resources/helpers?latitude=18.5074&longitude=73.8077&radius_km=15.0",
            headers=requester["headers"],
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["total"] == 1
        assert len(data2["helpers"]) == 1
        h = data2["helpers"][0]
        assert h["user_id"] == str(user_db.id)
        assert h["name"] == "Rahul Kothrud Helper"
        assert h["city"] == "Pune"
        assert h["area"] == "Kothrud"
        # Privacy check: coords are rounded to 2 decimals (~1.1 km precision)
        assert h["approximate_latitude"] == 18.51
        assert h["approximate_longitude"] == 73.81
        assert h["distance_km"] == 0.0

        # 3. Scenario C: Deactivate that helper account
        user_db.is_active = False
        db.commit()

        # Query again: helper marker disappears (returns total=0)
        resp3 = client.get(
            "/api/resources/helpers?latitude=18.5074&longitude=73.8077&radius_km=15.0",
            headers=requester["headers"],
        )
        assert resp3.status_code == 200
        data3 = resp3.json()
        assert data3["total"] == 0
        assert data3["helpers"] == []
    finally:
        db.close()



