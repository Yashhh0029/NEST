import pytest
from app.db.database import SessionLocal
from app.models.user import User, UserRole
from app.models.profile import Profile
from app.models.location import Location
from app.models.request import Request
from app.models.safety import Block
from app.models.notification import Notification, NotificationType
from tests.conftest import create_authenticated_user


def test_role_switching_matrix(client):
    """
    Test complete role transition matrix:
    - Newcomer -> Helper
    - Helper -> Both
    - Both -> Helper
    - Helper -> Newcomer
    - Newcomer -> Both
    - Both -> Newcomer
    - Verify persistence in DB and /api/profile/me & /api/auth/me.
    """
    auth = create_authenticated_user(client, "Role Test User", "role_test_matrix@example.test", role="newcomer")
    headers = auth["headers"]

    # Initial check: newcomer
    me_resp = client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["role"] == "newcomer"

    # 1. Newcomer -> Helper via PUT /api/profile/me/role
    resp = client.put("/api/profile/me/role", json={"role": "helper"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["role"] == "helper"

    # Verify profile endpoint reflects it
    prof_resp = client.get("/api/profile/me", headers=headers)
    assert prof_resp.json()["user"]["role"] == "helper"

    # 2. Helper -> Both via PUT /api/profile/me/role
    resp = client.put("/api/profile/me/role", json={"role": "both"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["role"] == "both"

    # 3. Both -> Helper via PUT /api/profile/me (general profile update mechanism)
    resp = client.put("/api/profile/me", json={"role": "helper", "headline": "Local Guide"}, headers=headers)
    assert resp.status_code == 200

    prof_resp = client.get("/api/profile/me", headers=headers)
    assert prof_resp.json()["user"]["role"] == "helper"

    # 4. Helper -> Newcomer via PUT /api/profile/me/role
    resp = client.put("/api/profile/me/role", json={"role": "newcomer"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["role"] == "newcomer"

    # 5. Newcomer -> Both via PATCH /api/profile/me
    resp = client.patch("/api/profile/me", json={"role": "both"}, headers=headers)
    assert resp.status_code == 200
    prof_resp = client.get("/api/profile/me", headers=headers)
    assert prof_resp.json()["user"]["role"] == "both"

    # 6. Both -> Newcomer via PUT /api/profile/me/role
    resp = client.put("/api/profile/me/role", json={"role": "newcomer"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["role"] == "newcomer"


def test_production_reproduction_mahalunge_scenario(client):
    """
    Exact production reproduction case:
    - Requester (Rocky-like): profile location UNSET.
    - Request: "I need pg", target location: Mahalunge (18.755195, 73.809071).
    - Account B (Yash-like): location in Mahalunge (18.755195, 73.809071).
    
    Step 1: Account B is Newcomer -> Rocky creates request -> Account B receives NO notification.
    Step 2: Account B switches to Helper -> Rocky creates a NEW request -> Account B receives notification!
    Step 3: Account B switches back to Newcomer -> Rocky creates request -> Account B receives NO notification.
    """
    target_lat = 18.755195
    target_lng = 73.809071

    # Requester A: Rocky (no profile location set)
    requester_a = create_authenticated_user(client, "Rocky Req", "rocky_test_repro@example.test", role="newcomer")

    # Account B: Helper candidate located in Mahalunge
    account_b = create_authenticated_user(client, "Yash B", "yash_test_repro@example.test", role="newcomer")

    # Set Account B's location to Mahalunge
    db = SessionLocal()
    try:
        user_b_id = account_b["user"]["id"]
        loc = Location(
            user_id=user_b_id,
            location_label="Primary",
            area="Near Hanuman mandir",
            city="Mahalunge",
            state="Maharashtra",
            country="India",
            latitude=target_lat,
            longitude=target_lng,
            formatted_address="Mahalunge, Maharashtra 410501, India"
        )
        db.add(loc)
        db.commit()
    finally:
        db.close()

    # --- PHASE 1: Account B is Newcomer ---
    req_payload_1 = {
        "text": "I need pg accommodation in Mahalunge",
        "target_latitude": target_lat,
        "target_longitude": target_lng,
        "target_city": "Mahalunge",
        "target_area": "Mahalunge",
        "target_display_name": "Mahalunge",
        "target_google_place_id": "ChIJ3x-Canm2wjsRwPJ-IJb_4C8",
        "target_formatted_address": "Mahalunge, Maharashtra 410501, India"
    }
    resp1 = client.post("/api/requests", json=req_payload_1, headers=requester_a["headers"])
    assert resp1.status_code == 201

    # Account B is Newcomer -> should have 0 notifications
    notifs_b1 = client.get("/api/notifications", headers=account_b["headers"])
    assert len(notifs_b1.json()["items"]) == 0

    # --- PHASE 2: Account B switches role to Helper ---
    role_change_resp = client.put("/api/profile/me/role", json={"role": "helper"}, headers=account_b["headers"])
    assert role_change_resp.status_code == 200
    assert role_change_resp.json()["role"] == "helper"

    # Rocky creates a NEW request in Mahalunge
    req_payload_2 = {
        "text": "Looking for PG flat in Mahalunge near temple",
        "target_latitude": target_lat,
        "target_longitude": target_lng,
        "target_city": "Mahalunge",
        "target_area": "Near Hanuman mandir",
        "target_display_name": "Mahalunge",
        "target_google_place_id": "ChIJ3x-Canm2wjsRwPJ-IJb_4C8",
        "target_formatted_address": "Mahalunge, Maharashtra 410501, India"
    }
    resp2 = client.post("/api/requests", json=req_payload_2, headers=requester_a["headers"])
    assert resp2.status_code == 201
    new_req_id = resp2.json()["id"]

    # Account B (now Helper) MUST receive the notification!
    notifs_b2 = client.get("/api/notifications", headers=account_b["headers"])
    items = notifs_b2.json()["items"]
    assert len(items) == 1
    assert items[0]["request_id"] == new_req_id
    assert items[0]["title"] == "Someone needs help nearby"
    assert items[0]["distance_km"] == pytest.approx(0.0, abs=0.1)
    assert items[0]["is_read"] is False

    # Unread count must be 1
    unread = client.get("/api/notifications/unread-count", headers=account_b["headers"])
    assert unread.json()["unread_count"] == 1

    # --- PHASE 3: Account B switches role to Both ---
    client.put("/api/profile/me/role", json={"role": "both"}, headers=account_b["headers"])

    # Rocky creates request 3
    resp3 = client.post("/api/requests", json={
        "text": "Need room near Mahalunge IT area",
        "target_latitude": target_lat,
        "target_longitude": target_lng,
        "target_city": "Mahalunge",
    }, headers=requester_a["headers"])
    assert resp3.status_code == 201

    # Account B (role Both) receives the notification!
    notifs_b3 = client.get("/api/notifications", headers=account_b["headers"])
    assert len(notifs_b3.json()["items"]) == 2

    # --- PHASE 4: Account B switches role back to Newcomer ---
    client.put("/api/profile/me/role", json={"role": "newcomer"}, headers=account_b["headers"])

    # Rocky creates request 4
    resp4 = client.post("/api/requests", json={
        "text": "Need urgent tiffin in Mahalunge",
        "target_latitude": target_lat,
        "target_longitude": target_lng,
        "target_city": "Mahalunge",
    }, headers=requester_a["headers"])
    assert resp4.status_code == 201

    # Account B (now Newcomer again) does NOT receive notification for request 4
    notifs_b4 = client.get("/api/notifications", headers=account_b["headers"])
    assert len(notifs_b4.json()["items"]) == 2  # still only the 2 previous ones
