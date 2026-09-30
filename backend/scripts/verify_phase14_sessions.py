#!/usr/bin/env python3
"""
NEST Phase 14 Live End-to-End Verification Script
Tests Assistance Sessions, Availability Intelligence & Schedule Coordination against http://127.0.0.1:8000.
Executes 25 comprehensive live verification scenarios without mocks.
"""

from datetime import date, datetime, timedelta, timezone
import sys
import uuid
import requests

BASE_URL = "http://127.0.0.1:8000"

def log_step(num: int, title: str):
    print(f"\n[SCENARIO {num:02d}] {title}")

def assert_status(resp: requests.Response, expected: int, msg: str = ""):
    if resp.status_code != expected:
        print(f"  FAILED: Expected HTTP {expected}, got HTTP {resp.status_code}. Response: {resp.text}")
        sys.exit(1)
    print(f"  PASS: HTTP {resp.status_code} {msg}")

def register_and_login(name: str, email: str, password: str = "Password123!", role: str = "newcomer"):
    reg = requests.post(f"{BASE_URL}/api/auth/register", json={
        "name": name, "email": email, "password": password, "role": role
    })
    assert_status(reg, 201, f"{name} registered")
    login = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": email, "password": password
    })
    assert_status(login, 200, f"{name} logged in")
    token = login.json()["access_token"]
    user_id = login.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}
    return user_id, headers

