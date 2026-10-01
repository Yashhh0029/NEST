import uuid
import pytest
from fastapi.testclient import TestClient
from tests.conftest import create_authenticated_user
from app.schemas.google_location import (
    PlaceAutocompletePrediction,
    ResolvedLocation,
    TravelRouteInfo,
)
from app.services.google_maps_service import google_maps_service


@pytest.fixture(autouse=True)
def mock_google_maps_services(monkeypatch):
    """
    Mock Google Maps API calls for predictable, deterministic test behavior
    without requiring external network calls or a paid Google Maps Platform API key.
    """
    def mock_autocomplete(input_text: str, session_token: str = None):
        if not input_text or len(input_text.strip()) == 0:
            return []
        return [
            PlaceAutocompletePrediction(
                place_id="ChIJ_bengaluru_whitefield",
                main_text="Whitefield",
                secondary_text="Bengaluru, Karnataka, India",
                description="Whitefield, Bengaluru, Karnataka, India",
            ),
            PlaceAutocompletePrediction(
                place_id="ChIJ_bengaluru_indiranagar",
                main_text="Indiranagar",
                secondary_text="Bengaluru, Karnataka, India",
                description="Indiranagar, Bengaluru, Karnataka, India",
            ),
        ]

    def mock_geocode(address: str):
        norm = address.lower()
        if "whitefield" in norm or "bengaluru" in norm or "bangalore" in norm:
            return ResolvedLocation(
                google_place_id="ChIJ_bengaluru_whitefield",
                formatted_address="Whitefield, Bengaluru, Karnataka, India",
                city="Bengaluru",
                area="Whitefield",
                state="Karnataka",
                country="India",
                postal_code="560066",
                latitude=12.9698,
                longitude=77.7500,
                location_precision="neighborhood",
                location_source="google_geocoding",
            )
        elif "nagpur" in norm:
            return ResolvedLocation(
                google_place_id="ChIJ_nagpur",
                formatted_address="Nagpur, Maharashtra, India",
                city="Nagpur",
                area="Dharampeth",
                state="Maharashtra",
                country="India",
                postal_code="440010",
                latitude=21.1458,
                longitude=79.0882,
                location_precision="locality",
                location_source="google_geocoding",
            )
        elif "kochi" in norm or "kakkanad" in norm:
            return ResolvedLocation(
                google_place_id="ChIJ_kochi_kakkanad",
                formatted_address="Kakkanad, Kochi, Kerala, India",
                city="Kochi",
                area="Kakkanad",
                state="Kerala",
                country="India",
                postal_code="682030",
                latitude=9.9312,
                longitude=76.2673,
                location_precision="locality",
                location_source="google_geocoding",
            )
        elif "pune" in norm or "kothrud" in norm or "hinjewadi" in norm:
            return ResolvedLocation(
                google_place_id="ChIJ_pune_kothrud",
                formatted_address="Kothrud, Pune, Maharashtra, India",
                city="Pune",
                area="Kothrud",
                state="Maharashtra",
                country="India",
                postal_code="411038",
                latitude=18.5204,
                longitude=73.8567,
                location_precision="locality",
                location_source="google_geocoding",
            )
        return None

    def mock_reverse_geocode(lat: float, lon: float):
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            return None
        return ResolvedLocation(
            google_place_id="ChIJ_rev_geo_blr",
            formatted_address="Indiranagar, Bengaluru, Karnataka, India",
            city="Bengaluru",
            area="Indiranagar",
            state="Karnataka",
            country="India",
            postal_code="560038",
            latitude=round(lat, 6),
            longitude=round(lon, 6),
            location_precision="rooftop",
            location_source="google_reverse_geocoding",
        )

    def mock_routes(origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float, travel_mode: str = "DRIVE"):
        return TravelRouteInfo(
            straight_line_distance_km=5.2,
            route_distance_km=6.8,
            estimated_travel_time_minutes=18.0,
            travel_mode=travel_mode,
        )

    monkeypatch.setattr(google_maps_service, "autocomplete_places", mock_autocomplete)
    monkeypatch.setattr(google_maps_service, "geocode_address", mock_geocode)
    monkeypatch.setattr(google_maps_service, "reverse_geocode", mock_reverse_geocode)
    monkeypatch.setattr(google_maps_service, "compute_route_travel", mock_routes)


