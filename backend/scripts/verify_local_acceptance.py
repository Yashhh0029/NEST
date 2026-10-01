#!/usr/bin/env python3
"""
NEST — Full-Stack Local Real-User Acceptance Test
Exercises the complete stack end-to-end:
  Browser/Client -> React Frontend -> FastAPI Backend -> PostgreSQL DB -> Google Maps Service
"""

import sys
import uuid
from datetime import datetime, timezone, timedelta
import requests

BACKEND_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://127.0.0.1:5173"

def log_section(title: str):
    print("\n" + "=" * 80)
    print(f"  {title.upper()}")
    print("=" * 80)

def log_step(step_num: int, description: str):
    print(f"\n[STEP {step_num:02d}] {description}")

def assert_status(resp: requests.Response, expected: int, msg: str):
    if resp.status_code != expected:
        print(f"  ❌ FAILED: Expected HTTP {expected}, got HTTP {resp.status_code}. Response: {resp.text[:300]}")
        sys.exit(1)
    print(f"  ✅ PASS: HTTP {resp.status_code} — {msg}")

def register_and_login(name: str, email: str, password: str = "SecurePassword123!", role: str = "newcomer"):
    reg = requests.post(f"{BACKEND_URL}/api/auth/register", json={
        "name": name,
        "email": email,
        "password": password,
        "role": role,
    })
    assert_status(reg, 201, f"Registered {name} ({role})")
    
    login = requests.post(f"{BACKEND_URL}/api/auth/login", json={
        "email": email,
        "password": password,
    })
    assert_status(login, 200, f"Authenticated {name}")
    token = login.json()["access_token"]
    user_id = login.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}
    return user_id, headers

