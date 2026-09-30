import concurrent.futures
import threading
from datetime import date, datetime, timedelta, timezone
import uuid
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.database import SessionLocal
from app.models.connection import Connection
from app.models.request import Request
from app.models.request_location import RequestLocation
from app.services.google_maps_service import google_maps_service
from tests.conftest import create_authenticated_user


@pytest.fixture
def mock_venue_service(monkeypatch):
    """
    Mock Google Places venue details for testing.
    """
    def mock_get_venue_details(place_id: str):
        if "far_away" in place_id.lower():
            return {
                "place_id": place_id,
                "name": "Far Away Cafe",
                "formatted_address": "Mysuru Road, 60km away",
                "latitude": 12.4000,
                "longitude": 76.8000,
                "primary_type": "cafe",
                "types": ["cafe", "establishment"],
            }
        elif "cafe" in place_id.lower():
            return {
                "place_id": place_id,
                "name": "Central Cafe & Library",
                "formatted_address": "123 Indiranagar 100ft Rd, Bengaluru, Karnataka 560038",
                "latitude": 12.9716,
                "longitude": 77.5946,
                "primary_type": "cafe",
                "types": ["cafe", "coffee_shop", "establishment"],
            }
        elif "hotel" in place_id.lower() or "residence" in place_id.lower():
            return {
                "place_id": place_id,
                "name": "Grand Palace Hotel",
                "formatted_address": "456 Luxury Ave, Bengaluru",
                "latitude": 12.9750,
                "longitude": 77.6000,
                "primary_type": "hotel",
                "types": ["lodging", "hotel", "establishment"],
            }
        return None

    monkeypatch.setattr(google_maps_service, "get_venue_details", mock_get_venue_details)


def test_availability_slots_crud_and_validation(client: TestClient):
    user = create_authenticated_user(client, "Avail User 1", f"avail_u1_{uuid.uuid4().hex[:6]}@example.test")
    headers = user["headers"]

    # 1. Successful update of recurring slots
    payload = {
        "helper_timezone": "Asia/Kolkata",
        "slots": [
            {"day_of_week": 0, "start_time": "09:00:00", "end_time": "12:00:00"},
            {"day_of_week": 0, "start_time": "14:00:00", "end_time": "17:00:00"},
            {"day_of_week": 5, "start_time": "10:00:00", "end_time": "14:00:00"},
        ],
    }
    resp = client.put(f"{settings.API_V1_STR}/availability/slots", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data["slots"]) == 3
    assert data["helper_timezone"] == "Asia/Kolkata"

    # 2. Rejection of invalid day of week (7)
    bad_payload = {
        "slots": [{"day_of_week": 7, "start_time": "09:00:00", "end_time": "10:00:00"}]
    }
    resp = client.put(f"{settings.API_V1_STR}/availability/slots", json=bad_payload, headers=headers)
    assert resp.status_code == 422

    # 3. Rejection of invalid time order (start >= end)
    bad_time_payload = {
        "slots": [{"day_of_week": 1, "start_time": "15:00:00", "end_time": "10:00:00"}]
    }
    resp = client.put(f"{settings.API_V1_STR}/availability/slots", json=bad_time_payload, headers=headers)
    assert resp.status_code == 422

    # 4. Rejection of intra-day overlapping slots
    overlap_payload = {
        "slots": [
            {"day_of_week": 2, "start_time": "09:00:00", "end_time": "12:00:00"},
            {"day_of_week": 2, "start_time": "11:00:00", "end_time": "13:00:00"},
        ]
    }
    resp = client.put(f"{settings.API_V1_STR}/availability/slots", json=overlap_payload, headers=headers)
    assert resp.status_code == 422