def test_location_autocomplete_unauthenticated_accessible(client: TestClient):
    """GET and POST /api/location/autocomplete should be accessible without authentication."""
    # GET
    resp = client.get("/api/location/autocomplete?input_text=Bengaluru")
    assert resp.status_code == 200
    data = resp.json()
    assert "predictions" in data
    assert len(data["predictions"]) > 0

    # POST
    resp_post = client.post("/api/location/autocomplete", json={"input_text": "Bengaluru"})
    assert resp_post.status_code == 200
    assert len(resp_post.json()["predictions"]) > 0


def test_location_autocomplete_short_input_rejected(client: TestClient):
    """Input less than 1 char should be rejected with 422."""
    resp = client.get("/api/location/autocomplete?input_text=")
    assert resp.status_code == 422

    resp_post = client.post("/api/location/autocomplete", json={"input_text": ""})
    assert resp_post.status_code == 422


def test_reverse_geocode_bounds_validation(client: TestClient):
    """Coordinates outside valid [-90, 90] and [-180, 180] must be rejected with 422."""
    resp = client.post(
        "/api/location/reverse-geocode",
        json={"latitude": 105.0, "longitude": 77.0},
    )
    assert resp.status_code == 422

    resp2 = client.post(
        "/api/location/reverse-geocode",
        json={"latitude": 12.97, "longitude": 200.0},
    )
    assert resp2.status_code == 422


