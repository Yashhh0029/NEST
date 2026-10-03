import pytest
from app.db.database import SessionLocal
from app.models.user import User, UserRole
from app.models.profile import Profile
from app.models.location import Location
from app.models.request import Request
from app.models.safety import Block
from app.models.notification import Notification, NotificationType
from app.services.notification_service import notify_nearby_helpers_for_request, haversine_km
from tests.conftest import create_authenticated_user


def create_user_with_location(client, name: str, email: str, role: str, lat: float, lng: float, area: str = "Kothrud", city: str = "Pune"):
    """Helper to create an authenticated user with a saved primary profile location."""
    user_data = create_authenticated_user(client, name, email, role=role)
    db = SessionLocal()
    try:
        user_id = user_data["user"]["id"]
        # Update user role enum if needed
        db_user = db.query(User).filter(User.id == user_id).first()
        db_user.role = UserRole(role)
        
        # Ensure profile exists
        profile = db.query(Profile).filter(Profile.user_id == user_id).first()
        if not profile:
            profile = Profile(user_id=user_id, bio=f"Bio for {name}")
            db.add(profile)
            db.flush()

        # Add or update primary location
        loc = db.query(Location).filter(
            Location.user_id == user_id,
            Location.location_label == "Primary"
        ).first()
        if not loc:
            loc = Location(
                user_id=user_id,
                location_label="Primary",
                area=area,
                city=city,
                state="Maharashtra",
                latitude=lat,
                longitude=lng
            )
            db.add(loc)
        else:
            loc.latitude = lat
            loc.longitude = lng
            loc.area = area
            loc.city = city
        db.commit()
    finally:
        db.close()
    return user_data


def test_haversine_formula():
    """Verify haversine_km accurate distance calculation."""
    # Arihant Society to Deccan Gymkhana (~4.2 km)
    dist = haversine_km(18.5074, 73.8077, 18.5167, 73.8415)
    assert 3.5 < dist < 5.0
    
    # 0 distance
    assert haversine_km(18.5074, 73.8077, 18.5074, 73.8077) == 0.0


def test_automatic_nearby_notification_on_request_creation(client):
    """
    Test that creating a request dispatches automatic notifications to nearby helpers
    within 5km of TARGET_LOCATION, while preserving manual request flow.
    """
    target_lat = 18.5074
    target_lng = 73.8077

    # 1. Requester is in Mumbai (18.9220, 72.8347) but targeting Pune Kothrud
    requester = create_user_with_location(
        client, "Newcomer Req", "newcomer_target@example.com", "newcomer", 18.9220, 72.8347
    )

    # 2. Helper A: 1.2 km away from target in Kothrud
    helper_a = create_user_with_location(
        client, "Helper A", "helper_a_notify@example.com", "helper", 18.5180, 73.8077
    )

    # 3. Helper B: 3.8 km away from target
    helper_b = create_user_with_location(
        client, "Helper B", "helper_b_notify@example.com", "helper", 18.5410, 73.8077
    )

    # 4. Helper C: 4.8 km away from target (within 5 km)
    helper_c = create_user_with_location(
        client, "Helper C", "helper_c_notify@example.com", "both", 18.5500, 73.8077
    )

    # 5. Helper Far: 6.0 km away from target (outside 5 km)
    helper_far = create_user_with_location(
        client, "Helper Far", "helper_far_notify@example.com", "helper", 18.5620, 73.8077
    )

    # Requester creates a request with explicit target location
    create_payload = {
        "text": "Need PG accommodation near Arihant Society Kothrud Pune",
        "target_latitude": target_lat,
        "target_longitude": target_lng,
        "target_city": "Pune",
        "target_area": "Kothrud",
        "target_display_name": "Arihant Society",
        "target_google_place_id": "ChIJ_test_arihant_place",
        "target_formatted_address": "Arihant Society, Kothrud, Pune, Maharashtra 411038"
    }

    resp = client.post("/api/requests", json=create_payload, headers=requester["headers"])
    assert resp.status_code == 201, resp.text
    req_data = resp.json()
    req_id = req_data["id"]

    # Check notification for Helper A (1.2 km): should exist
    resp_a = client.get("/api/notifications", headers=helper_a["headers"])
    assert resp_a.status_code == 200
    items_a = resp_a.json()["items"]
    assert len(items_a) == 1
    assert items_a[0]["request_id"] == req_id
    assert items_a[0]["title"] == "Someone needs help nearby"
    assert "accommodation" in items_a[0]["message"]
    assert items_a[0]["is_read"] is False
    assert items_a[0]["distance_km"] is not None
    assert items_a[0]["distance_km"] < 2.0

    # Check notification for Helper B (3.8 km): should exist
    resp_b = client.get("/api/notifications", headers=helper_b["headers"])
    assert resp_b.status_code == 200
    items_b = resp_b.json()["items"]
    assert len(items_b) == 1
    assert items_b[0]["request_id"] == req_id
    assert items_b[0]["distance_km"] < 4.0

    # Check notification for Helper C (4.8 km): should exist
    resp_c = client.get("/api/notifications", headers=helper_c["headers"])
    assert resp_c.status_code == 200
    items_c = resp_c.json()["items"]
    assert len(items_c) == 1
    assert items_c[0]["request_id"] == req_id

    # Check notification for Helper Far (> 5 km): should NOT exist
    resp_far = client.get("/api/notifications", headers=helper_far["headers"])
    assert resp_far.status_code == 200
    assert len(resp_far.json()["items"]) == 0

    # Check unread count for Helper A
    unread_resp = client.get("/api/notifications/unread-count", headers=helper_a["headers"])
    assert unread_resp.status_code == 200
    assert unread_resp.json()["unread_count"] == 1