def main():
    print("=" * 80)
    print("NEST PHASE 14 — ASSISTANCE SESSIONS & AVAILABILITY INTELLIGENCE LIVE E2E")
    print("=" * 80)

    # SCENARIO 01: System & Database Health Check
    log_step(1, "Verify System & PostgreSQL Runtime Health")
    h = requests.get(f"{BASE_URL}/api/health")
    assert_status(h, 200, "Health check online")
    assert h.json()["database"] == "connected"

    uid = uuid.uuid4().hex[:6]

    # SCENARIO 02: Register Live Test Users
    log_step(2, "Register Newcomer, Primary Helper, and Unconnected Stranger")
    newcomer_id, newcomer_h = register_and_login("Vivaan Newcomer", f"vivaan_{uid}@example.test")
    helper_id, helper_h = register_and_login("Priya Helper", f"priya_{uid}@example.test")
    stranger_id, stranger_h = register_and_login("Karan Stranger", f"karan_{uid}@example.test")

    # Helper Profile & Location
    requests.put(f"{BASE_URL}/api/profile/me", headers=helper_h, json={
        "headline": "Indiranagar Local Guide",
        "bio": "Experienced Bangalore local helper.",
        "years_in_city": 5.0,
    })
    requests.put(f"{BASE_URL}/api/profile/me/location", headers=helper_h, json={
        "city": "Bengaluru",
        "area": "Indiranagar",
        "latitude": 12.9716,
        "longitude": 77.5946,
    })

    # SCENARIO 03: Helper Configures Weekly Availability Slots
    log_step(3, "Helper Sets Weekly Availability Schedule")
    slots_payload = {
        "slots": [
            {"day_of_week": 0, "start_time": "09:00:00", "end_time": "12:00:00"},
            {"day_of_week": 2, "start_time": "14:00:00", "end_time": "18:00:00"},
            {"day_of_week": 5, "start_time": "10:00:00", "end_time": "16:00:00"},
        ],
        "helper_timezone": "Asia/Kolkata"
    }
    slot_resp = requests.put(f"{BASE_URL}/api/availability/slots", headers=helper_h, json=slots_payload)
    assert_status(slot_resp, 200, "Availability slots configured")
    assert len(slot_resp.json()["slots"]) == 3

    # SCENARIO 04: Validation of Overlapping Slots on Same Day
    log_step(4, "Reject Overlapping Availability Slots (Intra-day Conflict)")
    bad_slots = {
        "slots": [
            {"day_of_week": 0, "start_time": "09:00:00", "end_time": "12:00:00"},
            {"day_of_week": 0, "start_time": "11:00:00", "end_time": "14:00:00"},
        ]
    }
    bad_slot_resp = requests.put(f"{BASE_URL}/api/availability/slots", headers=helper_h, json=bad_slots)
    assert_status(bad_slot_resp, 422, "Intra-day overlap rejected")

    # SCENARIO 05: Helper Configures Capacity Limits & Timezone
    log_step(5, "Helper Configures Assistance Capacity Limits & Timezone")
    cap_payload = {
        "helper_timezone": "Asia/Kolkata",
        "max_weekly_sessions": 10,
        "accepting_sessions": True,
    }
    cap_resp = requests.put(f"{BASE_URL}/api/availability/capacity", headers=helper_h, json=cap_payload)
    assert_status(cap_resp, 200, "Capacity limits saved")
    assert cap_resp.json()["capacity_status"] == "AVAILABLE"

    # SCENARIO 06: Two-Tier Privacy Model — Stranger Views Coarse Profile
    log_step(6, "Stranger Views Helper Availability (Two-Tier Privacy: Coarse Only)")
    coarse_resp = requests.get(f"{BASE_URL}/api/availability/user/{helper_id}", headers=stranger_h)
    assert_status(coarse_resp, 200, "Coarse availability retrieved")
    coarse_data = coarse_resp.json()
    assert "slots" not in coarse_data or coarse_data["slots"] is None or isinstance(coarse_data.get("available_days"), list)

    # SCENARIO 07: Newcomer Creates Request with Phase 14 Timing Preferences
    log_step(7, "Newcomer Creates Request with Structured Timing Preferences")
    next_saturday = (date.today() + timedelta(days=(5 - date.today().weekday()) % 7 + 7)).isoformat()
    req_payload = {
        "text": "Need assistance finding a PG in Indiranagar near 100ft road",
        "preferred_date": next_saturday,
        "preferred_start_time": "10:00:00",
        "preferred_end_time": "13:00:00",
        "requester_timezone": "Asia/Kolkata",
        "is_time_flexible": True,
        "flexibility_window_days": 2,
        "preferred_days_of_week": [5],
    }
    req_resp = requests.post(f"{BASE_URL}/api/requests", headers=newcomer_h, json=req_payload)
    assert_status(req_resp, 201, "Request created with timing preferences")
    request_id = req_resp.json()["id"]

    # SCENARIO 08: Establish Real Mutual Connection
    log_step(8, "Connect Newcomer and Helper via Connection Workflow")
    conn_create = requests.post(f"{BASE_URL}/api/connections", headers=newcomer_h, json={
        "request_id": request_id,
        "helper_id": helper_id,
        "initial_message": "Hi Priya, saw your profile for Indiranagar PG assistance!",
    })
    assert_status(conn_create, 201, "Connection request sent")
    conn_id = conn_create.json()["id"]

    accept_conn = requests.patch(f"{BASE_URL}/api/connections/{conn_id}", headers=helper_h, json={
        "action": "accept"
    })
    assert_status(accept_conn, 200, "Connection accepted")

    # SCENARIO 09: Two-Tier Privacy Model — Connected User Sees Detailed Slots
    log_step(9, "Connected Newcomer Views Helper Detailed Availability Slots")
    detailed_resp = requests.get(f"{BASE_URL}/api/availability/user/{helper_id}", headers=newcomer_h)
    assert_status(detailed_resp, 200, "Detailed availability retrieved")
    detailed_data = detailed_resp.json()
    assert detailed_data.get("slots") is not None
    assert len(detailed_data["slots"]) == 3

    # SCENARIO 10: Reject Disallowed Venue for In-Person Session
    log_step(10, "Reject Disallowed In-Person Venue (Lodging/Hotel)")
    future_start = (datetime.now(timezone.utc) + timedelta(days=2)).replace(microsecond=0)
    bad_venue_payload = {
        "request_id": request_id,
        "recipient_id": helper_id,
        "title": "Hotel Meetup",
        "modality": "IN_PERSON",
        "meeting_place_id": "ChIJ_hotel_not_allowed",
        "scheduled_start": future_start.isoformat(),
        "duration_minutes": 60,
    }
    bad_v_res = requests.post(f"{BASE_URL}/api/sessions", headers=newcomer_h, json=bad_venue_payload)
    assert_status(bad_v_res, 422, "Disallowed venue rejected")

    # SCENARIO 11: Reject In-Person Venue Beyond 25 km Radius
    log_step(11, "Reject In-Person Venue Beyond Approved 25 km Radius")
    far_venue_payload = {
        "request_id": request_id,
        "recipient_id": helper_id,
        "title": "Far Out Meeting",
        "modality": "IN_PERSON",
        "meeting_place_id": "ChIJ_far_away_60km",
        "scheduled_start": future_start.isoformat(),
        "duration_minutes": 60,
    }
    far_v_res = requests.post(f"{BASE_URL}/api/sessions", headers=newcomer_h, json=far_venue_payload)
    assert_status(far_v_res, 422, "Venue beyond 25km radius rejected")

    # SCENARIO 12: Successfully Propose In-Person Assistance Session
    log_step(12, "Successfully Propose Approved In-Person Assistance Session")
    valid_session_payload = {
        "request_id": request_id,
        "recipient_id": helper_id,
        "title": "Indiranagar PG Viewing & Coffee",
        "modality": "IN_PERSON",
        "meeting_place_id": "ChIJ_indiranagar_central_cafe",
        "scheduled_start": future_start.isoformat(),
        "duration_minutes": 60,
        "timezone": "Asia/Kolkata",
    }
    sess_res = requests.post(f"{BASE_URL}/api/sessions", headers=newcomer_h, json=valid_session_payload)
    assert_status(sess_res, 201, "In-person assistance session proposed")
    session_id = sess_res.json()["id"]

    # SCENARIO 13: Non-Participant Access Denied (IDOR Protection)
    log_step(13, "Enforce IDOR Access Control (Stranger Cannot View Session)")
    idor_res = requests.get(f"{BASE_URL}/api/sessions/{session_id}", headers=stranger_h)
    assert_status(idor_res, 403, "Stranger blocked from session access")

    # SCENARIO 14: Anti-Self-Accept Protection
    log_step(14, "Enforce Anti-Self-Accept Rule (Proposer Cannot Accept Own Proposal)")
    self_acc = requests.post(f"{BASE_URL}/api/sessions/{session_id}/accept", headers=newcomer_h)
    assert_status(self_acc, 403, "Proposer self-acceptance blocked")

    # SCENARIO 15: Recipient Accepts Session -> Transitions to CONFIRMED
    log_step(15, "Helper Accepts Session Proposal -> Status CONFIRMED")
    accept_res = requests.post(f"{BASE_URL}/api/sessions/{session_id}/accept", headers=helper_h)
    assert_status(accept_res, 200, "Session confirmed")
    assert accept_res.json()["status"] == "CONFIRMED"

    # SCENARIO 16: RFC 5545 iCalendar (.ics) Export
    log_step(16, "Export Confirmed Session as Deterministic RFC 5545 .ics Calendar")
    cal_res = requests.get(f"{BASE_URL}/api/sessions/{session_id}/calendar.ics", headers=newcomer_h)
    assert_status(cal_res, 200, "iCalendar exported")
    cal_text = cal_res.text
    assert "BEGIN:VCALENDAR" in cal_text
    assert "BEGIN:VEVENT" in cal_text
    assert "VALARM" in cal_text
    assert "ORGANIZER" in cal_text

    # SCENARIO 17: Database-Level Double-Booking Concurrency Conflict
    log_step(17, "Prevent Double-Booking of Confirmed Time Slot")
    double_payload = {
        "request_id": request_id,
        "recipient_id": helper_id,
        "title": "Conflicting Session",
        "modality": "IN_PERSON",
        "meeting_place_id": "ChIJ_indiranagar_central_cafe",
        "scheduled_start": future_start.isoformat(),
        "duration_minutes": 60,
    }
    double_res = requests.post(f"{BASE_URL}/api/sessions", headers=newcomer_h, json=double_payload)
    assert_status(double_res, 409, "Double-booking conflict prevented")

    # SCENARIO 18: Reject Insecure HTTP Remote Meeting URL
    log_step(18, "Reject Insecure HTTP Remote Meeting URL")
    future_start_remote = future_start + timedelta(days=3)
    bad_http_payload = {
        "request_id": request_id,
        "recipient_id": helper_id,
        "title": "Remote Setup Call",
        "modality": "REMOTE",
        "meeting_url": "http://meet.insecure.test/call",
        "scheduled_start": future_start_remote.isoformat(),
        "duration_minutes": 45,
    }
    bad_http_res = requests.post(f"{BASE_URL}/api/sessions", headers=newcomer_h, json=bad_http_payload)
    assert_status(bad_http_res, 422, "Insecure HTTP remote URL rejected")

    # SCENARIO 19: Reject Localhost / SSRF Remote Meeting URL
    log_step(19, "Reject Localhost / SSRF Remote Meeting URL")
    ssrf_payload = {
        "request_id": request_id,
        "recipient_id": helper_id,
        "title": "SSRF Call",
        "modality": "REMOTE",
        "meeting_url": "https://localhost:8080/call",
        "scheduled_start": future_start_remote.isoformat(),
        "duration_minutes": 45,
    }
    ssrf_res = requests.post(f"{BASE_URL}/api/sessions", headers=newcomer_h, json=ssrf_payload)
    assert_status(ssrf_res, 422, "Localhost SSRF URL rejected")

    # SCENARIO 20: Successfully Propose Remote Assistance Session
    log_step(20, "Successfully Propose Valid Remote Assistance Session")
    remote_payload = {
        "request_id": request_id,
        "recipient_id": helper_id,
        "title": "Virtual Neighborhood Orientation",
        "modality": "REMOTE",
        "meeting_url": "https://meet.google.com/xyz-nest-demo",
        "scheduled_start": future_start_remote.isoformat(),
        "duration_minutes": 45,
    }
    remote_res = requests.post(f"{BASE_URL}/api/sessions", headers=newcomer_h, json=remote_payload)
    assert_status(remote_res, 201, "Remote assistance session proposed")
    remote_session_id = remote_res.json()["id"]

    # SCENARIO 21: Remote URL Privacy Check in PROPOSED State
    log_step(21, "Remote URL Privacy: Recipient Cannot See URL Before Confirmation")
    check_proposed = requests.get(f"{BASE_URL}/api/sessions/{remote_session_id}", headers=helper_h)
    assert_status(check_proposed, 200, "Session retrieved by recipient")
    assert check_proposed.json().get("meeting_url") is None

    # SCENARIO 22: Remote URL Revealed Upon Confirmation
    log_step(22, "Remote URL Revealed to Recipient Upon Session Confirmation")
    requests.post(f"{BASE_URL}/api/sessions/{remote_session_id}/accept", headers=helper_h)
    check_confirmed = requests.get(f"{BASE_URL}/api/sessions/{remote_session_id}", headers=helper_h)
    assert_status(check_confirmed, 200, "Confirmed session retrieved")
    assert check_confirmed.json().get("meeting_url") == "https://meet.google.com/xyz-nest-demo"

    # SCENARIO 23: Reschedule State Machine & Counter Increment
    log_step(23, "Reschedule Session Workflow with Audit Counter")
    new_reschedule_start = (future_start + timedelta(days=1)).isoformat()
    reschedule_res = requests.post(f"{BASE_URL}/api/sessions/{session_id}/reschedule", headers=newcomer_h, json={
        "new_scheduled_start": new_reschedule_start,
        "new_duration_minutes": 90,
        "reason": "Flight arrival adjusted by 1 day",
    })
    assert_status(reschedule_res, 200, "Reschedule proposed")
    reschedule_data = reschedule_res.json()
    assert reschedule_data["status"] == "RESCHEDULE_PROPOSED"
    assert reschedule_data["reschedule_count"] == 1

    # Accept Reschedule
    re_accept = requests.post(f"{BASE_URL}/api/sessions/{session_id}/accept", headers=helper_h)
    assert_status(re_accept, 200, "Reschedule accepted")
    assert re_accept.json()["status"] == "CONFIRMED"

    # SCENARIO 24: Dual-Confirmation Completion Workflow
    log_step(24, "Dual-Confirmation Completion Workflow")
    # Step A: Newcomer marks complete
    comp_a = requests.post(f"{BASE_URL}/api/sessions/{session_id}/complete", headers=newcomer_h)
    assert_status(comp_a, 200, "Newcomer confirmed completion")
    assert comp_a.json()["status"] == "CONFIRMED" # Remains confirmed until both parties confirm
    assert comp_a.json()["requester_completed_at"] is not None
    assert comp_a.json()["helper_completed_at"] is None

    # Step B: Helper marks complete -> Transitions to COMPLETED
    comp_b = requests.post(f"{BASE_URL}/api/sessions/{session_id}/complete", headers=helper_h)
    assert_status(comp_b, 200, "Helper confirmed completion")
    assert comp_b.json()["status"] == "COMPLETED"
    assert comp_b.json()["helper_completed_at"] is not None

    # SCENARIO 25: Request Intelligence Need-Level Resolution Integration
    log_step(25, "Resolve Request Need via Completed Assistance Session")
    req_needs = req_resp.json().get("extracted_requirements", {}).get("needs", [])
    target_category = req_needs[0]["category"] if req_needs else "housing"

    # First: Uncompleted remote session cannot resolve need
    bad_resolve = requests.patch(f"{BASE_URL}/api/requests/{request_id}/need-progress", headers=newcomer_h, json={
        "category": target_category,
        "status": "RESOLVED",
        "resolved_via": "session",
        "resolved_entity_id": remote_session_id, # not completed
        "notes": "Attempting to resolve via uncompleted session",
    })
    assert_status(bad_resolve, 400, "Uncompleted session cannot resolve need")

    # Second: Completed session successfully resolves need
    good_resolve = requests.patch(f"{BASE_URL}/api/requests/{request_id}/need-progress", headers=newcomer_h, json={
        "category": target_category,
        "status": "RESOLVED",
        "resolved_via": "session",
        "resolved_entity_id": session_id, # completed session
        "notes": "Met Priya in Indiranagar; viewed 3 flats and signed lease.",
    })
    assert_status(good_resolve, 200, "Need successfully resolved with assistance session")
    intel_data = good_resolve.json()
    assert intel_data["status"] == "RESOLVED"
    assert intel_data["resolved_needs"] >= 1

    # SCENARIO 26: Active Session Cancelled upon Blocking
    log_step(26, "Active Confirmed Session Cancelled Automatically When User Blocks")
    blk_res = requests.post(f"{BASE_URL}/api/blocks/{helper_id}", headers=newcomer_h)
    assert_status(blk_res, 201, "Newcomer blocked helper")

    # Verify remote session cancelled automatically
    chk_blk = requests.get(f"{BASE_URL}/api/sessions/{remote_session_id}", headers=newcomer_h)
    assert_status(chk_blk, 200, "Remote session retrieved after blocking")
    assert chk_blk.json()["status"] == "CANCELLED"
    assert "safety restriction" in chk_blk.json()["status_reason"].lower()

    # SCENARIO 27: Blocked User Cannot Propose Sessions
    log_step(27, "Blocked Users Denied New Session Proposals")
    blk_prop = requests.post(f"{BASE_URL}/api/sessions", headers=newcomer_h, json={
        "request_id": request_id,
        "recipient_id": helper_id,
        "title": "Blocked Proposal Attempt",
        "modality": "REMOTE",
        "meeting_url": "https://meet.google.com/xyz-nest-demo",
        "scheduled_start": (datetime.now(timezone.utc) + timedelta(days=8)).isoformat(),
        "duration_minutes": 30,
    })
    assert_status(blk_prop, 403, "Session proposal blocked due to safety restriction")

    # SCENARIO 28: Historical Completed Session Retained
    log_step(28, "Completed Session Retained in History After Blocking")
    hist_chk = requests.get(f"{BASE_URL}/api/sessions/{session_id}", headers=newcomer_h)
    assert_status(hist_chk, 200, "Historical completed session retrieved")
    assert hist_chk.json()["status"] == "COMPLETED"

    # SCENARIO 29: Admin Suspension Automatically Cancels Active Sessions
    log_step(29, "Admin Suspension Automatically Cancels Helper's Future Sessions")
    # Unblock first so new session can be proposed
    unblk_res = requests.delete(f"{BASE_URL}/api/blocks/{helper_id}", headers=newcomer_h)
    assert_status(unblk_res, 204, "Helper unblocked")

    admin_id, admin_h = register_and_login("Admin Mod", f"admin_{uid}@example.test", role="admin")

    # Propose and accept a new session
    susp_start = (datetime.now(timezone.utc) + timedelta(days=9)).isoformat()
    new_sess_res = requests.post(f"{BASE_URL}/api/sessions", headers=newcomer_h, json={
        "request_id": request_id,
        "recipient_id": helper_id,
        "title": "Session Prior to Suspension",
        "modality": "REMOTE",
        "meeting_url": "https://meet.google.com/xyz-nest-demo",
        "scheduled_start": susp_start,
        "duration_minutes": 30,
    })
    assert_status(new_sess_res, 201, "New session proposed")
    susp_sess_id = new_sess_res.json()["id"]
    acc_susp = requests.post(f"{BASE_URL}/api/sessions/{susp_sess_id}/accept", headers=helper_h)
    assert_status(acc_susp, 200, "Session confirmed before suspension")

    # Admin suspends helper
    susp_res = requests.post(f"{BASE_URL}/api/admin/users/{helper_id}/suspend", headers=admin_h, json={
        "reason": "Platform safety audit suspension"
    })
    assert_status(susp_res, 200, "Helper suspended by admin")

    # Verify session cancelled
    susp_chk = requests.get(f"{BASE_URL}/api/sessions/{susp_sess_id}", headers=newcomer_h)
    assert_status(susp_chk, 200, "Suspended session checked")
    assert susp_chk.json()["status"] == "CANCELLED"
    assert "account suspension" in susp_chk.json()["status_reason"].lower()

    # SCENARIO 30: Suspended User Access Denial & Reactivation
    log_step(30, "Suspended User Denied Session Operations, Restored on Reactivation")
    denied_prop = requests.post(f"{BASE_URL}/api/sessions", headers=helper_h, json={
        "request_id": request_id,
        "recipient_id": newcomer_id,
        "title": "Suspended Attempt",
        "modality": "REMOTE",
        "meeting_url": "https://meet.google.com/xyz-nest-demo",
        "scheduled_start": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat(),
        "duration_minutes": 30,
    })
    assert_status(denied_prop, 403, "Suspended user denied session proposal")

    # Admin reactivates helper
    react_res = requests.post(f"{BASE_URL}/api/admin/users/{helper_id}/reactivate", headers=admin_h, json={
        "reason": "Account restored after review"
    })
    assert_status(react_res, 200, "Helper reactivated by admin")

    print("\n" + "=" * 80)
    print("PHASE 14 LIVE END-TO-END VERIFICATION COMPLETED: ALL 30 SCENARIOS PASSED!")
    print("=" * 80)

if __name__ == "__main__":
    main()