def test_resolve_text_locality(client: TestClient):
    """POST /api/location/resolve resolves common Indian localities."""
    resp = client.post(
        "/api/location/resolve",
        json={"text": "Whitefield, Bengaluru"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["city"] == "Bengaluru"
    assert "Whitefield" in (data["area"] or data["formatted_address"] or "")
    assert data["latitude"] is not None
    assert data["longitude"] is not None


def test_request_target_location_isolation(client: TestClient):
    """
    Verify strict isolation between:
    1. Requester's home/profile location (Nagpur)
    2. Request target destination location (Whitefield, Bengaluru)
    """
    user = create_authenticated_user(client, "Relocating User", "relocator@example.test")

    # Set user profile location to Nagpur
    loc_resp = client.put(
        "/api/profile/me/location",
        headers=user["headers"],
        json={
            "city": "Nagpur",
            "area": "Dharampeth",
            "state": "Maharashtra",
            "country": "India",
            "latitude": 21.1458,
            "longitude": 79.0882,
            "location_source": "manual",
        },
    )
    assert loc_resp.status_code == 200
    assert loc_resp.json()["city"] == "Nagpur"

    # User posts request for relocation to Whitefield Bengaluru
    req_resp = client.post(
        "/api/requests",
        headers=user["headers"],
        json={"text": "Moving to Whitefield Bengaluru next week, need vegetarian PG and flatmates"},
    )
    assert req_resp.status_code == 201
    req_id = req_resp.json()["id"]

    # Requester's profile location MUST still be Nagpur
    me_loc = client.get("/api/profile/me/location", headers=user["headers"])
    assert me_loc.status_code == 200
    assert me_loc.json()["city"] == "Nagpur"
    assert abs(me_loc.json()["latitude"] - 21.1458) < 0.01

    # Request target location MUST be Bengaluru / Whitefield
    target_resp = client.get(f"/api/location/request/{req_id}", headers=user["headers"])
    assert target_resp.status_code == 200
    target_data = target_resp.json()
    assert target_data["city"] == "Bengaluru"
    assert abs(target_data["latitude"] - 12.9698) < 0.05
    assert abs(target_data["longitude"] - 77.7500) < 0.05


def test_matching_uses_request_target_not_profile_location(client: TestClient):
    """
    If a user lives in Nagpur but requests help for Whitefield, Bengaluru:
    Matching must score candidates against Bengaluru coordinates, NOT Nagpur!
    A Bengaluru helper candidate should score significantly closer than a Nagpur candidate.
    """
    # 1. Relocating newcomer (lives in Nagpur, needs help in Bengaluru)
    newcomer = create_authenticated_user(client, "Newcomer in Nagpur", "newcomer_ngp@example.test")
    client.put(
        "/api/profile/me/location",
        headers=newcomer["headers"],
        json={
            "city": "Nagpur",
            "latitude": 21.1458,
            "longitude": 79.0882,
        },
    )

    # 2. Candidate Helper in Bengaluru (Whitefield)
    blr_helper = create_authenticated_user(client, "BLR Helper", "blr_helper@example.test")
    client.put(
        "/api/profile/me",
        headers=blr_helper["headers"],
        json={"headline": "Tech lead & local guide in Whitefield", "years_experience": 4.0},
    )
    client.put(
        "/api/profile/me/location",
        headers=blr_helper["headers"],
        json={
            "city": "Bengaluru",
            "area": "Whitefield",
            "latitude": 12.9716,
            "longitude": 77.7520,
        },
    )

    # 3. Candidate Helper in Nagpur
    ngp_helper = create_authenticated_user(client, "NGP Helper", "ngp_helper@example.test")
    client.put(
        "/api/profile/me",
        headers=ngp_helper["headers"],
        json={"headline": "Local guide in Nagpur", "years_experience": 4.0},
    )
    client.put(
        "/api/profile/me/location",
        headers=ngp_helper["headers"],
        json={
            "city": "Nagpur",
            "area": "Dharampeth",
            "latitude": 21.1460,
            "longitude": 79.0880,
        },
    )

    # Newcomer posts request targeting Whitefield Bengaluru
    req_resp = client.post(
        "/api/requests",
        headers=newcomer["headers"],
        json={"text": "I am moving to Whitefield Bengaluru and need flatmate guidance"},
    )
    assert req_resp.status_code == 201
    req_id = req_resp.json()["id"]

    # Query matching endpoint
    match_resp = client.post(
        "/api/matching/find-matches",
        headers=newcomer["headers"],
        json={"request_id": req_id},
    )
    assert match_resp.status_code == 200
    match_data = match_resp.json()

    # Target location in response is Bengaluru
    assert match_data["target_location"]["city"] == "Bengaluru"

    # Find BLR helper vs NGP helper in matches
    matches = match_data["matches"]
    blr_cand = next((m for m in matches if m["user_id"] == blr_helper["user"]["id"]), None)
    ngp_cand = next((m for m in matches if m["user_id"] == ngp_helper["user"]["id"]), None)

    assert blr_cand is not None, "Bengaluru helper must be evaluated"
    assert ngp_cand is not None, "Nagpur helper must be evaluated"

    # BLR helper must have a very small distance (< 15 km) to Whitefield target
    assert blr_cand["distance_km"] is not None
    assert blr_cand["distance_km"] < 15.0

    # NGP helper must have a large distance (> 500 km) to Whitefield target
    assert ngp_cand["distance_km"] is not None
    assert ngp_cand["distance_km"] > 500.0

    # BLR helper location score must be significantly higher than NGP helper
    assert blr_cand["scores"]["location_score"] > ngp_cand["scores"]["location_score"]


def test_candidate_privacy_no_exact_coordinates_exposed(client: TestClient):
    """
    Ensure matching API NEVER leaks raw GPS coordinates or exact residential address.
    Coordinates returned must be approximate (at most 2 decimal places, ~1.1 km area precision).
    """
    requester = create_authenticated_user(client, "Privacy Requester", "privacy_req@example.test")
    helper = create_authenticated_user(client, "Privacy Helper", "privacy_helper@example.test")

    # Set precise GPS for helper
    client.put(
        "/api/profile/me",
        headers=helper["headers"],
        json={"headline": "Local developer"},
    )
    client.put(
        "/api/profile/me/location",
        headers=helper["headers"],
        json={
            "city": "Bengaluru",
            "area": "Koramangala",
            "formatted_address": "Flat 402, Sunshine Apts, 5th Block, Koramangala, Bengaluru",
            "latitude": 12.9351748291,
            "longitude": 77.6244910283,
        },
    )

    req_resp = client.post(
        "/api/requests",
        headers=requester["headers"],
        json={"text": "Need help in Koramangala Bengaluru"},
    )
    req_id = req_resp.json()["id"]

    match_resp = client.post(
        "/api/matching/find-matches",
        headers=requester["headers"],
        json={"request_id": req_id},
    )
    assert match_resp.status_code == 200
    matches = match_resp.json()["matches"]
    target_cand = next((m for m in matches if m["user_id"] == helper["user"]["id"]), None)
    assert target_cand is not None

    # Privacy check:
    # 1. Exact address string must NOT be in the candidate response
    cand_str = str(target_cand)
    assert "Flat 402" not in cand_str
    assert "Sunshine Apts" not in cand_str

    # 2. Approximate coordinates must be rounded to 2 decimal places
    approx_lat = target_cand["approximate_latitude"]
    approx_lon = target_cand["approximate_longitude"]
    assert approx_lat is not None
    assert approx_lon is not None
    # 12.9351748291 rounded to 2 decimal places is 12.94
    assert approx_lat == 12.94
    # 77.6244910283 rounded to 2 decimal places is 77.62
    assert approx_lon == 77.62


def test_prearrival_relocation_pune_to_kochi(client: TestClient):
    """
    LOCATION-FIRST DUAL-LOCATION & PRE-ARRIVAL RELOCATION TEST:
    1. Newcomer physically located in Pune (UserLocation = Pune).
    2. Newcomer creates a request targeting Kochi ('I'm moving to Kochi and need a PG before I arrive').
    3. Verify Newcomer's UserLocation in profile remains Pune (never overwritten by request target).
    4. Verify Request target location is resolved to Kochi.
    5. Helper enrolled in Kochi discovers the request in /api/requests/nearby within 50 km.
    6. Helper enrolled in Pune does NOT discover the request within 50 km (Pune-Kochi is ~1100 km away).
    """
    # 1. Newcomer in Pune
    newcomer = create_authenticated_user(client, "Rohan Relocating", "rohan.reloc@example.test", role="newcomer")
    pune_loc_resp = client.put(
        "/api/profile/me/location",
        headers=newcomer["headers"],
        json={
            "city": "Pune",
            "area": "Kothrud",
            "state": "Maharashtra",
            "country": "India",
            "latitude": 18.5204,
            "longitude": 73.8567,
            "location_label": "Primary",
        },
    )
    assert pune_loc_resp.status_code == 200

    # 2. Helper Anita in Kochi
    kochi_helper = create_authenticated_user(client, "Anita Kochi", "anita.kochi@example.test", role="helper")
    client.put(
        "/api/profile/me/location",
        headers=kochi_helper["headers"],
        json={
            "city": "Kochi",
            "area": "Kakkanad",
            "state": "Kerala",
            "country": "India",
            "latitude": 9.9312,
            "longitude": 76.2673,
            "location_label": "Primary",
        },
    )

    # 3. Helper Vikram in Pune
    pune_helper = create_authenticated_user(client, "Vikram Pune", "vikram.pune@example.test", role="helper")
    client.put(
        "/api/profile/me/location",
        headers=pune_helper["headers"],
        json={
            "city": "Pune",
            "area": "Kothrud",
            "state": "Maharashtra",
            "country": "India",
            "latitude": 18.5204,
            "longitude": 73.8567,
            "location_label": "Primary",
        },
    )

    # 4. Newcomer creates Kochi relocation request
    req_resp = client.post(
        "/api/requests",
        headers=newcomer["headers"],
        json={
            "text": "I'm moving to Kochi and need a PG in Kakkanad before I arrive.",
            "target_city": "Kochi",
            "target_area": "Kakkanad",
            "target_latitude": 9.9312,
            "target_longitude": 76.2673,
            "target_formatted_address": "Kakkanad, Kochi, Kerala, India",
        },
    )
    assert req_resp.status_code == 201
    created_req = req_resp.json()
    req_id = created_req["id"]
    assert created_req["city"] == "Kochi"

    # 5. Verify Newcomer's primary location is STILL Pune (NOT overwritten!)
    user_loc_resp = client.get("/api/profile/me/location", headers=newcomer["headers"])
    assert user_loc_resp.status_code == 200
    user_loc_data = user_loc_resp.json()
    assert user_loc_data["city"] == "Pune"
    assert user_loc_data["area"] == "Kothrud"
    assert user_loc_data["state"] == "Maharashtra"
    assert round(user_loc_data["latitude"], 2) == 18.52
    assert round(user_loc_data["longitude"], 2) == 73.86

    # 6. Helper in Kochi queries nearby requests (within 50 km) -> MUST find Rohan's request!
    kochi_feed_resp = client.get("/api/requests/nearby?radius_km=50", headers=kochi_helper["headers"])
    assert kochi_feed_resp.status_code == 200
    kochi_feed = kochi_feed_resp.json()
    found_in_kochi = [r for r in kochi_feed if r["id"] == req_id]
    assert len(found_in_kochi) == 1
    assert found_in_kochi[0]["city"] == "Kochi"
    assert found_in_kochi[0]["distance_km"] is not None
    assert found_in_kochi[0]["distance_km"] <= 5.0

    # 7. Helper in Pune queries nearby requests (within 50 km) -> MUST NOT find Rohan's Kochi request!
    pune_feed_resp = client.get("/api/requests/nearby?radius_km=50", headers=pune_helper["headers"])
    assert pune_feed_resp.status_code == 200
    pune_feed = pune_feed_resp.json()
    found_in_pune = [r for r in pune_feed if r["id"] == req_id]
    assert len(found_in_pune) == 0