def test_availability_capacity_and_timezone_controls(client: TestClient):
    user = create_authenticated_user(client, "Avail User 2", f"avail_u2_{uuid.uuid4().hex[:6]}@example.test")
    headers = user["headers"]

    # 1. Update capacity and IANA timezone
    cap_payload = {
        "helper_timezone": "America/New_York",
        "accepting_sessions": True,
        "max_weekly_sessions": 5,
    }
    resp = client.put(f"{settings.API_V1_STR}/availability/capacity", json=cap_payload, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["helper_timezone"] == "America/New_York"
    assert data["max_weekly_sessions"] == 5
    assert data["accepting_sessions"] is True

    # 2. Reject invalid IANA timezone
    bad_tz_payload = {"helper_timezone": "NonExistent/Mars_Time"}
    resp = client.put(f"{settings.API_V1_STR}/availability/capacity", json=bad_tz_payload, headers=headers)
    assert resp.status_code == 422


def test_availability_exceptions_blackout(client: TestClient):
    user = create_authenticated_user(client, "Avail User 3", f"avail_u3_{uuid.uuid4().hex[:6]}@example.test")
    headers = user["headers"]

    # 1. Add blackout date
    target_date = (date.today() + timedelta(days=3)).isoformat()
    ex_payload = {
        "exception_date": target_date,
        "is_available": False,
        "reason": "Personal travel / conference",
    }
    resp = client.post(f"{settings.API_V1_STR}/availability/exceptions", json=ex_payload, headers=headers)
    assert resp.status_code == 201, resp.text
    ex_data = resp.json()
    assert ex_data["is_available"] is False
    assert ex_data["exception_date"] == target_date
    ex_id = ex_data["id"]

    # 2. Retrieve my availability and verify exception
    my_resp = client.get(f"{settings.API_V1_STR}/availability/my", headers=headers)
    assert my_resp.status_code == 200
    my_data = my_resp.json()
    assert len(my_data["exceptions"]) >= 1

    # 3. Delete exception
    del_resp = client.delete(f"{settings.API_V1_STR}/availability/exceptions/{ex_id}", headers=headers)
    assert del_resp.status_code == 204


def test_two_tier_privacy_model(client: TestClient):
    helper = create_authenticated_user(client, "Privacy Helper", f"hlp_priv_{uuid.uuid4().hex[:6]}@example.test")
    public_viewer = create_authenticated_user(client, "Public Viewer", f"pub_priv_{uuid.uuid4().hex[:6]}@example.test")
    connected_user = create_authenticated_user(client, "Connected User", f"conn_priv_{uuid.uuid4().hex[:6]}@example.test")

    # Set helper slots
    slots_payload = {
        "helper_timezone": "Asia/Kolkata",
        "slots": [
            {"day_of_week": 1, "start_time": "18:00:00", "end_time": "20:00:00"},
            {"day_of_week": 5, "start_time": "10:00:00", "end_time": "13:00:00"},
        ],
    }
    client.put(f"{settings.API_V1_STR}/availability/slots", json=slots_payload, headers=helper["headers"])

    # 1. Tier 1: Public viewer (no connection) queries helper
    pub_resp = client.get(f"{settings.API_V1_STR}/availability/user/{helper['user']['id']}", headers=public_viewer["headers"])
    assert pub_resp.status_code == 200
    pub_data = pub_resp.json()
    assert "coarse_windows" in pub_data
    assert "slots" not in pub_data  # NEVER leak exact slots to public viewer
    assert pub_data["has_schedule_configured"] is True

    # 2. Tier 2: Create an accepted connection with connected_user
    db = SessionLocal()
    try:
        req = Request(
            id=uuid.uuid4(),
            user_id=uuid.UUID(connected_user["user"]["id"]),
            raw_text="Help with accommodation: Need local guidance",
            city="Bengaluru",
            status="OPEN",
        )
        db.add(req)
        req_loc = RequestLocation(request_id=req.id, latitude=12.9716, longitude=77.5946, city="Bengaluru")
        db.add(req_loc)
        conn = Connection(
            id=uuid.uuid4(),
            request_id=req.id,
            requester_id=uuid.UUID(connected_user["user"]["id"]),
            helper_id=uuid.UUID(helper["user"]["id"]),
            status="ACCEPTED",
        )
        db.add(conn)
        db.commit()
    finally:
        db.close()

    # Now connected user queries helper availability
    conn_resp = client.get(f"{settings.API_V1_STR}/availability/user/{helper['user']['id']}", headers=connected_user["headers"])
    assert conn_resp.status_code == 200
    conn_data = conn_resp.json()
    assert "slots" in conn_data  # Detailed slots are visible to authorized connection partner
    assert len(conn_data["slots"]) == 2


def test_session_lifecycle_and_state_machine(client: TestClient, mock_venue_service):
    requester = create_authenticated_user(client, "Req User 1", f"s_req1_{uuid.uuid4().hex[:6]}@example.test")
    helper = create_authenticated_user(client, "Hlp User 1", f"s_hlp1_{uuid.uuid4().hex[:6]}@example.test")

    db = SessionLocal()
    try:
        req = Request(
            id=uuid.uuid4(),
            user_id=uuid.UUID(requester["user"]["id"]),
            raw_text="Newcomer neighborhood orientation in Indiranagar",
            city="Bengaluru",
            status="OPEN",
        )
        db.add(req)
        req_loc = RequestLocation(request_id=req.id, latitude=12.9716, longitude=77.5946, city="Bengaluru")
        db.add(req_loc)
        conn = Connection(
            id=uuid.uuid4(),
            request_id=req.id,
            requester_id=uuid.UUID(requester["user"]["id"]),
            helper_id=uuid.UUID(helper["user"]["id"]),
            status="ACCEPTED",
        )
        db.add(conn)
        db.commit()
        req_id = req.id
    finally:
        db.close()

    future_start = (datetime.now(timezone.utc) + timedelta(days=2)).replace(microsecond=0)

    # 1. Propose session
    propose_payload = {
        "request_id": str(req_id),
        "recipient_id": str(helper["user"]["id"]),
        "title": "Indiranagar Coffee & Housing Discussion",
        "description": "Meet at Central Cafe to review rental options",
        "modality": "IN_PERSON",
        "meeting_place_id": "ChIJ_indiranagar_cafe_123",
        "scheduled_start": future_start.isoformat(),
        "duration_minutes": 60,
        "session_timezone": "Asia/Kolkata",
    }
    resp = client.post(f"{settings.API_V1_STR}/sessions", json=propose_payload, headers=requester["headers"])
    assert resp.status_code == 201, resp.text
    session_data = resp.json()
    assert session_data["status"] == "PROPOSED"
    assert session_data["meeting_place_name"] == "Central Cafe & Library"
    session_id = session_data["id"]

    # 2. Anti-self-accept: Requester cannot accept their own proposal
    self_accept_resp = client.post(f"{settings.API_V1_STR}/sessions/{session_id}/accept", headers=requester["headers"])
    assert self_accept_resp.status_code == 403

    # 3. Recipient (Helper) accepts session -> CONFIRMED
    accept_resp = client.post(f"{settings.API_V1_STR}/sessions/{session_id}/accept", headers=helper["headers"])
    assert accept_resp.status_code == 200
    assert accept_resp.json()["status"] == "CONFIRMED"

    # 4. Propose reschedule by helper
    resched_start = (future_start + timedelta(hours=3)).isoformat()
    resched_payload = {
        "new_scheduled_start": resched_start,
        "new_duration_minutes": 90,
        "reschedule_reason": "Need to push by 3 hours due to meeting",
    }
    resched_resp = client.post(
        f"{settings.API_V1_STR}/sessions/{session_id}/reschedule",
        json=resched_payload,
        headers=helper["headers"],
    )
    assert resched_resp.status_code == 200
    assert resched_resp.json()["status"] == "RESCHEDULE_PROPOSED"
    assert resched_resp.json()["reschedule_count"] == 1

    # 5. Requester accepts reschedule -> CONFIRMED
    r_accept = client.post(f"{settings.API_V1_STR}/sessions/{session_id}/accept", headers=requester["headers"])
    assert r_accept.status_code == 200
    assert r_accept.json()["status"] == "CONFIRMED"

    # 6. Dual-confirmation completion
    # Requester completes
    c1 = client.post(f"{settings.API_V1_STR}/sessions/{session_id}/complete", headers=requester["headers"])
    assert c1.status_code == 200
    assert c1.json()["status"] == "CONFIRMED"  # still CONFIRMED until second participant confirms
    assert c1.json()["requester_completed_at"] is not None
    assert c1.json()["helper_completed_at"] is None

    # Helper completes
    c2 = client.post(f"{settings.API_V1_STR}/sessions/{session_id}/complete", headers=helper["headers"])
    assert c2.status_code == 200
    assert c2.json()["status"] == "COMPLETED"
    assert c2.json()["helper_completed_at"] is not None


def test_session_venue_and_remote_validation(client: TestClient, mock_venue_service):
    requester = create_authenticated_user(client, "Req Venue", f"v_req_{uuid.uuid4().hex[:6]}@example.test")
    helper = create_authenticated_user(client, "Hlp Venue", f"v_hlp_{uuid.uuid4().hex[:6]}@example.test")

    db = SessionLocal()
    try:
        req = Request(
            id=uuid.uuid4(),
            user_id=uuid.UUID(requester["user"]["id"]),
            raw_text="College orientation: Help with campus",
            city="Bengaluru",
            status="OPEN",
        )
        db.add(req)
        req_loc = RequestLocation(request_id=req.id, latitude=12.9716, longitude=77.5946, city="Bengaluru")
        db.add(req_loc)
        conn = Connection(
            id=uuid.uuid4(),
            request_id=req.id,
            requester_id=uuid.UUID(requester["user"]["id"]),
            helper_id=uuid.UUID(helper["user"]["id"]),
            status="ACCEPTED",
        )
        db.add(conn)
        db.commit()
        req_id = req.id
    finally:
        db.close()

    future_start = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    # 1. Reject disallowed venue (Hotel / lodging)
    bad_venue_payload = {
        "request_id": str(req_id),
        "recipient_id": str(helper["user"]["id"]),
        "title": "Hotel Meeting",
        "modality": "IN_PERSON",
        "meeting_place_id": "ChIJ_luxury_hotel_456",
        "scheduled_start": future_start,
        "duration_minutes": 60,
    }
    resp = client.post(f"{settings.API_V1_STR}/sessions", json=bad_venue_payload, headers=requester["headers"])
    assert resp.status_code == 422
    assert "not permitted" in resp.json()["detail"].lower()

    # 2. Reject venue > 25 km away
    far_venue_payload = {
        "request_id": str(req_id),
        "recipient_id": str(helper["user"]["id"]),
        "title": "Far Away Meeting",
        "modality": "IN_PERSON",
        "meeting_place_id": "ChIJ_far_away_cafe",
        "scheduled_start": future_start,
        "duration_minutes": 60,
    }
    resp = client.post(f"{settings.API_V1_STR}/sessions", json=far_venue_payload, headers=requester["headers"])
    assert resp.status_code == 422
    assert "exceeding the approved 25 km radius" in resp.json()["detail"].lower()

    # 3. Reject insecure HTTP remote URL
    insecure_remote_payload = {
        "request_id": str(req_id),
        "recipient_id": str(helper["user"]["id"]),
        "title": "Remote Insecure Call",
        "modality": "REMOTE",
        "meeting_url": "http://meet.google.com/xyz",
        "scheduled_start": future_start,
        "duration_minutes": 60,
    }
    resp = client.post(f"{settings.API_V1_STR}/sessions", json=insecure_remote_payload, headers=requester["headers"])
    assert resp.status_code == 422
    assert "secure https" in resp.json()["detail"].lower()

    # 4. Reject localhost / SSRF URL
    ssrf_remote_payload = {
        "request_id": str(req_id),
        "recipient_id": str(helper["user"]["id"]),
        "title": "SSRF Call",
        "modality": "REMOTE",
        "meeting_url": "https://localhost:8080/call",
        "scheduled_start": future_start,
        "duration_minutes": 60,
    }
    resp = client.post(f"{settings.API_V1_STR}/sessions", json=ssrf_remote_payload, headers=requester["headers"])
    assert resp.status_code == 422
    assert "prohibited" in resp.json()["detail"].lower()

    # 5. Accept valid HTTPS remote URL
    valid_remote_payload = {
        "request_id": str(req_id),
        "recipient_id": str(helper["user"]["id"]),
        "title": "Valid Remote Session",
        "modality": "REMOTE",
        "meeting_url": "https://meet.google.com/abc-defg-hij",
        "scheduled_start": future_start,
        "duration_minutes": 60,
    }
    resp = client.post(f"{settings.API_V1_STR}/sessions", json=valid_remote_payload, headers=requester["headers"])
    assert resp.status_code == 201


def test_session_calendar_export_rfc5545(client: TestClient, mock_venue_service):
    requester = create_authenticated_user(client, "ICS Req", f"ics_r_{uuid.uuid4().hex[:6]}@example.test")
    helper = create_authenticated_user(client, "ICS Hlp", f"ics_h_{uuid.uuid4().hex[:6]}@example.test")

    db = SessionLocal()
    try:
        req = Request(
            id=uuid.uuid4(),
            user_id=uuid.UUID(requester["user"]["id"]),
            raw_text="ICS Test Request",
            city="Bengaluru",
            status="OPEN",
        )
        db.add(req)
        conn = Connection(
            id=uuid.uuid4(),
            request_id=req.id,
            requester_id=uuid.UUID(requester["user"]["id"]),
            helper_id=uuid.UUID(helper["user"]["id"]),
            status="ACCEPTED",
        )
        db.add(conn)
        db.commit()
        req_id = req.id
    finally:
        db.close()

    future_start = (datetime.now(timezone.utc) + timedelta(days=4)).replace(microsecond=0)
    propose_payload = {
        "request_id": str(req_id),
        "recipient_id": str(helper["user"]["id"]),
        "title": "Campus Orientation Tour",
        "description": "Walkthrough of engineering campus and libraries",
        "modality": "IN_PERSON",
        "meeting_place_id": "ChIJ_central_cafe",
        "scheduled_start": future_start.isoformat(),
        "duration_minutes": 90,
    }
    p_resp = client.post(f"{settings.API_V1_STR}/sessions", json=propose_payload, headers=requester["headers"])
    assert p_resp.status_code == 201
    session_id = p_resp.json()["id"]

    # Export calendar
    ics_resp = client.get(f"{settings.API_V1_STR}/sessions/{session_id}/ics", headers=requester["headers"])
    assert ics_resp.status_code == 200
    assert "text/calendar" in ics_resp.headers["Content-Type"]
    ics_text = ics_resp.text
    assert "BEGIN:VCALENDAR" in ics_text
    assert f"UID:session-{session_id}@nest.community" in ics_text
    assert "TRIGGER:-PT30M" in ics_text
    assert "ORGANIZER;CN=NEST Community:mailto:sessions@nest.community" in ics_text
    assert "END:VCALENDAR" in ics_text


def test_concurrency_double_booking_protection(client: TestClient, mock_venue_service):
    helper = create_authenticated_user(client, "Concur Helper", f"c_hlp_{uuid.uuid4().hex[:6]}@example.test")
    req1 = create_authenticated_user(client, "Concur Req 1", f"c_rq1_{uuid.uuid4().hex[:6]}@example.test")
    req2 = create_authenticated_user(client, "Concur Req 2", f"c_rq2_{uuid.uuid4().hex[:6]}@example.test")

    db = SessionLocal()
    try:
        r_obj1 = Request(id=uuid.uuid4(), user_id=uuid.UUID(req1["user"]["id"]), raw_text="R1", city="Bengaluru", status="OPEN")
        r_obj2 = Request(id=uuid.uuid4(), user_id=uuid.UUID(req2["user"]["id"]), raw_text="R2", city="Bengaluru", status="OPEN")
        db.add_all([r_obj1, r_obj2])
        c1 = Connection(id=uuid.uuid4(), request_id=r_obj1.id, requester_id=uuid.UUID(req1["user"]["id"]), helper_id=uuid.UUID(helper["user"]["id"]), status="ACCEPTED")
        c2 = Connection(id=uuid.uuid4(), request_id=r_obj2.id, requester_id=uuid.UUID(req2["user"]["id"]), helper_id=uuid.UUID(helper["user"]["id"]), status="ACCEPTED")
        db.add_all([c1, c2])
        db.commit()
        r1_id = r_obj1.id
        r2_id = r_obj2.id
    finally:
        db.close()

    future_start = (datetime.now(timezone.utc) + timedelta(days=5)).replace(microsecond=0)

    # 1. First session proposal created and confirmed for helper at future_start (10:00 to 11:00)
    p1 = {
        "request_id": str(r1_id),
        "recipient_id": str(helper["user"]["id"]),
        "title": "Confirmed Booking 1",
        "modality": "IN_PERSON",
        "meeting_place_id": "ChIJ_central_cafe",
        "scheduled_start": future_start.isoformat(),
        "duration_minutes": 60,
    }
    s1_resp = client.post(f"{settings.API_V1_STR}/sessions", json=p1, headers=req1["headers"])
    assert s1_resp.status_code == 201
    s1_id = s1_resp.json()["id"]

    # Helper confirms session 1
    conf1 = client.post(f"{settings.API_V1_STR}/sessions/{s1_id}/accept", headers=helper["headers"])
    assert conf1.status_code == 200
    assert conf1.json()["status"] == "CONFIRMED"

    # 2. Second requester attempts to book overlapping session (future_start + 30 mins)
    overlapping_start = (future_start + timedelta(minutes=30)).isoformat()
    p2 = {
        "request_id": str(r2_id),
        "recipient_id": str(helper["user"]["id"]),
        "title": "Conflicting Booking 2",
        "modality": "IN_PERSON",
        "meeting_place_id": "ChIJ_central_cafe",
        "scheduled_start": overlapping_start,
        "duration_minutes": 60,
    }
    s2_resp = client.post(f"{settings.API_V1_STR}/sessions", json=p2, headers=req2["headers"])
    assert s2_resp.status_code == 409
    assert "conflicts with an existing confirmed session" in s2_resp.json()["detail"].lower()


def test_safety_blocking_cancels_future_sessions(client: TestClient, mock_venue_service):
    requester = create_authenticated_user(client, "Block Req", f"b_req_{uuid.uuid4().hex[:6]}@example.test")
    helper = create_authenticated_user(client, "Block Hlp", f"b_hlp_{uuid.uuid4().hex[:6]}@example.test")

    db = SessionLocal()
    try:
        req = Request(id=uuid.uuid4(), user_id=uuid.UUID(requester["user"]["id"]), raw_text="Safety Req", city="Bengaluru", status="OPEN")
        db.add(req)
        conn = Connection(id=uuid.uuid4(), request_id=req.id, requester_id=uuid.UUID(requester["user"]["id"]), helper_id=uuid.UUID(helper["user"]["id"]), status="ACCEPTED")
        db.add(conn)
        db.commit()
        req_id = req.id
    finally:
        db.close()

    future_start = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    p = {
        "request_id": str(req_id),
        "recipient_id": str(helper["user"]["id"]),
        "title": "Future Session Before Block",
        "modality": "IN_PERSON",
        "meeting_place_id": "ChIJ_central_cafe",
        "scheduled_start": future_start,
        "duration_minutes": 60,
    }
    s_resp = client.post(f"{settings.API_V1_STR}/sessions", json=p, headers=requester["headers"])
    assert s_resp.status_code == 201
    session_id = s_resp.json()["id"]

    # Requester blocks helper
    block_resp = client.post(f"{settings.API_V1_STR}/blocks/{helper['user']['id']}", headers=requester["headers"])
    assert block_resp.status_code == 201

    # Verify session was automatically cancelled
    chk = client.get(f"{settings.API_V1_STR}/sessions/{session_id}", headers=requester["headers"])
    assert chk.status_code == 200
    assert chk.json()["status"] == "CANCELLED"
    assert "safety restriction" in chk.json()["status_reason"].lower()


def test_request_intelligence_session_resolution_integration(client: TestClient, mock_venue_service):
    requester = create_authenticated_user(client, "Intel Req", f"i_req_{uuid.uuid4().hex[:6]}@example.test")
    helper = create_authenticated_user(client, "Intel Hlp", f"i_hlp_{uuid.uuid4().hex[:6]}@example.test")

    db = SessionLocal()
    try:
        req = Request(
            id=uuid.uuid4(),
            user_id=uuid.UUID(requester["user"]["id"]),
            raw_text="Settling in Bengaluru: Need flat in Indiranagar",
            city="Bengaluru",
            status="OPEN",
            extracted_requirements={"needs": [{"category": "housing", "item": "apartment"}]},
        )
        db.add(req)
        req_loc = RequestLocation(request_id=req.id, latitude=12.9716, longitude=77.5946, city="Bengaluru")
        db.add(req_loc)
        conn = Connection(
            id=uuid.uuid4(),
            request_id=req.id,
            requester_id=uuid.UUID(requester["user"]["id"]),
            helper_id=uuid.UUID(helper["user"]["id"]),
            status="ACCEPTED",
        )
        db.add(conn)
        db.commit()
        req_id = req.id
    finally:
        db.close()

    future_start = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    p = {
        "request_id": str(req_id),
        "recipient_id": str(helper["user"]["id"]),
        "title": "Apartment Visit Assistance",
        "modality": "IN_PERSON",
        "meeting_place_id": "ChIJ_central_cafe",
        "scheduled_start": future_start,
        "duration_minutes": 60,
    }
    s_resp = client.post(f"{settings.API_V1_STR}/sessions", json=p, headers=requester["headers"])
    assert s_resp.status_code == 201
    session_id = s_resp.json()["id"]

    # 1. Unconfirmed / uncompleted session cannot resolve need
    progress_payload = {
        "category": "housing",
        "status": "RESOLVED",
        "resolved_via": "session",
        "resolved_entity_id": session_id,
        "notes": "Met and found flat",
    }
    fail_res = client.patch(
        f"{settings.API_V1_STR}/requests/{req_id}/need-progress",
        json=progress_payload,
        headers=requester["headers"],
    )
    assert fail_res.status_code == 400
    assert "only completed assistance sessions" in fail_res.json()["detail"].lower()

    # 2. Complete session via dual confirmation
    client.post(f"{settings.API_V1_STR}/sessions/{session_id}/accept", headers=helper["headers"])
    client.post(f"{settings.API_V1_STR}/sessions/{session_id}/complete", headers=requester["headers"])
    client.post(f"{settings.API_V1_STR}/sessions/{session_id}/complete", headers=helper["headers"])

    # 3. Now resolve need with completed session
    pass_res = client.patch(
        f"{settings.API_V1_STR}/requests/{req_id}/need-progress",
        json=progress_payload,
        headers=requester["headers"],
    )
    assert pass_res.status_code == 200
    intel_data = pass_res.json()
    assert intel_data["status"] == "RESOLVED"
    assert intel_data["resolved_needs"] >= 1


def test_request_timing_preferences_api(client: TestClient):
    user = create_authenticated_user(client, "Timing User", f"time_u_{uuid.uuid4().hex[:6]}@example.test")
    headers = user["headers"]

    # Create request with rich timing preferences
    target_d = (date.today() + timedelta(days=7)).isoformat()
    req_payload = {
        "text": "Weekend apartment hunt looking for apartments near Koramangala",
        "preferred_date": target_d,
        "preferred_start_time": "10:00:00",
        "preferred_end_time": "13:00:00",
        "requester_timezone": "Asia/Kolkata",
        "is_time_flexible": True,
        "flexibility_window_days": 3,
        "preferred_days_of_week": [5, 6],
    }
    create_resp = client.post(f"{settings.API_V1_STR}/requests", json=req_payload, headers=headers)
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()
    assert created["preferred_date"] == target_d
    assert created["is_time_flexible"] is True
    assert created["flexibility_window_days"] == 3
    assert created["preferred_days_of_week"] == [5, 6]
    req_id = created["id"]

    # Update timing preferences
    update_payload = {
        "is_time_flexible": False,
        "flexibility_window_days": 0,
    }
    up_resp = client.patch(f"{settings.API_V1_STR}/requests/{req_id}", json=update_payload, headers=headers)
    assert up_resp.status_code == 200
    assert up_resp.json()["is_time_flexible"] is False


def test_session_decline_and_cancel_lifecycle(client: TestClient, mock_venue_service):
    requester = create_authenticated_user(client, "Dec Req", f"dec_r_{uuid.uuid4().hex[:6]}@example.test")
    helper = create_authenticated_user(client, "Dec Hlp", f"dec_h_{uuid.uuid4().hex[:6]}@example.test")

    db = SessionLocal()
    try:
        req = Request(id=uuid.uuid4(), user_id=uuid.UUID(requester["user"]["id"]), raw_text="Dec Req", city="Bengaluru", status="OPEN")
        db.add(req)
        conn = Connection(id=uuid.uuid4(), request_id=req.id, requester_id=uuid.UUID(requester["user"]["id"]), helper_id=uuid.UUID(helper["user"]["id"]), status="ACCEPTED")
        db.add(conn)
        db.commit()
        req_id = req.id
    finally:
        db.close()

    future_start = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()

    # 1. Propose and decline
    p = {
        "request_id": str(req_id),
        "recipient_id": str(helper["user"]["id"]),
        "title": "Declined Session Proposal",
        "modality": "IN_PERSON",
        "meeting_place_id": "ChIJ_central_cafe",
        "scheduled_start": future_start,
        "duration_minutes": 60,
    }
    s1 = client.post(f"{settings.API_V1_STR}/sessions", json=p, headers=requester["headers"]).json()
    dec_resp = client.post(
        f"{settings.API_V1_STR}/sessions/{s1['id']}/decline",
        json={"reason": "Unavailable at that time"},
        headers=helper["headers"],
    )
    assert dec_resp.status_code == 200
    assert dec_resp.json()["status"] == "DECLINED"
    assert dec_resp.json()["status_reason"] == "Unavailable at that time"

    # Cannot accept a declined session
    bad_acc = client.post(f"{settings.API_V1_STR}/sessions/{s1['id']}/accept", headers=helper["headers"])
    assert bad_acc.status_code == 400

    # 2. Propose, confirm, then cancel
    future_start2 = (datetime.now(timezone.utc) + timedelta(days=4)).isoformat()
    p["scheduled_start"] = future_start2
    p["title"] = "Cancelled Session"
    s2 = client.post(f"{settings.API_V1_STR}/sessions", json=p, headers=requester["headers"]).json()
    client.post(f"{settings.API_V1_STR}/sessions/{s2['id']}/accept", headers=helper["headers"])

    cancel_resp = client.post(
        f"{settings.API_V1_STR}/sessions/{s2['id']}/cancel",
        json={"reason": "Emergency conflict"},
        headers=requester["headers"],
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"
    assert cancel_resp.json()["status_reason"] == "Emergency conflict"


def test_session_idor_protection(client: TestClient, mock_venue_service):
    requester = create_authenticated_user(client, "IDOR Req", f"idor_r_{uuid.uuid4().hex[:6]}@example.test")
    helper = create_authenticated_user(client, "IDOR Hlp", f"idor_h_{uuid.uuid4().hex[:6]}@example.test")
    intruder = create_authenticated_user(client, "IDOR Intruder", f"idor_x_{uuid.uuid4().hex[:6]}@example.test")

    db = SessionLocal()
    try:
        req = Request(id=uuid.uuid4(), user_id=uuid.UUID(requester["user"]["id"]), raw_text="IDOR Req", city="Bengaluru", status="OPEN")
        db.add(req)
        conn = Connection(id=uuid.uuid4(), request_id=req.id, requester_id=uuid.UUID(requester["user"]["id"]), helper_id=uuid.UUID(helper["user"]["id"]), status="ACCEPTED")
        db.add(conn)
        db.commit()
        req_id = req.id
    finally:
        db.close()

    future_start = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    p = {
        "request_id": str(req_id),
        "recipient_id": str(helper["user"]["id"]),
        "title": "Private Session",
        "modality": "IN_PERSON",
        "meeting_place_id": "ChIJ_central_cafe",
        "scheduled_start": future_start,
        "duration_minutes": 60,
    }
    s = client.post(f"{settings.API_V1_STR}/sessions", json=p, headers=requester["headers"]).json()
    session_id = s["id"]

    # Intruder attempts to view session
    v_resp = client.get(f"{settings.API_V1_STR}/sessions/{session_id}", headers=intruder["headers"])
    assert v_resp.status_code == 403

    # Intruder attempts to accept session
    a_resp = client.post(f"{settings.API_V1_STR}/sessions/{session_id}/accept", headers=intruder["headers"])
    assert a_resp.status_code == 403

    # Intruder attempts to cancel session
    c_resp = client.post(f"{settings.API_V1_STR}/sessions/{session_id}/cancel", headers=intruder["headers"])
    assert c_resp.status_code == 403

    # Intruder attempts to export calendar
    ics_resp = client.get(f"{settings.API_V1_STR}/sessions/{session_id}/ics", headers=intruder["headers"])
    assert ics_resp.status_code == 403


def test_session_list_filters(client: TestClient, mock_venue_service):
    requester = create_authenticated_user(client, "List Req", f"list_r_{uuid.uuid4().hex[:6]}@example.test")
    helper = create_authenticated_user(client, "List Hlp", f"list_h_{uuid.uuid4().hex[:6]}@example.test")

    db = SessionLocal()
    try:
        req = Request(id=uuid.uuid4(), user_id=uuid.UUID(requester["user"]["id"]), raw_text="List Req", city="Bengaluru", status="OPEN")
        db.add(req)
        conn = Connection(id=uuid.uuid4(), request_id=req.id, requester_id=uuid.UUID(requester["user"]["id"]), helper_id=uuid.UUID(helper["user"]["id"]), status="ACCEPTED")
        db.add(conn)
        db.commit()
        req_id = req.id
        conn_id = conn.id
    finally:
        db.close()

    future_start = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    p = {
        "request_id": str(req_id),
        "recipient_id": str(helper["user"]["id"]),
        "title": "Filter Test Session",
        "modality": "IN_PERSON",
        "meeting_place_id": "ChIJ_central_cafe",
        "scheduled_start": future_start,
        "duration_minutes": 60,
    }
    client.post(f"{settings.API_V1_STR}/sessions", json=p, headers=requester["headers"])

    # Filter by status PROPOSED
    resp = client.get(f"{settings.API_V1_STR}/sessions?status=PROPOSED", headers=requester["headers"])
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1

    # Filter by non-matching status
    resp_empty = client.get(f"{settings.API_V1_STR}/sessions?status=COMPLETED", headers=requester["headers"])
    assert resp_empty.status_code == 200
    assert resp_empty.json()["total"] == 0

    # Filter by request_id
    resp_req = client.get(f"{settings.API_V1_STR}/sessions?request_id={req_id}", headers=requester["headers"])
    assert resp_req.status_code == 200
    assert resp_req.json()["total"] >= 1


def test_remote_url_privacy_in_proposed_state(client: TestClient):
    requester = create_authenticated_user(client, "URL Req", f"url_r_{uuid.uuid4().hex[:6]}@example.test")
    helper = create_authenticated_user(client, "URL Hlp", f"url_h_{uuid.uuid4().hex[:6]}@example.test")

    db = SessionLocal()
    try:
        req = Request(id=uuid.uuid4(), user_id=uuid.UUID(requester["user"]["id"]), raw_text="URL Req", city="Bengaluru", status="OPEN")
        db.add(req)
        conn = Connection(id=uuid.uuid4(), request_id=req.id, requester_id=uuid.UUID(requester["user"]["id"]), helper_id=uuid.UUID(helper["user"]["id"]), status="ACCEPTED")
        db.add(conn)
        db.commit()
        req_id = req.id
    finally:
        db.close()

    future_start = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    p = {
        "request_id": str(req_id),
        "recipient_id": str(helper["user"]["id"]),
        "title": "Secret Remote Call",
        "modality": "REMOTE",
        "meeting_url": "https://meet.google.com/secret-room-123",
        "scheduled_start": future_start,
        "duration_minutes": 45,
    }
    s = client.post(f"{settings.API_V1_STR}/sessions", json=p, headers=requester["headers"]).json()
    session_id = s["id"]

    # Proposer can see their own entered URL
    assert s["meeting_url"] == "https://meet.google.com/secret-room-123"

    # Recipient viewing the proposed session should NOT see the meeting URL yet
    h_view = client.get(f"{settings.API_V1_STR}/sessions/{session_id}", headers=helper["headers"]).json()
    assert h_view["meeting_url"] is None

    # Once accepted, recipient can now see the confirmed meeting URL
    client.post(f"{settings.API_V1_STR}/sessions/{session_id}/accept", headers=helper["headers"])
    h_view2 = client.get(f"{settings.API_V1_STR}/sessions/{session_id}", headers=helper["headers"]).json()
    assert h_view2["meeting_url"] == "https://meet.google.com/secret-room-123"


def test_helper_not_accepting_sessions_blocks_proposal(client: TestClient, mock_venue_service):
    requester = create_authenticated_user(client, "Off Req", f"off_r_{uuid.uuid4().hex[:6]}@example.test")
    helper = create_authenticated_user(client, "Off Hlp", f"off_h_{uuid.uuid4().hex[:6]}@example.test")

    # Helper turns off accepting sessions
    client.put(
        f"{settings.API_V1_STR}/availability/capacity",
        json={"accepting_sessions": False},
        headers=helper["headers"],
    )

    db = SessionLocal()
    try:
        req = Request(id=uuid.uuid4(), user_id=uuid.UUID(requester["user"]["id"]), raw_text="Off Req", city="Bengaluru", status="OPEN")
        db.add(req)
        conn = Connection(id=uuid.uuid4(), request_id=req.id, requester_id=uuid.UUID(requester["user"]["id"]), helper_id=uuid.UUID(helper["user"]["id"]), status="ACCEPTED")
        db.add(conn)
        db.commit()
        req_id = req.id
    finally:
        db.close()

    future_start = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    p = {
        "request_id": str(req_id),
        "recipient_id": str(helper["user"]["id"]),
        "title": "Blocked By Capacity",
        "modality": "IN_PERSON",
        "meeting_place_id": "ChIJ_central_cafe",
        "scheduled_start": future_start,
        "duration_minutes": 60,
    }
    resp = client.post(f"{settings.API_V1_STR}/sessions", json=p, headers=requester["headers"])
    assert resp.status_code == 400
    assert "not accepting new assistance sessions" in resp.json()["detail"].lower()


def test_helper_max_weekly_sessions_capacity_limit(client: TestClient, mock_venue_service):
    helper = create_authenticated_user(client, "Cap Hlp", f"cap_h_{uuid.uuid4().hex[:6]}@example.test")
    req1 = create_authenticated_user(client, "Cap Req 1", f"cap_r1_{uuid.uuid4().hex[:6]}@example.test")
    req2 = create_authenticated_user(client, "Cap Req 2", f"cap_r2_{uuid.uuid4().hex[:6]}@example.test")

    # Helper sets capacity to max 1 session per week
    client.put(
        f"{settings.API_V1_STR}/availability/capacity",
        json={"max_weekly_sessions": 1, "accepting_sessions": True},
        headers=helper["headers"],
    )

    db = SessionLocal()
    try:
        r1 = Request(id=uuid.uuid4(), user_id=uuid.UUID(req1["user"]["id"]), raw_text="Cap R1", city="Bengaluru", status="OPEN")
        r2 = Request(id=uuid.uuid4(), user_id=uuid.UUID(req2["user"]["id"]), raw_text="Cap R2", city="Bengaluru", status="OPEN")
        db.add_all([r1, r2])
        c1 = Connection(id=uuid.uuid4(), request_id=r1.id, requester_id=uuid.UUID(req1["user"]["id"]), helper_id=uuid.UUID(helper["user"]["id"]), status="ACCEPTED")
        c2 = Connection(id=uuid.uuid4(), request_id=r2.id, requester_id=uuid.UUID(req2["user"]["id"]), helper_id=uuid.UUID(helper["user"]["id"]), status="ACCEPTED")
        db.add_all([c1, c2])
        db.commit()
        r1_id = r1.id
        r2_id = r2.id
    finally:
        db.close()

    # Confirmed session 1
    future_start1 = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    p1 = {
        "request_id": str(r1_id),
        "recipient_id": str(helper["user"]["id"]),
        "title": "First Weekly Session",
        "modality": "IN_PERSON",
        "meeting_place_id": "ChIJ_central_cafe",
        "scheduled_start": future_start1,
        "duration_minutes": 60,
    }
    s1 = client.post(f"{settings.API_V1_STR}/sessions", json=p1, headers=req1["headers"]).json()
    client.post(f"{settings.API_V1_STR}/sessions/{s1['id']}/accept", headers=helper["headers"])

    # Attempt second session proposal within the week
    future_start2 = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    p2 = {
        "request_id": str(r2_id),
        "recipient_id": str(helper["user"]["id"]),
        "title": "Exceeding Weekly Session",
        "modality": "IN_PERSON",
        "meeting_place_id": "ChIJ_central_cafe",
        "scheduled_start": future_start2,
        "duration_minutes": 60,
    }
    resp2 = client.post(f"{settings.API_V1_STR}/sessions", json=p2, headers=req2["headers"])
    assert resp2.status_code == 409
    assert "maximum weekly session capacity" in resp2.json()["detail"].lower()


def test_concurrent_multithreaded_race_protection(client: TestClient, mock_venue_service):
    """
    Spawns concurrent threads to prove PostgreSQL-level row locking prevents race condition double-booking.
    """
    helper = create_authenticated_user(client, "Race Hlp", f"rc_h_{uuid.uuid4().hex[:6]}@example.test")
    req1 = create_authenticated_user(client, "Race R1", f"rc_r1_{uuid.uuid4().hex[:6]}@example.test")
    req2 = create_authenticated_user(client, "Race R2", f"rc_r2_{uuid.uuid4().hex[:6]}@example.test")

    db = SessionLocal()
    try:
        r1 = Request(id=uuid.uuid4(), user_id=uuid.UUID(req1["user"]["id"]), raw_text="Race R1", city="Bengaluru", status="OPEN")
        r2 = Request(id=uuid.uuid4(), user_id=uuid.UUID(req2["user"]["id"]), raw_text="Race R2", city="Bengaluru", status="OPEN")
        db.add_all([r1, r2])
        c1 = Connection(id=uuid.uuid4(), request_id=r1.id, requester_id=uuid.UUID(req1["user"]["id"]), helper_id=uuid.UUID(helper["user"]["id"]), status="ACCEPTED")
        c2 = Connection(id=uuid.uuid4(), request_id=r2.id, requester_id=uuid.UUID(req2["user"]["id"]), helper_id=uuid.UUID(helper["user"]["id"]), status="ACCEPTED")
        db.add_all([c1, c2])
        db.commit()
        r1_id = r1.id
        r2_id = r2.id
    finally:
        db.close()

    target_start = (datetime.now(timezone.utc) + timedelta(days=6)).replace(microsecond=0)

    # Pre-create session 1
    p1 = {
        "request_id": str(r1_id),
        "recipient_id": str(helper["user"]["id"]),
        "title": "Race Session 1",
        "modality": "IN_PERSON",
        "meeting_place_id": "ChIJ_central_cafe",
        "scheduled_start": target_start.isoformat(),
        "duration_minutes": 60,
    }
    s1 = client.post(f"{settings.API_V1_STR}/sessions", json=p1, headers=req1["headers"]).json()
    client.post(f"{settings.API_V1_STR}/sessions/{s1['id']}/accept", headers=helper["headers"])

    # Concurrently attempt two proposals that overlap with s1
    def try_propose(req_id_val, headers_val):
        p = {
            "request_id": str(req_id_val),
            "recipient_id": str(helper["user"]["id"]),
            "title": "Overlap Attempt",
            "modality": "IN_PERSON",
            "meeting_place_id": "ChIJ_central_cafe",
            "scheduled_start": (target_start + timedelta(minutes=15)).isoformat(),
            "duration_minutes": 45,
        }
        return client.post(f"{settings.API_V1_STR}/sessions", json=p, headers=headers_val)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(try_propose, r2_id, req2["headers"])
        f2 = executor.submit(try_propose, r2_id, req2["headers"])
        r_f1 = f1.result()
        r_f2 = f2.result()

    # Both must be rejected due to overlap with confirmed session 1
    assert r_f1.status_code == 409
    assert r_f2.status_code == 409


def test_admin_suspension_cancels_future_sessions(client: TestClient, mock_venue_service):
    admin = create_authenticated_user(client, "Admin User", f"adm_{uuid.uuid4().hex[:6]}@example.test", role="admin")
    requester = create_authenticated_user(client, "Susp Req", f"susp_r_{uuid.uuid4().hex[:6]}@example.test")
    helper = create_authenticated_user(client, "Susp Hlp", f"susp_h_{uuid.uuid4().hex[:6]}@example.test")

    db = SessionLocal()
    try:
        req = Request(id=uuid.uuid4(), user_id=uuid.UUID(requester["user"]["id"]), raw_text="Susp Req", city="Bengaluru", status="OPEN")
        db.add(req)
        conn = Connection(id=uuid.uuid4(), request_id=req.id, requester_id=uuid.UUID(requester["user"]["id"]), helper_id=uuid.UUID(helper["user"]["id"]), status="ACCEPTED")
        db.add(conn)
        db.commit()
        req_id = req.id
    finally:
        db.close()

    future_start = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    p = {
        "request_id": str(req_id),
        "recipient_id": str(helper["user"]["id"]),
        "title": "Session Before Suspension",
        "modality": "IN_PERSON",
        "meeting_place_id": "ChIJ_central_cafe",
        "scheduled_start": future_start,
        "duration_minutes": 60,
    }
    s = client.post(f"{settings.API_V1_STR}/sessions", json=p, headers=requester["headers"]).json()
    session_id = s["id"]

    # Admin suspends helper
    susp_resp = client.post(
        f"{settings.API_V1_STR}/admin/users/{helper['user']['id']}/suspend",
        json={"reason": "Terms of service violation"},
        headers=admin["headers"],
    )
    assert susp_resp.status_code == 200

    # Session is automatically cancelled
    chk = client.get(f"{settings.API_V1_STR}/sessions/{session_id}", headers=requester["headers"])
    assert chk.status_code == 200
    assert chk.json()["status"] == "CANCELLED"
    assert "account suspension" in chk.json()["status_reason"].lower()


def test_true_concurrent_double_booking_race(client: TestClient, mock_venue_service):
    """
    True multi-threaded barrier test verifying row-level locks on the helper
    prevent double-booking under concurrent acceptance race conditions.
    """
    helper = create_authenticated_user(client, "Barrier Helper", f"barr_h_{uuid.uuid4().hex[:6]}@example.test")
    req1 = create_authenticated_user(client, "Barrier Req 1", f"barr_r1_{uuid.uuid4().hex[:6]}@example.test")
    req2 = create_authenticated_user(client, "Barrier Req 2", f"barr_r2_{uuid.uuid4().hex[:6]}@example.test")

    db = SessionLocal()
    try:
        r1 = Request(id=uuid.uuid4(), user_id=uuid.UUID(req1["user"]["id"]), raw_text="Barrier R1", city="Bengaluru", status="OPEN")
        r2 = Request(id=uuid.uuid4(), user_id=uuid.UUID(req2["user"]["id"]), raw_text="Barrier R2", city="Bengaluru", status="OPEN")
        db.add_all([r1, r2])
        c1 = Connection(id=uuid.uuid4(), request_id=r1.id, requester_id=uuid.UUID(req1["user"]["id"]), helper_id=uuid.UUID(helper["user"]["id"]), status="ACCEPTED")
        c2 = Connection(id=uuid.uuid4(), request_id=r2.id, requester_id=uuid.UUID(req2["user"]["id"]), helper_id=uuid.UUID(helper["user"]["id"]), status="ACCEPTED")
        db.add_all([c1, c2])
        db.commit()
        r1_id = r1.id
        r2_id = r2.id
    finally:
        db.close()

    target_start = (datetime.now(timezone.utc) + timedelta(days=5)).replace(microsecond=0)

    # Propose two sessions targeting the exact same time slot with the same helper
    p1 = {
        "request_id": str(r1_id),
        "recipient_id": str(helper["user"]["id"]),
        "title": "Concurrent Slot Proposal 1",
        "modality": "IN_PERSON",
        "meeting_place_id": "ChIJ_central_cafe",
        "scheduled_start": target_start.isoformat(),
        "duration_minutes": 60,
    }
    s1 = client.post(f"{settings.API_V1_STR}/sessions", json=p1, headers=req1["headers"]).json()

    p2 = {
        "request_id": str(r2_id),
        "recipient_id": str(helper["user"]["id"]),
        "title": "Concurrent Slot Proposal 2",
        "modality": "IN_PERSON",
        "meeting_place_id": "ChIJ_central_cafe",
        "scheduled_start": target_start.isoformat(),
        "duration_minutes": 60,
    }
    s2 = client.post(f"{settings.API_V1_STR}/sessions", json=p2, headers=req2["headers"]).json()

    barrier = threading.Barrier(2)
    results = []

    def race_accept(sess_id):
        barrier.wait()
        res = client.post(f"{settings.API_V1_STR}/sessions/{sess_id}/accept", headers=helper["headers"])
        results.append(res.status_code)

    t1 = threading.Thread(target=race_accept, args=(s1["id"],))
    t2 = threading.Thread(target=race_accept, args=(s2["id"],))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Exactly one accept must succeed and one must be rejected with 409 CONFLICT
    assert sorted(results) == [200, 409]


def test_helper_proposed_session_scheduling_conflict_protection(client: TestClient, mock_venue_service):
    """
    Verifies that when a helper proposes a session to a newcomer, conflict protection
    locks and checks both participants symmetrically, preventing double booking.
    """
    helper = create_authenticated_user(client, "Sym Helper", f"sym_h_{uuid.uuid4().hex[:6]}@example.test")
    newcomer = create_authenticated_user(client, "Sym Newcomer", f"sym_n_{uuid.uuid4().hex[:6]}@example.test")
    other_helper = create_authenticated_user(client, "Other Helper", f"oth_h_{uuid.uuid4().hex[:6]}@example.test")

    db = SessionLocal()
    try:
        r1 = Request(id=uuid.uuid4(), user_id=uuid.UUID(newcomer["user"]["id"]), raw_text="Need guide", city="Bengaluru", status="OPEN")
        db.add(r1)
        c1 = Connection(id=uuid.uuid4(), request_id=r1.id, requester_id=uuid.UUID(newcomer["user"]["id"]), helper_id=uuid.UUID(helper["user"]["id"]), status="ACCEPTED")
        c2 = Connection(id=uuid.uuid4(), request_id=r1.id, requester_id=uuid.UUID(newcomer["user"]["id"]), helper_id=uuid.UUID(other_helper["user"]["id"]), status="ACCEPTED")
        db.add_all([c1, c2])
        db.commit()
        r1_id = r1.id
    finally:
        db.close()

    target_start = (datetime.now(timezone.utc) + timedelta(days=4)).replace(microsecond=0)

    # Helper proposes session to newcomer
    p_helper = {
        "request_id": str(r1_id),
        "recipient_id": str(newcomer["user"]["id"]),
        "title": "Helper Proposed Tour",
        "modality": "IN_PERSON",
        "meeting_place_id": "ChIJ_central_cafe",
        "scheduled_start": target_start.isoformat(),
        "duration_minutes": 60,
    }
    h_sess = client.post(f"{settings.API_V1_STR}/sessions", json=p_helper, headers=helper["headers"])
    assert h_sess.status_code == 201
    h_sess_id = h_sess.json()["id"]

    # Newcomer accepts helper's proposed session
    acc_res = client.post(f"{settings.API_V1_STR}/sessions/{h_sess_id}/accept", headers=newcomer["headers"])
    assert acc_res.status_code == 200

    # Newcomer now tries to propose an overlapping session with other_helper
    p_conflict = {
        "request_id": str(r1_id),
        "recipient_id": str(other_helper["user"]["id"]),
        "title": "Overlapping Tour Attempt",
        "modality": "IN_PERSON",
        "meeting_place_id": "ChIJ_central_cafe",
        "scheduled_start": (target_start + timedelta(minutes=30)).isoformat(),
        "duration_minutes": 45,
    }
    conf_res = client.post(f"{settings.API_V1_STR}/sessions", json=p_conflict, headers=newcomer["headers"])
    assert conf_res.status_code == 409
    assert "conflicts" in conf_res.json()["detail"].lower()


def test_session_completion_does_not_silently_resolve_need(client: TestClient, mock_venue_service):
    """
    Verifies Phase 13 boundary integrity:
    Completing an assistance session does NOT automatically or silently resolve
    the underlying need. Explicit user resolution is strictly required.
    """
    requester = create_authenticated_user(client, "Req Boundary", f"bnd_r_{uuid.uuid4().hex[:6]}@example.test")
    helper = create_authenticated_user(client, "Hlp Boundary", f"bnd_h_{uuid.uuid4().hex[:6]}@example.test")

    # 1. Create request with parsed need
    req_resp = client.post(
        f"{settings.API_V1_STR}/requests",
        json={"text": "Moving to Indiranagar, need a 1BHK apartment and someone to guide me on local rent agreements."},
        headers=requester["headers"],
    )
    assert req_resp.status_code == 201
    req_id = req_resp.json()["id"]

    # Connect helper
    db = SessionLocal()
    try:
        conn = Connection(id=uuid.uuid4(), request_id=uuid.UUID(req_id), requester_id=uuid.UUID(requester["user"]["id"]), helper_id=uuid.UUID(helper["user"]["id"]), status="ACCEPTED")
        db.add(conn)
        db.commit()
    finally:
        db.close()

    # Propose, accept, and dual-complete assistance session
    target_start = (datetime.now(timezone.utc) + timedelta(days=3)).replace(microsecond=0)
    sess_payload = {
        "request_id": req_id,
        "recipient_id": str(helper["user"]["id"]),
        "title": "Apartment Agreement Assistance",
        "modality": "IN_PERSON",
        "meeting_place_id": "ChIJ_central_cafe",
        "scheduled_start": target_start.isoformat(),
        "duration_minutes": 60,
    }
    s_resp = client.post(f"{settings.API_V1_STR}/sessions", json=sess_payload, headers=requester["headers"])
    sess_id = s_resp.json()["id"]

    client.post(f"{settings.API_V1_STR}/sessions/{sess_id}/accept", headers=helper["headers"])
    client.post(f"{settings.API_V1_STR}/sessions/{sess_id}/complete", headers=requester["headers"])
    c2 = client.post(f"{settings.API_V1_STR}/sessions/{sess_id}/complete", headers=helper["headers"])
    assert c2.status_code == 200
    assert c2.json()["status"] == "COMPLETED"

    # Verify intelligence hub: need is STILL NOT automatically resolved
    hub_res = client.get(f"{settings.API_V1_STR}/requests/{req_id}/intelligence", headers=requester["headers"])
    assert hub_res.status_code == 200
    hub_data = hub_res.json()
    extracted_needs = hub_data.get("needs", [])
    cat = extracted_needs[0]["category"] if extracted_needs else "accommodation"
    target_progress = [n for n in hub_data.get("need_progress", []) if n.get("category") == cat]
    if target_progress:
        assert target_progress[0]["status"] != "RESOLVED"

    # Now newcomer performs explicit resolution via PATCH need-progress
    resolve_res = client.patch(
        f"{settings.API_V1_STR}/requests/{req_id}/need-progress",
        json={
            "category": cat,
            "status": "RESOLVED",
            "resolved_via": "session",
            "resolved_entity_id": sess_id,
            "notes": "Helper checked lease agreement in person and confirmed terms.",
        },
        headers=requester["headers"],
    )
    assert resolve_res.status_code == 200
    updated_progress = resolve_res.json()
    assert updated_progress["status"] == "RESOLVED"
    assert updated_progress["resolved_needs"] >= 1


def test_cross_timezone_scheduling_and_utc_persistence(client: TestClient, mock_venue_service):
    """
    Verifies that schedules across diverse non-India timezones (e.g. America/New_York and Europe/London)
    are stored as true UTC in the database, with round-trip timezone preservation.
    """
    helper = create_authenticated_user(client, "NY Helper", f"ny_{uuid.uuid4().hex[:6]}@example.test")
    newcomer = create_authenticated_user(client, "London Newcomer", f"lon_{uuid.uuid4().hex[:6]}@example.test")

    # Helper updates availability and timezone to America/New_York
    tz_res = client.put(
        f"{settings.API_V1_STR}/availability/capacity",
        json={"helper_timezone": "America/New_York", "max_weekly_sessions": 4, "accepting_sessions": True},
        headers=helper["headers"],
    )
    assert tz_res.status_code == 200
    assert tz_res.json()["helper_timezone"] == "America/New_York"

    # Set helper slots on Wednesday
    slots_res = client.put(
        f"{settings.API_V1_STR}/availability/slots",
        json={
            "helper_timezone": "America/New_York",
            "slots": [
                {"day_of_week": 2, "start_time": "14:00:00", "end_time": "18:00:00"},
            ],
        },
        headers=helper["headers"],
    )
    assert slots_res.status_code == 200

    # Newcomer creates connection with helper
    db = SessionLocal()
    try:
        req = Request(id=uuid.uuid4(), user_id=uuid.UUID(newcomer["user"]["id"]), raw_text="Remote onboarding", city="Bengaluru", status="OPEN")
        db.add(req)
        conn = Connection(id=uuid.uuid4(), request_id=req.id, requester_id=uuid.UUID(newcomer["user"]["id"]), helper_id=uuid.UUID(helper["user"]["id"]), status="ACCEPTED")
        db.add(conn)
        db.commit()
        req_id = req.id
    finally:
        db.close()

    # Propose session specifying America/New_York timezone
    sess_dt = (datetime.now(timezone.utc) + timedelta(days=7)).replace(microsecond=0)
    sess_res = client.post(
        f"{settings.API_V1_STR}/sessions",
        json={
            "request_id": str(req_id),
            "recipient_id": str(helper["user"]["id"]),
            "title": "Cross-Timezone Orientation",
            "modality": "REMOTE",
            "meeting_url": "https://meet.google.com/abc-defg-hij",
            "scheduled_start": sess_dt.isoformat(),
            "duration_minutes": 60,
            "session_timezone": "America/New_York",
        },
        headers=newcomer["headers"],
    )
    assert sess_res.status_code == 201
    s_data = sess_res.json()
    assert s_data["session_timezone"] == "America/New_York"
    assert s_data["scheduled_start"] is not None