def test_safety_blocking_and_self_exclusion(client):
    """
    Test that:
    1. Requester never gets notified for their own request even if role is 'both' and at 0 km.
    2. Helpers who are blocked by requester (or have blocked requester) never get notified.
    """
    target_lat = 18.5074
    target_lng = 73.8077

    # Requester with role 'both' at same coords
    requester = create_user_with_location(
        client, "Self Both Req", "both_requester@example.com", "both", target_lat, target_lng
    )

    # Blocked Helper 1: Requester blocks Helper 1
    blocked_by_req = create_user_with_location(
        client, "Blocked By Req", "blocked_by_req@example.com", "helper", target_lat + 0.005, target_lng
    )

    # Blocked Helper 2: Helper 2 blocks Requester
    blocks_requester = create_user_with_location(
        client, "Blocks Req", "blocks_req@example.com", "helper", target_lat + 0.006, target_lng
    )

    # Normal Helper
    normal_helper = create_user_with_location(
        client, "Normal Helper", "normal_nearby@example.com", "helper", target_lat + 0.007, target_lng
    )

    # Insert blocks in DB
    db = SessionLocal()
    try:
        # Requester blocks blocked_by_req
        b1 = Block(
            blocker_id=requester["user"]["id"],
            blocked_id=blocked_by_req["user"]["id"]
        )
        # blocks_requester blocks requester
        b2 = Block(
            blocker_id=blocks_requester["user"]["id"],
            blocked_id=requester["user"]["id"]
        )
        db.add_all([b1, b2])
        db.commit()
    finally:
        db.close()

    create_payload = {
        "text": "Need help with safety testing in Arihant Society Kothrud",
        "target_latitude": target_lat,
        "target_longitude": target_lng,
        "target_city": "Pune",
        "target_area": "Kothrud",
        "target_display_name": "Arihant Society",
        "target_google_place_id": "ChIJ_safety_test",
        "target_formatted_address": "Kothrud, Pune"
    }

    resp = client.post("/api/requests", json=create_payload, headers=requester["headers"])
    assert resp.status_code == 201
    req_id = resp.json()["id"]

    # 1. Requester should NOT have notifications for own request
    resp_req = client.get("/api/notifications", headers=requester["headers"])
    assert resp_req.status_code == 200
    assert len(resp_req.json()["items"]) == 0

    # 2. Blocked helper 1 should NOT have notifications
    resp_b1 = client.get("/api/notifications", headers=blocked_by_req["headers"])
    assert resp_b1.status_code == 200
    assert len(resp_b1.json()["items"]) == 0

    # 3. Blocked helper 2 should NOT have notifications
    resp_b2 = client.get("/api/notifications", headers=blocks_requester["headers"])
    assert resp_b2.status_code == 200
    assert len(resp_b2.json()["items"]) == 0

    # 4. Normal helper SHOULD have notification
    resp_norm = client.get("/api/notifications", headers=normal_helper["headers"])
    assert resp_norm.status_code == 200
    items = resp_norm.json()["items"]
    assert len(items) == 1
    assert items[0]["request_id"] == req_id


def test_duplicate_notification_prevention(client):
    """
    Test that re-running notify_nearby_helpers_for_request does not create duplicate notifications.
    """
    target_lat = 18.5074
    target_lng = 73.8077

    requester = create_user_with_location(
        client, "Dup Requester", "dup_requester@example.com", "newcomer", 18.5074, 73.8077
    )
    helper = create_user_with_location(
        client, "Dup Helper", "dup_helper@example.com", "helper", 18.5100, 73.8077
    )

    create_payload = {
        "text": "Need bus transport guidance near Kothrud Depot Pune",
        "target_latitude": target_lat,
        "target_longitude": target_lng,
        "target_city": "Pune",
        "target_area": "Kothrud",
        "target_display_name": "Kothrud Depot",
        "target_google_place_id": "ChIJ_dup_test",
        "target_formatted_address": "Kothrud, Pune"
    }
    resp = client.post("/api/requests", json=create_payload, headers=requester["headers"])
    assert resp.status_code == 201
    req_id = resp.json()["id"]

    # Check notification count is 1
    resp_helper = client.get("/api/notifications", headers=helper["headers"])
    assert len(resp_helper.json()["items"]) == 1

    # Manually call notify_nearby_helpers_for_request again for the same request
    db = SessionLocal()
    try:
        req_obj = db.query(Request).filter(Request.id == req_id).first()
        notify_nearby_helpers_for_request(db, req_obj)
    finally:
        db.close()

    # Verify count is still exactly 1
    resp_helper_after = client.get("/api/notifications", headers=helper["headers"])
    assert len(resp_helper_after.json()["items"]) == 1


