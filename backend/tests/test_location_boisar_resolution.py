import uuid
import pytest
from fastapi.testclient import TestClient
from tests.conftest import create_authenticated_user
from app.services.request_parser import parse_request


def test_boisar_nlp_extraction():
    """Verify that shifting to boisar,mumbai extracts Boisar as authoritative target destination."""
    text = "hey im shifting to boisar,mumbai i want flat to live and also good healthy mess"
    res = parse_request(text)
    assert res.location.city == "Boisar"
    assert res.location.state == "Maharashtra"
    assert res.location.latitude is not None and abs(res.location.latitude - 19.808) < 0.1
    assert res.location.longitude is not None and abs(res.location.longitude - 72.771) < 0.1
    assert res.location.google_place_id == "ChIJI1ifSTke5zsRys2rC5ulSmk"
    assert any("flat" in n.item or "room" in n.item for n in res.needs)
    assert any("mess" in n.item for n in res.needs)


def test_cross_city_origin_destination_separation():
    """Verify that moving from Bangalore to Pune identifies Pune as target, Bangalore as origin."""
    text = "moving from Bangalore to Pune for my job"
    res = parse_request(text)
    assert res.location.city == "Pune"
    assert res.location.origin_city == "Bengaluru"


def test_boisar_request_creation_and_helper_matching(client: TestClient):
    """
    End-to-end verification of Boisar newcomer request creation,
    persistence of Boisar coordinates, and precise nearby matching:
    - Boisar helper (<20km) receives the request.
    - Mumbai downtown helper (~95km away) does NOT receive the request.
    """
    # 1. Create newcomer user
    newcomer = create_authenticated_user(client, "Newcomer Rahul", f"rahul_{uuid.uuid4().hex[:6]}@example.test")

    # 2. Create helper in Boisar
    boisar_helper = create_authenticated_user(client, "Boisar Local Guide", f"boisar_helper_{uuid.uuid4().hex[:6]}@example.test")
    client.post("/api/profile", headers=boisar_helper["headers"], json={
        "headline": "Local Boisar resident & housing guide",
        "bio": "Living in Boisar for 10 years, can help newcomers with flats and mess food.",
        "years_experience": 5,
    })
    client.post("/api/profile/skills", headers=boisar_helper["headers"], json={
        "skills": ["Relocation & Housing", "Food & Cooking"],
    })
    client.put("/api/profile/me/location", headers=boisar_helper["headers"], json={
        "city": "Boisar",
        "area": "Boisar",
        "latitude": 19.808156,
        "longitude": 72.771777,
        "location_source": "gps",
    })

    # 3. Create helper in Mumbai (downtown, ~95km away from Boisar)
    mumbai_helper = create_authenticated_user(client, "Mumbai Guide", f"mumbai_helper_{uuid.uuid4().hex[:6]}@example.test")
    client.post("/api/profile", headers=mumbai_helper["headers"], json={
        "headline": "Mumbai central housing guide",
        "bio": "South Mumbai guide.",
        "years_experience": 5,
    })
    client.put("/api/profile/me/location", headers=mumbai_helper["headers"], json={
        "city": "Mumbai",
        "latitude": 18.9387,
        "longitude": 72.8353,
        "location_source": "gps",
    })

    # 4. Newcomer submits the request
    req_res = client.post("/api/requests", headers=newcomer["headers"], json={
        "text": "hey im shifting to boisar,mumbai i want flat to live and also good healthy mess",
    })
    assert req_res.status_code == 201
    req_data = req_res.json()
    assert req_data["city"] == "Boisar"
    assert req_data["target_location"] is not None
    assert req_data["target_location"]["city"] == "Boisar"
    assert abs(req_data["target_location"]["latitude"] - 19.808) < 0.1
    assert abs(req_data["target_location"]["longitude"] - 72.771) < 0.1

    # 5. Boisar helper fetches nearby requests
    boisar_feed = client.get("/api/requests/nearby?radius_km=20", headers=boisar_helper["headers"])
    assert boisar_feed.status_code == 200
    boisar_items = boisar_feed.json()
    assert any(item["id"] == req_data["id"] for item in boisar_items), "Boisar helper must see the Boisar request within 20km!"

    # 6. Mumbai helper fetches nearby requests
    mumbai_feed = client.get("/api/requests/nearby?radius_km=20", headers=mumbai_helper["headers"])
    assert mumbai_feed.status_code == 200
    mumbai_items = mumbai_feed.json()
    assert not any(item["id"] == req_data["id"] for item in mumbai_items), "Mumbai helper must NOT see the Boisar request (~95km away)!"
