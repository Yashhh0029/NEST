import uuid
from datetime import datetime, timezone, timedelta
from fastapi import status
from fastapi.testclient import TestClient
from tests.conftest import create_authenticated_user


def test_complete_core_user_journey_e2e(client: TestClient):
    """
    End-to-End integration test covering the complete 17-point core user journey:
    1. User creates profile
    2. User sets Google Place location
    3. Profile location persists
    4. User creates request
    5. Explicit target location persists
    6. Request parser extracts relevant information
    7. Matching uses target location
    8. Helper location is evaluated correctly
    9. Blocked helper is excluded
    10. Match result is returned
    11. Connection can be created
    12. Duplicate connection is prevented
    13. Authorized users can access chat
    14. Unauthorized users cannot access chat
    15. Assistance session ownership works
    16. Missing profile location is handled correctly
    17. Cross-city relocation remains correct
    """
    # -------------------------------------------------------------
    # 1. User A (Newcomer) creates profile
    # -------------------------------------------------------------
    newcomer = create_authenticated_user(client, "Aarav Sharma", "aarav.s@example.test", role="newcomer")

    # 16. Verify missing profile location is handled gracefully initially
    init_profile = client.get("/api/profile/me", headers=newcomer["headers"])
    assert init_profile.status_code == status.HTTP_200_OK
    assert init_profile.json()["location"] is None

    profile_payload = {
        "headline": "Relocating Software Engineer",
        "bio": "Relocating from Pune for a new engineering role.",
        "occupation": "Software Engineer",
        "organization": "TechCorp",
        "years_experience": 2.0,
        "languages": ["English", "Hindi"],
        "help_description": None,
        "needs_description": "Need verified PG near Infopark Kakkanad.",
        "availability": True,
    }
    prof_resp = client.put("/api/profile/me", json=profile_payload, headers=newcomer["headers"])
    assert prof_resp.status_code == status.HTTP_200_OK
    assert prof_resp.json()["headline"] == profile_payload["headline"]

    # -------------------------------------------------------------
    # 2 & 3. User A sets Google Place location & it persists
    # Home city = Pune
    # -------------------------------------------------------------
    loc_payload = {
        "city": "Pune",
        "area": "Wakad",
        "state": "Maharashtra",
        "country": "India",
        "display_name": "ABC Society",
        "place_types": "residential,premise",
        "google_place_id": "ChIJ_pune_society_123",
        "formatted_address": "ABC Society, Wakad, Pune, Maharashtra 411057, India",
        "latitude": 18.5987,
        "longitude": 73.7654,
        "location_source": "google_places",
        "location_precision": "rooftop",
    }
    set_loc_resp = client.put("/api/profile/me/location", json=loc_payload, headers=newcomer["headers"])
    assert set_loc_resp.status_code == status.HTTP_200_OK

    # 3. Verify persistence
    me_resp = client.get("/api/profile/me", headers=newcomer["headers"])
    assert me_resp.status_code == status.HTTP_200_OK
    persisted_loc = me_resp.json()["location"]
    assert persisted_loc is not None
    assert persisted_loc["display_name"] == "ABC Society"
    assert persisted_loc["city"] == "Pune"
    assert persisted_loc["area"] == "Wakad"
    assert persisted_loc["google_place_id"] == "ChIJ_pune_society_123"

    # Public profile privacy check: coarse city/area only, no exact coords or place_id
    pub_profile = client.get(f"/api/profile/users/{newcomer['user']['id']}")
    assert pub_profile.status_code == status.HTTP_200_OK
    assert pub_profile.json()["location"]["city"] == "Pune"
    assert pub_profile.json()["location"]["area"] == "Wakad"
    assert "latitude" not in pub_profile.json()["location"]
    assert "formatted_address" not in pub_profile.json()["location"]

    # -------------------------------------------------------------
    # 4, 5, 6. User creates request with cross-city relocation
    # Home is Pune, but destination is Kakkanad, Kochi!
    # -------------------------------------------------------------
    req_text = "I am moving to Kakkanad, Kochi and need help finding a PG under 10k"
    req_resp = client.post(
        "/api/requests",
        json={
            "text": req_text,
            "target_city": "Kochi",
            "target_area": "Kakkanad",
        },
        headers=newcomer["headers"],
    )
    assert req_resp.status_code == status.HTTP_201_CREATED
    req_data = req_resp.json()
    req_id = req_data["id"]

    # 5. Explicit target location persists (Kochi / Kakkanad, NOT Pune)
    assert req_data["city"] == "Kochi"
    assert req_data["area"] == "Kakkanad"
    assert req_data["status"] == "OPEN"
    assert req_data["user_id"] == newcomer["user"]["id"]

    # 6. Parser extracted relevant information
    assert req_data["budget_amount"] == 10000.0
    assert req_data["extracted_requirements"] is not None

    # Verify dedicated request location endpoint
    target_loc_resp = client.get(f"/api/location/request/{req_id}", headers=newcomer["headers"])
    assert target_loc_resp.status_code == status.HTTP_200_OK
    assert target_loc_resp.json()["city"] == "Kochi"
    assert target_loc_resp.json()["area"] == "Kakkanad"

    # -------------------------------------------------------------
    # Setup Candidate Helpers:
    # Helper 1: Located in Kakkanad, Kochi (Matching destination)
    # Helper 2: Located in Pune (Requester's home, but WRONG destination!)
    # Helper 3: Located in Kochi, but will be BLOCKED
    # -------------------------------------------------------------
    helper_kochi = create_authenticated_user(client, "Ravi Nair", "ravi.nair@example.test", role="helper")
    client.put("/api/profile/me", json={
        "headline": "Kakkanad Local Guide & IT Professional",
        "bio": "Living in Kakkanad, Kochi for 5 years. Know all PGs and mess services.",
        "years_experience": 5.0,
        "languages": ["Malayalam", "English", "Hindi"],
        "help_description": "Can help newcomers find verified PGs in Kakkanad and Infopark transit.",
        "availability": True,
    }, headers=helper_kochi["headers"])
    client.put("/api/profile/me/location", json={
        "city": "Kochi",
        "area": "Kakkanad",
        "state": "Kerala",
        "country": "India",
        "latitude": 10.0159,
        "longitude": 76.3419,
    }, headers=helper_kochi["headers"])
    client.post("/api/profile/me/skills", json={"name": "Kakkanad PG Guidance", "proficiency": "expert"}, headers=helper_kochi["headers"])

    # Helper 2 (Pune)
    helper_pune = create_authenticated_user(client, "Suresh Patil", "suresh.p@example.test", role="helper")
    client.put("/api/profile/me", json={
        "headline": "Pune Resident",
        "bio": "Living in Wakad, Pune.",
        "years_experience": 4.0,
        "help_description": "Pune local advice",
        "availability": True,
    }, headers=helper_pune["headers"])
    client.put("/api/profile/me/location", json={
        "city": "Pune",
        "area": "Wakad",
        "state": "Maharashtra",
        "latitude": 18.5987,
        "longitude": 73.7654,
    }, headers=helper_pune["headers"])

    # Helper 3 (Kochi, to be blocked)
    helper_blocked = create_authenticated_user(client, "Bad Actor", "bad.actor@example.test", role="helper")
    client.put("/api/profile/me", json={
        "headline": "Kochi Helper",
        "bio": "In Kochi.",
        "availability": True,
    }, headers=helper_blocked["headers"])
    client.put("/api/profile/me/location", json={
        "city": "Kochi",
        "area": "Kakkanad",
        "latitude": 10.0159,
        "longitude": 76.3419,
    }, headers=helper_blocked["headers"])

    # -------------------------------------------------------------
    # 9. Block helper_blocked
    # -------------------------------------------------------------
    block_resp = client.post(
        f"/api/blocks/{helper_blocked['user']['id']}",
        headers=newcomer["headers"],
    )
    assert block_resp.status_code == status.HTTP_201_CREATED

    # -------------------------------------------------------------
    # 7, 8, 10, 17. Matching Engine Query
    # Must use TARGET location (Kakkanad, Kochi)
    # Helper in Kakkanad must rank high, Helper in Pune must have low location score
    # Blocked helper MUST be excluded
    # -------------------------------------------------------------
    match_resp = client.post(
        "/api/matching/find-matches",
        json={"request_id": req_id},
        headers=newcomer["headers"],
    )
    assert match_resp.status_code == status.HTTP_200_OK
    match_data = match_resp.json()

    # 10. Match result structure returned
    assert "matches" in match_data
    assert "target_location" in match_data
    assert match_data["target_location"]["city"] == "Kochi"

    candidate_ids = [m["user_id"] for m in match_data["matches"]]

    # 9. Blocked user must NOT be in matches
    assert str(helper_blocked["user"]["id"]) not in candidate_ids

    # 8 & 17. Kochi helper must be ranked, and have higher location score than Pune helper
    kochi_match = next((m for m in match_data["matches"] if m["user_id"] == str(helper_kochi["user"]["id"])), None)
    assert kochi_match is not None, "Kochi helper should be matched for Kochi target request"
    assert kochi_match["scores"]["location_score"] >= 0.85, "Location score in same area should be high"
    assert len(kochi_match["reasons"]) > 0, "Factual match reasons should be provided"

    # Pune helper if present should have low location score (< 0.20) because target is Kochi!
    pune_match = next((m for m in match_data["matches"] if m["user_id"] == str(helper_pune["user"]["id"])), None)
    if pune_match:
        assert pune_match["scores"]["location_score"] <= 0.10, "Cross-city helper must have very low location score"

    # -------------------------------------------------------------
    # 11 & 12. Connection Creation & Duplicate Prevention
    # -------------------------------------------------------------
    conn_create_resp = client.post(
        "/api/connections",
        json={
            "request_id": req_id,
            "helper_id": str(helper_kochi["user"]["id"]),
            "initial_message": "Hi Ravi, saw you know Kakkanad well! Could you help me find a PG?",
        },
        headers=newcomer["headers"],
    )
    assert conn_create_resp.status_code == status.HTTP_201_CREATED
    conn_data = conn_create_resp.json()
    conn_id = conn_data["id"]
    assert conn_data["status"] == "PENDING"
    assert conn_data["requester_id"] == newcomer["user"]["id"]
    assert conn_data["helper_id"] == str(helper_kochi["user"]["id"])

    # 12. Duplicate connection prevention
    dup_resp = client.post(
        "/api/connections",
        json={
            "request_id": req_id,
            "helper_id": str(helper_kochi["user"]["id"]),
        },
        headers=newcomer["headers"],
    )
    assert dup_resp.status_code == status.HTTP_409_CONFLICT

    # Helper accepts connection
    accept_resp = client.patch(
        f"/api/connections/{conn_id}",
        json={"action": "accept"},
        headers=helper_kochi["headers"],
    )
    assert accept_resp.status_code == status.HTTP_200_OK
    assert accept_resp.json()["status"] == "ACCEPTED"

    # -------------------------------------------------------------
    # 13 & 14. Chat Authorization
    # -------------------------------------------------------------
    # Authorized participant (Newcomer) creates/retrieves conversation
    conv_resp = client.post(
        "/api/conversations",
        json={"connection_id": conn_id},
        headers=newcomer["headers"],
    )
    assert conv_resp.status_code == status.HTTP_201_CREATED
    conv_id = conv_resp.json()["id"]

    # Send message
    msg_send_resp = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "Hello Ravi, excited to connect!"},
        headers=newcomer["headers"],
    )
    assert msg_send_resp.status_code == status.HTTP_201_CREATED

    # Helper reads conversation messages
    msgs_resp = client.get(
        f"/api/conversations/{conv_id}/messages",
        headers=helper_kochi["headers"],
    )
    assert msgs_resp.status_code == status.HTTP_200_OK
    assert len(msgs_resp.json()["messages"]) >= 1

    # 14. Unauthorized user C cannot access chat
    user_unauth = create_authenticated_user(client, "Stranger User", "stranger@example.test")
    unauth_conv_resp = client.get(
        f"/api/conversations/{conv_id}/messages",
        headers=user_unauth["headers"],
    )
    assert unauth_conv_resp.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]

    # -------------------------------------------------------------
    # 15. Assistance Session Ownership
    # -------------------------------------------------------------
    future_start = (datetime.now(timezone.utc) + timedelta(days=2)).replace(minute=0, second=0, microsecond=0)

    sess_create_resp = client.post(
        "/api/sessions",
        json={
            "request_id": req_id,
            "recipient_id": str(helper_kochi["user"]["id"]),
            "title": "PG Search & Area Orientation",
            "modality": "REMOTE",
            "scheduled_start": future_start.isoformat(),
            "duration_minutes": 60,
            "meeting_url": "https://meet.google.com/abc-defg-hij",
        },
        headers=newcomer["headers"],
    )
    assert sess_create_resp.status_code == status.HTTP_201_CREATED
    sess_id = sess_create_resp.json()["id"]

    # Authorized participant views session
    sess_get = client.get(f"/api/sessions/{sess_id}", headers=helper_kochi["headers"])
    assert sess_get.status_code == status.HTTP_200_OK
    assert sess_get.json()["title"] == "PG Search & Area Orientation"

    # Unauthorized user gets 403 Forbidden
    unauth_sess = client.get(f"/api/sessions/{sess_id}", headers=user_unauth["headers"])
    assert unauth_sess.status_code == status.HTTP_403_FORBIDDEN