def test_privacy_masking_on_request_access(client):
    """
    Test that when a notified helper views the request:
    - Exact latitude, longitude, and formatted_address are masked (None/coarse only).
    - Coarse area, city, and coarse display name remain visible.
    - The original owner CAN still see their exact coordinates.
    """
    target_lat = 18.507402
    target_lng = 73.807715

    requester = create_user_with_location(
        client, "Privacy Requester", "privacy_requester@example.com", "newcomer", target_lat, target_lng
    )
    helper = create_user_with_location(
        client, "Privacy Helper", "privacy_helper@example.com", "helper", 18.5100, 73.8077
    )

    create_payload = {
        "text": "Need private accommodation guidance near Secret Heights Kothrud Pune",
        "target_latitude": target_lat,
        "target_longitude": target_lng,
        "target_city": "Pune",
        "target_area": "Kothrud",
        "target_display_name": "Flat 402, Secret Heights",
        "target_google_place_id": "ChIJ_privacy_test",
        "target_formatted_address": "Flat 402, Secret Heights, Kothrud, Pune 411038"
    }
    resp = client.post("/api/requests", json=create_payload, headers=requester["headers"])
    assert resp.status_code == 201
    req_id = resp.json()["id"]

    # 1. Owner views request: exact latitude & longitude are present
    owner_view = client.get(f"/api/requests/{req_id}", headers=requester["headers"])
    assert owner_view.status_code == 200
    owner_loc = owner_view.json()["target_location"]
    assert owner_loc["latitude"] == pytest.approx(target_lat, rel=1e-5)
    assert owner_loc["longitude"] == pytest.approx(target_lng, rel=1e-5)
    assert owner_loc["display_name"] == "Flat 402, Secret Heights"

    # 2. Notified Helper views request: exact latitude & longitude must be masked (None)
    helper_view = client.get(f"/api/requests/{req_id}", headers=helper["headers"])
    assert helper_view.status_code == 200
    helper_loc = helper_view.json()["target_location"]
    assert helper_loc["latitude"] is None
    assert helper_loc["longitude"] is None
    assert helper_loc["formatted_address"] is None
    assert helper_loc["city"] == "Pune"
    assert helper_loc["area"] == "Kothrud"


def test_notification_read_lifecycle(client):
    """
    Test mark single read, mark all read, and unread count tracking.
    """
    target_lat = 18.5074
    target_lng = 73.8077

    requester = create_user_with_location(
        client, "Read Requester", "read_requester@example.com", "newcomer", target_lat, target_lng
    )
    helper = create_user_with_location(
        client, "Read Helper", "read_helper@example.com", "helper", 18.5090, 73.8077
    )

    # Create 2 requests
    for i in range(2):
        client.post("/api/requests", json={
            "text": f"Need assistance number {i+1} in Kothrud Pune",
            "target_latitude": target_lat,
            "target_longitude": target_lng,
            "target_city": "Pune",
            "target_area": "Kothrud",
            "target_display_name": f"Area {i}",
            "target_google_place_id": f"ChIJ_read_{i}",
            "target_formatted_address": "Kothrud, Pune"
        }, headers=requester["headers"])

    # Helper should have 2 unread notifications
    count_resp = client.get("/api/notifications/unread-count", headers=helper["headers"])
    assert count_resp.status_code == 200
    assert count_resp.json()["unread_count"] == 2

    list_resp = client.get("/api/notifications", headers=helper["headers"])
    notifications = list_resp.json()["items"]
    assert len(notifications) == 2

    first_notif_id = notifications[0]["id"]

    # Mark first notification as read
    patch_resp = client.patch(f"/api/notifications/{first_notif_id}/read", headers=helper["headers"])
    assert patch_resp.status_code == 200
    assert patch_resp.json()["is_read"] is True

    # Unread count should now be 1
    count_resp2 = client.get("/api/notifications/unread-count", headers=helper["headers"])
    assert count_resp2.json()["unread_count"] == 1

    # Mark all as read
    all_read_resp = client.post("/api/notifications/mark-all-read", headers=helper["headers"])
    assert all_read_resp.status_code == 200
    assert all_read_resp.json()["marked_count"] == 1

    # Unread count should now be 0
    count_resp3 = client.get("/api/notifications/unread-count", headers=helper["headers"])
    assert count_resp3.json()["unread_count"] == 0