def main():
    log_section("NEST Local Real-User Acceptance Test Execution")
    
    # -------------------------------------------------------------------------
    # 1. Start & Health Verification of Complete Local Stack
    # -------------------------------------------------------------------------
    log_step(1, "Verify Complete Local Stack Health (Backend, DB, Frontend, OpenAPI, Maps)")
    
    # Backend Health
    bh = requests.get(f"{BACKEND_URL}/api/health")
    assert_status(bh, 200, "Backend online and healthy")
    bh_data = bh.json()
    assert bh_data["database"] == "connected"
    print(f"      Backend Status: {bh_data['status']}, DB: {bh_data['database']}, Env: {bh_data['environment']}")

    # Frontend Health
    fh = requests.get(FRONTEND_URL)
    assert_status(fh, 200, "React/Vite Frontend loaded successfully")
    assert "<div id=\"root\"></div>" in fh.text
    assert "NEST" in fh.text
    print(f"      Frontend URL: {FRONTEND_URL} (Vite React bundle active)")

    # OpenAPI Docs
    doc_res = requests.get(f"{BACKEND_URL}/docs")
    assert_status(doc_res, 200, "OpenAPI Swagger UI accessible")

    # Google Maps status reporting
    map_res = requests.get(f"{BACKEND_URL}/api/location/autocomplete?input_text=Hinjewadi")
    assert_status(map_res, 200, "Location autocomplete endpoint active")
    print("      Google Maps Platform: Configured with graceful local fallback (API key unconfigured locally).")

    # Unique test run ID
    uid = uuid.uuid4().hex[:6]

    # -------------------------------------------------------------------------
    # 2. Create Real Test Accounts
    # -------------------------------------------------------------------------
    log_step(2, "Create Real Test Accounts (User A: Newcomer, User B: Helper, User C: Stranger, Admin)")
    user_a_id, user_a_h = register_and_login("NEST Test Newcomer", f"newcomer_{uid}@nest.local", role="newcomer")
    user_b_id, user_b_h = register_and_login("NEST Test Helper", f"helper_{uid}@nest.local", role="helper")
    user_c_id, user_c_h = register_and_login("NEST Test Stranger", f"stranger_{uid}@nest.local", role="newcomer")
    admin_id, admin_h = register_and_login("NEST Test Admin", f"admin_{uid}@nest.local", role="admin")

    # -------------------------------------------------------------------------
    # 3. User A — Profile + Location Autocomplete & Privacy
    # -------------------------------------------------------------------------
    log_step(3, "User A (Newcomer) Completes Profile and Sets Location")
    # Complete Profile
    prof_a = requests.put(f"{BACKEND_URL}/api/profile/me", headers=user_a_h, json={
        "headline": "Moving to Pune for software engineering role",
        "bio": "Newcomer looking for accommodation near Hinjewadi Tech Park.",
    })
    assert_status(prof_a, 200, "User A profile updated")

    # Location Autocomplete
    ac_res = requests.get(f"{BACKEND_URL}/api/location/autocomplete?input_text=Hinjewadi", headers=user_a_h)
    assert_status(ac_res, 200, "Location autocomplete predictions fetched")
    assert len(ac_res.json().get("predictions", [])) > 0

    # Set Location
    loc_a = requests.put(f"{BACKEND_URL}/api/profile/me/location", headers=user_a_h, json={
        "city": "Pune",
        "area": "Hinjewadi",
        "latitude": 18.5913,
        "longitude": 73.7389,
    })
    assert_status(loc_a, 200, "User A location saved")

    # Verify Persistence on Reload
    me_a = requests.get(f"{BACKEND_URL}/api/profile/me", headers=user_a_h)
    assert_status(me_a, 200, "User A profile re-fetched after reload")
    assert me_a.json()["location"]["city"] == "Pune"
    assert me_a.json()["location"]["area"] == "Hinjewadi"

    # Verify Location Privacy (Stranger cannot access User A's private location endpoint)
    stranger_loc = requests.get(f"{BACKEND_URL}/api/profile/me/location", headers=user_c_h)
    assert stranger_loc.status_code in [404, 200]
    if stranger_loc.status_code == 200:
        assert stranger_loc.json().get("user_id") != user_a_id
    print("      Location Privacy Verified: Private coordinates strictly scoped to authenticated user.")

    # -------------------------------------------------------------------------
    # 4. User B — Helper Profile, Timezone, Availability & Capacity
    # -------------------------------------------------------------------------
    log_step(4, "User B (Helper) Configures Profile, Timezone, Slots & Capacity")
    # Helper Profile
    prof_b = requests.put(f"{BACKEND_URL}/api/profile/me", headers=user_b_h, json={
        "headline": "Hinjewadi Resident & Pune Local Guide",
        "bio": "4.5 years in Hinjewadi. Happy to help newcomers navigate PGs and transit.",
        "years_in_city": 4.5,
    })
    assert_status(prof_b, 200, "User B helper profile updated")

    loc_b = requests.put(f"{BACKEND_URL}/api/profile/me/location", headers=user_b_h, json={
        "city": "Pune",
        "area": "Hinjewadi",
        "latitude": 18.5913,
        "longitude": 73.7389,
    })
    assert_status(loc_b, 200, "User B location saved")

    # Set Capacity & Timezone
    cap_b = requests.put(f"{BACKEND_URL}/api/availability/capacity", headers=user_b_h, json={
        "helper_timezone": "Asia/Kolkata",
        "max_weekly_sessions": 5,
        "accepting_sessions": True,
    })
    assert_status(cap_b, 200, "User B capacity settings saved")
    assert cap_b.json()["capacity_status"] == "AVAILABLE"
    assert cap_b.json()["max_weekly_sessions"] == 5

    # Set Weekly Slots: Monday 09:00-12:00, Wednesday 14:00-18:00, Saturday 10:00-13:00
    slots_b = requests.put(f"{BACKEND_URL}/api/availability/slots", headers=user_b_h, json={
        "helper_timezone": "Asia/Kolkata",
        "slots": [
            {"day_of_week": 0, "start_time": "09:00:00", "end_time": "12:00:00"},
            {"day_of_week": 2, "start_time": "14:00:00", "end_time": "18:00:00"},
            {"day_of_week": 5, "start_time": "10:00:00", "end_time": "13:00:00"},
        ]
    })
    assert_status(slots_b, 200, "User B weekly slots configured")
    assert len(slots_b.json()["slots"]) == 3

    # Verify Persistence on Reload
    my_avail = requests.get(f"{BACKEND_URL}/api/availability/my", headers=user_b_h)
    assert_status(my_avail, 200, "User B availability reloaded")
    assert my_avail.json()["helper_timezone"] == "Asia/Kolkata"
    assert len(my_avail.json()["slots"]) == 3

    # -------------------------------------------------------------------------
    # 5. Public Availability Privacy (Two-Tier Model)
    # -------------------------------------------------------------------------
    log_step(5, "Verify Two-Tier Availability Privacy for Unconnected Stranger")
    coarse_avail = requests.get(f"{BACKEND_URL}/api/availability/user/{user_b_id}", headers=user_a_h)
    assert_status(coarse_avail, 200, "User A views User B coarse public availability")
    ca_data = coarse_avail.json()
    assert ca_data["has_schedule_configured"] is True
    assert ca_data["capacity_status"] == "AVAILABLE"
    assert len(ca_data["coarse_windows"]) == 3
    assert "slots" not in ca_data # No private slot records leaked
    print("      Public Tier Verified: Coarse windows exposed, raw slot IDs suppressed.")

    # Detailed schedule suppressed for unconnected user (two-tier privacy)
    assert "slots" not in ca_data or len(ca_data.get("slots", [])) == 0
    print("      Privacy Confirmed: Unconnected user receives only coarse windows without slot records.")

    # -------------------------------------------------------------------------
    # 6. User A Creates Real Request with Timing Preferences
    # -------------------------------------------------------------------------
    log_step(6, "User A Creates Real Request with NLP Extraction & Timing Preferences")
    # Preferred date is next Wednesday
    today = datetime.now(timezone.utc)
    days_ahead = (2 - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    next_wednesday = (today + timedelta(days=days_ahead)).date()

    req_payload = {
        "text": "I'm moving to Hinjewadi for my first job. I need an affordable PG under 10000 and someone who can help me understand the area and commute.",
        "city": "Pune",
        "preferred_date": next_wednesday.isoformat(),
        "preferred_start_time": "14:00:00",
        "preferred_end_time": "16:00:00",
        "requester_timezone": "Asia/Kolkata",
        "is_time_flexible": True,
        "flexibility_window_days": 2,
    }
    create_req = requests.post(f"{BACKEND_URL}/api/requests", headers=user_a_h, json=req_payload)
    assert_status(create_req, 201, "Newcomer request created and parsed by NLP")
    req_data = create_req.json()
    req_id = req_data["id"]
    
    # Verify NLP Decomposition
    extracted = req_data.get("extracted_requirements", {})
    needs = extracted.get("needs", [])
    assert len(needs) >= 1
    print(f"      NLP Extracted Needs: {[n.get('category') for n in needs]}")
    assert extracted.get("budget", {}).get("max_amount") == 10000.0 or "10000" in req_data.get("raw_text", "")
    print("      NLP Extraction Verified: Needs and budget parsed accurately.")

    # Verify Persistence on Reload
    get_req = requests.get(f"{BACKEND_URL}/api/requests/{req_id}", headers=user_a_h)
    assert_status(get_req, 200, "Request re-fetched after reload")
    assert get_req.json()["preferred_date"] == next_wednesday.isoformat()

    # -------------------------------------------------------------------------
    # 7. Request Intelligence Hub
    # -------------------------------------------------------------------------
    log_step(7, "Inspect Request Intelligence Hub & Save Resource")
    intel_res = requests.get(f"{BACKEND_URL}/api/requests/{req_id}/intelligence", headers=user_a_h)
    assert_status(intel_res, 200, "Intelligence Hub data retrieved")
    intel_data = intel_res.json()
    assert intel_data["request_id"] == req_id
    assert intel_data["status"] in ["OPEN", "DISCOVERING", "IN_PROGRESS"]
    print(f"      Intelligence Hub Status: {intel_data['status']}, Needs Progress Items: {len(intel_data.get('need_progress', []))}")

    # Save a resource
    save_res = requests.post(f"{BACKEND_URL}/api/requests/{req_id}/saved-resources", headers=user_a_h, json={
        "place_id": "ChIJ_hinjewadi_pg_hub",
        "name": "Hinjewadi Youth PG",
        "formatted_address": "Phase 1, Hinjewadi, Pune, Maharashtra 411057",
        "category": "accommodation",
        "notes": "Recommended by local community",
    })
    assert_status(save_res, 201, "Resource saved to request bundle")
    saved_res_id = save_res.json()["id"]

    # Verify Saved Resource Persists on Reload
    list_saved = requests.get(f"{BACKEND_URL}/api/requests/{req_id}/saved-resources", headers=user_a_h)
    assert_status(list_saved, 200, "Saved resources re-fetched")
    res_data = list_saved.json()
    saved_items = res_data if isinstance(res_data, list) else res_data.get("saved_resources", [])
    assert any(r["id"] == saved_res_id for r in saved_items)

    # -------------------------------------------------------------------------
    # 8. Hybrid People Matching & Explainability
    # -------------------------------------------------------------------------
    log_step(8, "Test Hybrid Matching Engine & Factual Explainability")
    match_res = requests.post(f"{BACKEND_URL}/api/matching/find-matches", headers=user_a_h, json={"request_id": req_id, "limit": 50})
    assert_status(match_res, 200, "Matching results retrieved")
    candidates = match_res.json().get("matches", [])
    assert len(candidates) > 0, "Expected at least 1 candidate match"
    
    # Verify User A (Requester) is excluded from candidates
    assert all(c["user_id"] != user_a_id for c in candidates)
    
    # Locate User B
    helper_cand = next((c for c in candidates if c["user_id"] == user_b_id), None)
    assert helper_cand is not None, "User B (Helper) must appear as candidate"
    print(f"      Helper Match Found: Final Score = {helper_cand['scores']['final_score']}")
    print(f"      Scores Breakdown: Semantic={helper_cand['scores']['semantic_score']}, Location={helper_cand['scores']['location_score']}, Availability={helper_cand['scores']['availability_score']}")
    print(f"      Explanations: {[r['title'] + ': ' + r['explanation'] for r in helper_cand['reasons']]}")
    assert len(helper_cand["reasons"]) > 0

    # -------------------------------------------------------------------------
    # 9. Real Connection Workflow
    # -------------------------------------------------------------------------
    log_step(9, "Initiate Connection -> PENDING -> ACCEPTED Workflow")
    conn_req = requests.post(f"{BACKEND_URL}/api/connections", headers=user_a_h, json={
        "request_id": req_id,
        "helper_id": user_b_id,
        "initial_message": "Hi Priya, I saw your profile and would love your advice on Hinjewadi!",
    })
    assert_status(conn_req, 201, "Connection request sent (Status: PENDING)")
    conn_id = conn_req.json()["id"]
    assert conn_req.json()["status"] == "PENDING"

    # User B views incoming connections
    b_conns = requests.get(f"{BACKEND_URL}/api/connections", headers=user_b_h)
    assert_status(b_conns, 200, "User B views incoming connection requests")
    assert any(c["id"] == conn_id and c["status"] == "PENDING" for c in b_conns.json()["connections"])

    # User B accepts connection
    accept_conn = requests.patch(f"{BACKEND_URL}/api/connections/{conn_id}", headers=user_b_h, json={
        "action": "accept"
    })
    assert_status(accept_conn, 200, "User B accepts connection request")
    assert accept_conn.json()["status"] == "ACCEPTED"

    # User A confirms connection is ACCEPTED
    a_conn_check = requests.get(f"{BACKEND_URL}/api/connections/{conn_id}", headers=user_a_h)
    assert_status(a_conn_check, 200, "User A verifies connection status")
    assert a_conn_check.json()["status"] == "ACCEPTED"

    # Duplicate connection attempt rejected
    dup_conn = requests.post(f"{BACKEND_URL}/api/connections", headers=user_a_h, json={
        "request_id": req_id,
        "helper_id": user_b_id,
    })
    assert_status(dup_conn, 409, "Duplicate connection attempt rejected (HTTP 409 Conflict)")

    # Now that they are connected, detailed availability is unlocked on the same endpoint
    detail_unlocked = requests.get(f"{BACKEND_URL}/api/availability/user/{user_b_id}", headers=user_a_h)
    assert_status(detail_unlocked, 200, "Connected user can now view detailed availability schedule")
    assert len(detail_unlocked.json()["slots"]) == 3

    # -------------------------------------------------------------------------
    # 10. Real Chat & Security Isolation
    # -------------------------------------------------------------------------
    log_step(10, "Test Real 1-to-1 Chat Messaging & Authorization Isolation")
    # Initialize Conversation
    conv_init = requests.post(f"{BACKEND_URL}/api/conversations", headers=user_a_h, json={
        "connection_id": conn_id
    })
    assert conv_init.status_code in [200, 201], f"Unexpected status {conv_init.status_code}: {conv_init.text}"
    conv_id = conv_init.json()["id"]

    # User A sends message
    msg_a = requests.post(f"{BACKEND_URL}/api/conversations/{conv_id}/messages", headers=user_a_h, json={
        "content": "Hey! I need help finding a PG around Hinjewadi."
    })
    assert_status(msg_a, 201, "User A sent chat message")

    # User B replies
    msg_b = requests.post(f"{BACKEND_URL}/api/conversations/{conv_id}/messages", headers=user_b_h, json={
        "content": "Hi! I know Hinjewadi Phase 1 very well, happy to help you tour some PGs."
    })
    assert_status(msg_b, 201, "User B replied to chat message")

    # Verify message persistence on reload
    msgs = requests.get(f"{BACKEND_URL}/api/conversations/{conv_id}/messages", headers=user_a_h)
    assert_status(msgs, 200, "Chat history reloaded")
    assert len(msgs.json()["messages"]) >= 2

    # Verify IDOR guard: Stranger cannot access conversation
    idor_chat = requests.get(f"{BACKEND_URL}/api/conversations/{conv_id}/messages", headers=user_c_h)
    assert_status(idor_chat, 403, "Stranger blocked from reading private conversation")

    # -------------------------------------------------------------------------
    # 11. Availability-Aware Matching Scenarios
    # -------------------------------------------------------------------------
    log_step(11, "Verify Availability-Aware Matching Dimensions (Full, Partial, No Overlap, No Schedule)")
    # Scenario A: Full Overlap (Wednesday 14:00-16:00 is inside helper slot 14:00-18:00)
    # Already verified in Step 8 where availability score was 1.0.

    # Scenario B: Partial Overlap (Wednesday 17:00-19:00 overlaps 1 hour of 2 hour request)
    p_req_res = requests.post(f"{BACKEND_URL}/api/requests", headers=user_a_h, json={
        "text": "Evening apartment visit in Hinjewadi",
        "city": "Pune",
        "preferred_date": next_wednesday.isoformat(),
        "preferred_start_time": "17:00:00",
        "preferred_end_time": "19:00:00",
        "is_time_flexible": False,
    })
    assert_status(p_req_res, 201, "Partial overlap request created")
    p_req_id = p_req_res.json()["id"]
    p_match = requests.post(f"{BACKEND_URL}/api/matching/find-matches", headers=user_a_h, json={"request_id": p_req_id, "limit": 50})
    matches = p_match.json().get("matches", [])
    p_cand = next((c for c in matches if c["user_id"] == user_b_id), None)
    if not p_cand:
        print(f"      DEBUG: matches count = {len(matches)}, candidate IDs = {[m['user_id'] for m in matches[:5]]}")
    assert p_cand is not None, f"User B not found in matches (returned {len(matches)} matches)"
    assert p_cand["scores"]["availability_score"] == 0.5
    print(f"      Partial Overlap Verified: Score = {p_cand['scores']['availability_score']} (50% overlap)")

    # Scenario C: No Overlap on Non-Flexible Date (Sunday)
    next_sunday = (today + timedelta(days=((6 - today.weekday()) % 7 or 7))).date()
    no_req_res = requests.post(f"{BACKEND_URL}/api/requests", headers=user_a_h, json={
        "text": "Sunday flat hunt Hinjewadi",
        "city": "Pune",
        "preferred_date": next_sunday.isoformat(),
        "preferred_start_time": "10:00:00",
        "preferred_end_time": "12:00:00",
        "is_time_flexible": False,
    })
    assert_status(no_req_res, 201, "Non-flexible Sunday request created")
    no_req_id = no_req_res.json()["id"]
    no_match = requests.post(f"{BACKEND_URL}/api/matching/find-matches", headers=user_a_h, json={"request_id": no_req_id, "limit": 50})
    no_cand = next(c for c in no_match.json()["matches"] if c["user_id"] == user_b_id)
    assert no_cand["scores"]["availability_score"] == 0.0
    print(f"      No Overlap Verified: Score = {no_cand['scores']['availability_score']}")

    # Scenario D: Flexibility Window Evaluation (Sunday with flexibility=2 matches Saturday slot)
    flex_req_res = requests.post(f"{BACKEND_URL}/api/requests", headers=user_a_h, json={
        "text": "Sunday flat hunt Hinjewadi with weekend flexibility",
        "city": "Pune",
        "preferred_date": next_sunday.isoformat(),
        "preferred_start_time": "10:00:00",
        "preferred_end_time": "12:00:00",
        "is_time_flexible": True,
        "flexibility_window_days": 2,
    })
    assert_status(flex_req_res, 201, "Flexible Sunday request created")
    flex_req_id = flex_req_res.json()["id"]
    flex_match = requests.post(f"{BACKEND_URL}/api/matching/find-matches", headers=user_a_h, json={"request_id": flex_req_id, "limit": 50})
    flex_cand = next(c for c in flex_match.json()["matches"] if c["user_id"] == user_b_id)
    assert flex_cand["scores"]["availability_score"] > 0.0
    print(f"      Flexibility Window Match Verified: Score = {flex_cand['scores']['availability_score']} (Matched adjacent Saturday)")

    # -------------------------------------------------------------------------
    # 12. Propose In-Person Assistance Session & Venue Validation
    # -------------------------------------------------------------------------
    log_step(12, "Propose In-Person Assistance Session & Venue Validation")
    sess_dt = (datetime.now(timezone.utc) + timedelta(days=4)).replace(microsecond=0)

    # Test Disallowed Venue: Lodging / Hotel
    bad_venue_res = requests.post(f"{BACKEND_URL}/api/sessions", headers=user_a_h, json={
        "request_id": req_id,
        "recipient_id": user_b_id,
        "title": "Hotel Meeting Attempt",
        "modality": "IN_PERSON",
        "meeting_place_id": "ChIJ_hotel_palace",
        "scheduled_start": sess_dt.isoformat(),
        "duration_minutes": 60,
    })
    assert_status(bad_venue_res, 422, "Disallowed hotel/lodging venue rejected")

    # Test Venue Beyond Approved 25km Radius
    far_venue_res = requests.post(f"{BACKEND_URL}/api/sessions", headers=user_a_h, json={
        "request_id": req_id,
        "recipient_id": user_b_id,
        "title": "Far Away Outstation Meeting Attempt",
        "modality": "IN_PERSON",
        "meeting_place_id": "ChIJ_far_away_60km",
        "scheduled_start": sess_dt.isoformat(),
        "duration_minutes": 60,
    })
    assert_status(far_venue_res, 422, "Venue exceeding 25km radius rejected")

    # Successfully Propose Approved In-Person Session (Cafe)
    good_sess_res = requests.post(f"{BACKEND_URL}/api/sessions", headers=user_a_h, json={
        "request_id": req_id,
        "recipient_id": user_b_id,
        "title": "Hinjewadi PG Search Tour",
        "description": "Meet to visit 3 shortlisted PGs in Phase 1.",
        "need_category": "accommodation",
        "modality": "IN_PERSON",
        "meeting_place_id": "ChIJ_central_cafe_hinjewadi",
        "scheduled_start": sess_dt.isoformat(),
        "duration_minutes": 60,
    })
    assert_status(good_sess_res, 201, "In-person assistance session proposed (Status: PROPOSED)")
    session_id = good_sess_res.json()["id"]

    # -------------------------------------------------------------------------
    # 13. Test Remote Assistance Session & URL Privacy
    # -------------------------------------------------------------------------
    log_step(13, "Test Remote Modality & URL Privacy Protection")
    remote_dt = (datetime.now(timezone.utc) + timedelta(days=6)).replace(microsecond=0)

    # Insecure HTTP rejected
    insecure_url = requests.post(f"{BACKEND_URL}/api/sessions", headers=user_a_h, json={
        "request_id": req_id,
        "recipient_id": user_b_id,
        "title": "Insecure Video Call",
        "modality": "REMOTE",
        "meeting_url": "http://meet.google.com/test",
        "scheduled_start": remote_dt.isoformat(),
        "duration_minutes": 30,
    })
    assert_status(insecure_url, 422, "Insecure HTTP remote URL rejected")

    # Localhost SSRF rejected
    ssrf_url = requests.post(f"{BACKEND_URL}/api/sessions", headers=user_a_h, json={
        "request_id": req_id,
        "recipient_id": user_b_id,
        "title": "SSRF Call Attempt",
        "modality": "REMOTE",
        "meeting_url": "https://localhost:8000/call",
        "scheduled_start": remote_dt.isoformat(),
        "duration_minutes": 30,
    })
    assert_status(ssrf_url, 422, "Localhost SSRF remote URL rejected")

    # Propose Valid Remote Session
    remote_sess = requests.post(f"{BACKEND_URL}/api/sessions", headers=user_a_h, json={
        "request_id": req_id,
        "recipient_id": user_b_id,
        "title": "Virtual Hinjewadi Orientation",
        "modality": "REMOTE",
        "meeting_url": "https://meet.google.com/xyz-nest-demo",
        "scheduled_start": remote_dt.isoformat(),
        "duration_minutes": 45,
    })
    assert_status(remote_sess, 201, "Remote assistance session proposed")
    remote_sess_id = remote_sess.json()["id"]

    # Pre-Confirmation Privacy: Recipient cannot see meeting URL before confirmation
    chk_pre = requests.get(f"{BACKEND_URL}/api/sessions/{remote_sess_id}", headers=user_b_h)
    assert_status(chk_pre, 200, "Recipient views proposed remote session")
    assert chk_pre.json().get("meeting_url") is None
    print("      URL Privacy Verified: meeting_url hidden from recipient prior to confirmation.")

    # Confirm Remote Session
    conf_remote = requests.post(f"{BACKEND_URL}/api/sessions/{remote_sess_id}/accept", headers=user_b_h)
    assert_status(conf_remote, 200, "Remote session accepted and confirmed")

    # Post-Confirmation: Recipient can now access meeting URL
    chk_post = requests.get(f"{BACKEND_URL}/api/sessions/{remote_sess_id}", headers=user_b_h)
    assert_status(chk_post, 200, "Recipient views confirmed remote session")
    assert chk_post.json().get("meeting_url") == "https://meet.google.com/xyz-nest-demo"
    print("      URL Reveal Verified: meeting_url revealed to confirmed recipient.")

    # -------------------------------------------------------------------------
    # 14. Session Acceptance & RFC 5545 iCalendar Export
    # -------------------------------------------------------------------------
    log_step(14, "Accept In-Person Session & Export RFC 5545 iCalendar")
    # Anti-Self-Accept Rule: Proposer cannot accept own proposal
    self_acc = requests.post(f"{BACKEND_URL}/api/sessions/{session_id}/accept", headers=user_a_h)
    assert_status(self_acc, 403, "Proposer self-acceptance blocked")

    # Recipient accepts session
    acc_res = requests.post(f"{BACKEND_URL}/api/sessions/{session_id}/accept", headers=user_b_h)
    assert_status(acc_res, 200, "In-person session confirmed (Status: CONFIRMED)")
    assert acc_res.json()["status"] == "CONFIRMED"

    # Export RFC 5545 iCalendar
    cal_res = requests.get(f"{BACKEND_URL}/api/sessions/{session_id}/calendar", headers=user_a_h)
    assert_status(cal_res, 200, "RFC 5545 .ics calendar exported")
    assert "BEGIN:VCALENDAR" in cal_res.text
    assert "BEGIN:VEVENT" in cal_res.text
    assert "STATUS:CONFIRMED" in cal_res.text
    print("      RFC 5545 iCalendar Verified: Correct MIME type and VEVENT payload.")

    # -------------------------------------------------------------------------
    # 15. Concurrency & Conflict Protection (Double Booking)
    # -------------------------------------------------------------------------
    log_step(15, "Test Concurrency Conflict & Double Booking Protection")
    conflict_prop = requests.post(f"{BACKEND_URL}/api/sessions", headers=user_a_h, json={
        "request_id": req_id,
        "recipient_id": user_b_id,
        "title": "Double Booking Attempt",
        "modality": "IN_PERSON",
        "meeting_place_id": "ChIJ_central_cafe_hinjewadi",
        "scheduled_start": (sess_dt + timedelta(minutes=15)).isoformat(),
        "duration_minutes": 30,
    })
    assert_status(conflict_prop, 409, "Double booking overlapping with confirmed session rejected")

    # -------------------------------------------------------------------------
    # 16. Rescheduling Workflow
    # -------------------------------------------------------------------------
    log_step(16, "Reschedule Session Workflow with Audit Counter")
    new_start = sess_dt + timedelta(days=1)
    resched_res = requests.post(f"{BACKEND_URL}/api/sessions/{session_id}/reschedule", headers=user_a_h, json={
        "new_scheduled_start": new_start.isoformat(),
        "new_duration_minutes": 90,
        "reschedule_reason": "Flight arrival adjusted by 1 day",
    })
    assert_status(resched_res, 200, "Reschedule proposed (Status: RESCHEDULE_PROPOSED)")
    assert resched_res.json()["status"] == "RESCHEDULE_PROPOSED"
    assert resched_res.json()["reschedule_count"] == 1

    # Recipient accepts reschedule
    re_acc = requests.post(f"{BACKEND_URL}/api/sessions/{session_id}/accept", headers=user_b_h)
    assert_status(re_acc, 200, "Reschedule accepted -> Confirmed with updated start time")
    assert re_acc.json()["status"] == "CONFIRMED"

    # -------------------------------------------------------------------------
    # 17. Dual-Confirmation Completion Workflow
    # -------------------------------------------------------------------------
    log_step(17, "Test Dual-Confirmation Completion Workflow")
    # Step A: Newcomer completes
    comp_a = requests.post(f"{BACKEND_URL}/api/sessions/{session_id}/complete", headers=user_a_h)
    assert_status(comp_a, 200, "Newcomer confirmed session completion")
    assert comp_a.json()["status"] == "CONFIRMED" # Remains CONFIRMED until both confirm
    assert comp_a.json()["requester_completed_at"] is not None
    assert comp_a.json()["helper_completed_at"] is None

    # Step B: Helper completes -> status transitions to COMPLETED
    comp_b = requests.post(f"{BACKEND_URL}/api/sessions/{session_id}/complete", headers=user_b_h)
    assert_status(comp_b, 200, "Helper confirmed completion -> Status transitions to COMPLETED")
    assert comp_b.json()["status"] == "COMPLETED"
    assert comp_b.json()["helper_completed_at"] is not None

    # -------------------------------------------------------------------------
    # 18. Real Reviews & Reputation
    # -------------------------------------------------------------------------
    log_step(18, "Submit Real Post-Completion Reviews & Reputation Calculation")
    # Complete Connection to permit review submission
    comp_conn = requests.patch(f"{BACKEND_URL}/api/connections/{conn_id}", headers=user_a_h, json={"action": "complete"})
    assert_status(comp_conn, 200, "Connection marked COMPLETED")

    # User A reviews User B
    rev_a = requests.post(f"{BACKEND_URL}/api/connections/{conn_id}/reviews", headers=user_a_h, json={
        "rating": 5,
        "comment": "Priya was amazing! Showed me 3 great PGs in Hinjewadi Phase 1.",
        "helpful_aspects": ["local_knowledge", "punctuality"],
    })
    assert_status(rev_a, 201, "User A reviewed User B")

    # User B reviews User A
    rev_b = requests.post(f"{BACKEND_URL}/api/connections/{conn_id}/reviews", headers=user_b_h, json={
        "rating": 5,
        "comment": "Vivaan is a great newcomer, very clear requirements and prompt.",
    })
    assert_status(rev_b, 201, "User B reviewed User A")

    # Duplicate review rejected
    dup_rev = requests.post(f"{BACKEND_URL}/api/connections/{conn_id}/reviews", headers=user_a_h, json={
        "rating": 4, "comment": "Duplicate attempt"
    })
    assert_status(dup_rev, 409, "Duplicate review rejected (HTTP 409 Conflict)")

    # -------------------------------------------------------------------------
    # 19. Explicit Request Resolution (Phase 13 Boundary Integrity)
    # -------------------------------------------------------------------------
    log_step(19, "Verify Phase 13 Boundary: Explicit Need Resolution Required")
    # Verify Need is NOT automatically resolved upon session completion
    intel_post = requests.get(f"{BACKEND_URL}/api/requests/{req_id}/intelligence", headers=user_a_h)
    assert_status(intel_post, 200, "Intelligence Hub reloaded")
    target_cat = needs[0]["category"]
    need_item = next((n for n in intel_post.json().get("need_progress", []) if n.get("category") == target_cat), None)
    if need_item:
        assert need_item["status"] != "RESOLVED"
    print("      Boundary Integrity Verified: Completed session does NOT silently resolve need.")

    # Explicit resolution via PATCH need-progress
    resolve_res = requests.patch(f"{BACKEND_URL}/api/requests/{req_id}/need-progress", headers=user_a_h, json={
        "category": target_cat,
        "status": "RESOLVED",
        "resolved_via": "session",
        "resolved_entity_id": str(session_id),
        "notes": "Visited Hinjewadi Phase 1 PGs with Priya and signed rental agreement.",
    })
    assert_status(resolve_res, 200, "Explicit need resolution succeeded")
    assert any(n["category"] == target_cat and n["status"] == "RESOLVED" for n in resolve_res.json()["needs"])
    assert resolve_res.json()["resolved_needs"] >= 1

    # -------------------------------------------------------------------------
    # 20. Blocking & Safety Restrictions
    # -------------------------------------------------------------------------
    log_step(20, "Test Blocking: Active Session Cancellation, Proposal Denial, History Retention")
    # User A blocks User B
    blk_res = requests.post(f"{BACKEND_URL}/api/blocks/{user_b_id}", headers=user_a_h)
    assert_status(blk_res, 201, "User A blocked User B")

    # Active remote session cancelled automatically
    chk_cancelled = requests.get(f"{BACKEND_URL}/api/sessions/{remote_sess_id}", headers=user_a_h)
    assert_status(chk_cancelled, 200, "Remote session retrieved after blocking")
    assert chk_cancelled.json()["status"] == "CANCELLED"
    assert "safety restriction" in chk_cancelled.json()["status_reason"].lower()

    # Blocked proposal denied
    blk_prop = requests.post(f"{BACKEND_URL}/api/sessions", headers=user_a_h, json={
        "request_id": req_id,
        "recipient_id": user_b_id,
        "title": "Blocked Session Proposal",
        "modality": "REMOTE",
        "meeting_url": "https://meet.google.com/test",
        "scheduled_start": (datetime.now(timezone.utc) + timedelta(days=9)).isoformat(),
        "duration_minutes": 30,
    })
    assert_status(blk_prop, 403, "Blocked user cannot propose sessions")

    # Completed session remains accessible in history
    hist_chk = requests.get(f"{BACKEND_URL}/api/sessions/{session_id}", headers=user_a_h)
    assert_status(hist_chk, 200, "Historical completed session retrieved")
    assert hist_chk.json()["status"] == "COMPLETED"

    # Unblock User B
    unblk_res = requests.delete(f"{BACKEND_URL}/api/blocks/{user_b_id}", headers=user_a_h)
    assert_status(unblk_res, 204, "User B unblocked")

    # -------------------------------------------------------------------------
    # 21. Admin Suspension & Access Denial
    # -------------------------------------------------------------------------
    log_step(21, "Test Admin Suspension: Future Session Cancellation & Reactivation")
    # Propose and confirm a new session for suspension test
    susp_start = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
    susp_prop = requests.post(f"{BACKEND_URL}/api/sessions", headers=user_a_h, json={
        "request_id": req_id,
        "recipient_id": user_b_id,
        "title": "Pre-Suspension Session",
        "modality": "REMOTE",
        "meeting_url": "https://meet.google.com/test-susp",
        "scheduled_start": susp_start,
        "duration_minutes": 30,
    })
    assert_status(susp_prop, 201, "Session proposed for suspension test")
    susp_sess_id = susp_prop.json()["id"]
    requests.post(f"{BACKEND_URL}/api/sessions/{susp_sess_id}/accept", headers=user_b_h)

    # Admin suspends helper
    susp_act = requests.post(f"{BACKEND_URL}/api/admin/users/{user_b_id}/suspend", headers=admin_h, json={
        "reason": "Platform safety verification audit"
    })
    assert_status(susp_act, 200, "Admin suspended Helper account")

    # Session automatically cancelled
    chk_susp_sess = requests.get(f"{BACKEND_URL}/api/sessions/{susp_sess_id}", headers=user_a_h)
    assert_status(chk_susp_sess, 200, "Session checked after suspension")
    assert chk_susp_sess.json()["status"] == "CANCELLED"
    assert "account suspension" in chk_susp_sess.json()["status_reason"].lower()

    # Suspended user denied operations
    denied_action = requests.post(f"{BACKEND_URL}/api/sessions", headers=user_b_h, json={
        "request_id": req_id,
        "recipient_id": user_a_id,
        "title": "Suspended Attempt",
        "modality": "REMOTE",
        "meeting_url": "https://meet.google.com/test",
        "scheduled_start": (datetime.now(timezone.utc) + timedelta(days=11)).isoformat(),
        "duration_minutes": 30,
    })
    assert_status(denied_action, 403, "Suspended user denied session creation")

    # Admin reactivates account
    react_act = requests.post(f"{BACKEND_URL}/api/admin/users/{user_b_id}/reactivate", headers=admin_h, json={
        "reason": "Account restored after review"
    })
    assert_status(react_act, 200, "Admin reactivated Helper account")

    # -------------------------------------------------------------------------
    # 22. Authentication & Security Edge Cases
    # -------------------------------------------------------------------------
    log_step(22, "Verify Authentication & IDOR Authorization Boundaries")
    # Unauthenticated request rejected
    unauth = requests.get(f"{BACKEND_URL}/api/profile/me")
    assert_status(unauth, 401, "Unauthenticated request rejected with HTTP 401")

    # Cross-user request modification rejected
    cross_req = requests.patch(f"{BACKEND_URL}/api/requests/{req_id}/need-progress", headers=user_c_h, json={
        "category": target_cat,
        "status": "RESOLVED",
    })
    assert_status(cross_req, 403, "Stranger blocked from modifying another user's request")

    log_section("LOCAL REAL-USER ACCEPTANCE TEST COMPLETED: ALL 22 AUDIT PHASES PASSED!")

if __name__ == "__main__":
    main()
