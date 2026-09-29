#!/usr/bin/env python3
"""
NEST Phase 12 Live End-to-End Verification Script
Tests the Community Intelligence Layer against the live running backend on http://127.0.0.1:8000.
Executes 25 comprehensive verification steps without mocks.
"""

import os
import sys
import uuid
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_URL = "http://127.0.0.1:8000"

def log_step(num: int, title: str):
    print(f"\n[STEP {num:02d}] {title}")

def assert_status(resp: requests.Response, expected: int, msg: str = ""):
    if resp.status_code != expected:
        print(f"FAILED: Expected {expected}, got {resp.status_code}. Response: {resp.text}")
        sys.exit(1)
    print(f"  PASS: HTTP {resp.status_code} {msg}")

def register_and_login(name: str, email: str, password: str = "Password123!"):
    reg = requests.post(f"{BASE_URL}/api/auth/register", json={
        "name": name, "email": email, "password": password
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
    print("=" * 70)
    print("NEST PHASE 12 — COMMUNITY INTELLIGENCE LIVE E2E VERIFICATION")
    print("=" * 70)

    # Health check
    h = requests.get(f"{BASE_URL}/api/health")
    assert_status(h, 200, "Health check online")

    # Step 1: Register Alice, Bob, and Carol
    log_step(1, "Register Alice, Bob, and Carol test users")
    uid = uuid.uuid4().hex[:6]
    alice_id, alice_headers = register_and_login("Alice Baner", f"alice_c_{uid}@example.test")
    bob_id, bob_headers = register_and_login("Bob Tech", f"bob_c_{uid}@example.test")
    carol_id, carol_headers = register_and_login("Carol Local", f"carol_c_{uid}@example.test")

    # Step 2: Unauthenticated POST questions rejected (401)
    log_step(2, "Unauthenticated question creation returns 401 Unauthorized")
    unauth_post = requests.post(f"{BASE_URL}/api/community/questions", json={
        "title": "Unauthenticated Question Test",
        "body": "This question must not succeed without auth credentials.",
        "category": "DAILY_LIFE"
    })
    assert_status(unauth_post, 401, "Unauthenticated creation blocked")

    # Step 3: Honest empty search when criteria don't match
    log_step(3, "Search with nonexistent keywords returns honest empty result")
    search_empty = requests.get(f"{BASE_URL}/api/community/questions", params={"q": f"nonexistent_query_{uid}"})
    assert_status(search_empty, 200)
    assert search_empty.json()["total"] == 0
    assert len(search_empty.json()["questions"]) == 0
    print("  PASS: Zero manufactured questions returned")

    # Step 4: Alice asks Question 1
    log_step(4, "Alice posts Question 1 with location tags")
    q1_resp = requests.post(f"{BASE_URL}/api/community/questions", headers=alice_headers, json={
        "title": "Best broadband and power backup in Baner Pune?",
        "body": "Relocating to Baner near High Street. Need recommendations for fiber ISP and inverter setups for home office.",
        "category": "DAILY_LIFE",
        "city": "Pune",
        "area": "Baner"
    })
    assert_status(q1_resp, 201, "Question 1 created")
    q1 = q1_resp.json()
    q1_id = q1["id"]
    assert q1["author"]["name"] == "Alice Baner"
    assert q1["status"] == "OPEN"
    assert q1["has_accepted_answer"] is False
    assert q1["answers_count"] == 0
    print(f"  PASS: Question ID = {q1_id}")

    # Step 5: Location Privacy Check
    log_step(5, "Verify Question location exposes only city/area, no private coordinates")
    assert q1.get("city") == "Pune"
    assert q1.get("area") == "Baner"
    assert "latitude" not in q1
    assert "longitude" not in q1
    print("  PASS: Location privacy strictly preserved (city/area only)")

    # Step 6: Public browse
    log_step(6, "Public unauthenticated users can view community questions")
    pub_get = requests.get(f"{BASE_URL}/api/community/questions/{q1_id}")
    assert_status(pub_get, 200, "Public detail readable")
    assert pub_get.json()["id"] == q1_id

    # Step 7: Bob posts Answer 1
    log_step(7, "Bob posts Answer 1 to Question 1")
    ans1_resp = requests.post(f"{BASE_URL}/api/community/questions/{q1_id}/answers", headers=bob_headers, json={
        "body": "JioFiber is extremely stable in Baner with over 99.8% uptime and quick service."
    })
    assert_status(ans1_resp, 201, "Bob's answer posted")
    ans1 = ans1_resp.json()
    ans1_id = ans1["id"]
    assert ans1["author"]["name"] == "Bob Tech"
    assert ans1["helpful_votes"] == 0
    assert ans1["is_accepted"] is False

    # Step 8: Verify Bob's initial trust signals (reputation UNAVAILABLE)
    log_step(8, "Verify Bob's factual trust signals (cold start: UNAVAILABLE)")
    trust_b = ans1["author_trust_signals"]
    assert trust_b["reputation_status"] == "UNAVAILABLE"
    assert trust_b["average_rating"] is None
    assert trust_b["review_count"] == 0
    assert trust_b["completed_interactions_count"] == 0
    print("  PASS: Factual trust signals report UNAVAILABLE (no fake stars/scores)")

    # Step 9: Carol posts Answer 2
    log_step(9, "Carol posts Answer 2 to Question 1")
    ans2_resp = requests.post(f"{BASE_URL}/api/community/questions/{q1_id}/answers", headers=carol_headers, json={
        "body": "Airtel Xstream has slightly better routing for US servers and power cuts are rare here."
    })
    assert_status(ans2_resp, 201, "Carol's answer posted")
    ans2_id = ans2_resp.json()["id"]

    # Step 10: Self-voting prevention (400)
    log_step(10, "Prevent Bob from voting on his own answer (400 Bad Request)")
    self_vote = requests.post(f"{BASE_URL}/api/community/questions/{q1_id}/answers/{ans1_id}/vote", headers=bob_headers, json={
        "vote": "HELPFUL"
    })
    assert_status(self_vote, 400, "Self-voting correctly rejected")

    # Step 11: Alice votes HELPFUL on Bob's answer
    log_step(11, "Alice votes HELPFUL on Bob's answer")
    vote_h = requests.post(f"{BASE_URL}/api/community/questions/{q1_id}/answers/{ans1_id}/vote", headers=alice_headers, json={
        "vote": "HELPFUL"
    })
    assert_status(vote_h, 200, "Vote recorded")
    data_v1 = vote_h.json()
    assert data_v1["helpful_votes"] == 1
    assert data_v1["not_helpful_votes"] == 0
    assert data_v1["vote"] == "HELPFUL"
    print("  PASS: Helpful votes == 1")

    # Step 12: Alice changes vote to NOT_HELPFUL
    log_step(12, "Alice changes vote to NOT_HELPFUL")
    vote_nh = requests.post(f"{BASE_URL}/api/community/questions/{q1_id}/answers/{ans1_id}/vote", headers=alice_headers, json={
        "vote": "NOT_HELPFUL"
    })
    assert_status(vote_nh, 200, "Vote updated")
    data_v2 = vote_nh.json()
    assert data_v2["helpful_votes"] == 0
    assert data_v2["not_helpful_votes"] == 1
    assert data_v2["vote"] == "NOT_HELPFUL"
    print("  PASS: Helpful == 0, Not Helpful == 1")

    # Step 13: Alice removes her vote
    log_step(13, "Alice removes her vote")
    vote_del = requests.delete(f"{BASE_URL}/api/community/questions/{q1_id}/answers/{ans1_id}/vote", headers=alice_headers)
    assert_status(vote_del, 200, "Vote removed")
    data_v3 = vote_del.json()
    assert data_v3["helpful_votes"] == 0
    assert data_v3["not_helpful_votes"] == 0
    assert data_v3["vote"] is None
    print("  PASS: Neutral votes and null user_vote")

    # Step 14: Accumulate helpful votes
    log_step(14, "Alice and Carol vote HELPFUL on Bob's answer")
    requests.post(f"{BASE_URL}/api/community/questions/{q1_id}/answers/{ans1_id}/vote", headers=alice_headers, json={"vote": "HELPFUL"})
    ans_carol_v = requests.post(f"{BASE_URL}/api/community/questions/{q1_id}/answers/{ans1_id}/vote", headers=carol_headers, json={"vote": "HELPFUL"})
    assert ans_carol_v.json()["helpful_votes"] == 2
    print("  PASS: Bob's answer helpful_votes == 2")

    # Step 15: Non-author cannot accept answer (403)
    log_step(15, "Non-author (Bob) cannot accept answer (403 Forbidden)")
    bob_accept = requests.post(f"{BASE_URL}/api/community/questions/{q1_id}/answers/{ans1_id}/accept", headers=bob_headers)
    assert_status(bob_accept, 403, "Non-author acceptance forbidden")

    # Step 16: Question author (Alice) accepts Bob's answer
    log_step(16, "Question author (Alice) accepts Bob's answer")
    alice_accept = requests.post(f"{BASE_URL}/api/community/questions/{q1_id}/answers/{ans1_id}/accept", headers=alice_headers)
    assert_status(alice_accept, 200, "Bob's answer accepted")
    assert alice_accept.json()["is_accepted"] is True

    # Verify Question status transitioned to RESOLVED
    q1_updated = requests.get(f"{BASE_URL}/api/community/questions/{q1_id}").json()
    assert q1_updated["has_accepted_answer"] is True
    assert q1_updated["status"] == "RESOLVED"
    print("  PASS: Question status == RESOLVED, has_accepted_answer == True")

    # Step 17: Single accepted answer invariant
    log_step(17, "Single Accepted Answer rule: Alice accepts Carol's answer, Bob's is unaccepted")
    alice_accept_carol = requests.post(f"{BASE_URL}/api/community/questions/{q1_id}/answers/{ans2_id}/accept", headers=alice_headers)
    assert_status(alice_accept_carol, 200, "Carol's answer accepted")
    assert alice_accept_carol.json()["is_accepted"] is True

    # Re-fetch Question 1 detail
    q1_detail = requests.get(f"{BASE_URL}/api/community/questions/{q1_id}").json()
    answers = {a["id"]: a for a in q1_detail["answers"]}
    assert answers[ans2_id]["is_accepted"] is True
    assert answers[ans1_id]["is_accepted"] is False
    print("  PASS: Invariant held: Only Carol's answer is accepted, Bob's was cleanly unaccepted")

    # Step 18: Request Integration — Alice creates a request
    log_step(18, "Alice creates a newcomer request matching Question 1")
    req_resp = requests.post(f"{BASE_URL}/api/requests", headers=alice_headers, json={
        "text": "Need advice on reliable high-speed broadband setup in Baner Pune"
    })
    assert_status(req_resp, 201, "Newcomer request created")
    req_id = req_resp.json()["id"]

    # Step 19: Request Community Intelligence surfaces Question 1
    log_step(19, "GET /api/community/for-request/{req_id} surfaces Question 1")
    rel_q = requests.get(f"{BASE_URL}/api/community/for-request/{req_id}", headers=alice_headers, params={"limit": 20})
    assert_status(rel_q, 200, "Related questions retrieved")
    rel_data = rel_q.json()
    assert rel_data["total"] >= 1
    matched_ids = [str(item["question"]["id"]) for item in rel_data["items"]]
    assert q1_id in matched_ids
    print(f"  PASS: Question {q1_id} surfaced for request {req_id}")

    # Step 20: Request Intelligence honest empty state
    log_step(20, "Unrelated request returns honest empty community list")
    req_unrelated = requests.post(f"{BASE_URL}/api/requests", headers=alice_headers, json={
        "text": "Looking for scuba diving lessons in Guwahati Assam"
    })
    assert_status(req_unrelated, 201)
    unrel_id = req_unrelated.json()["id"]
    rel_unrel = requests.get(f"{BASE_URL}/api/community/for-request/{unrel_id}", headers=alice_headers)
    assert_status(rel_unrel, 200)
    assert rel_unrel.json()["total"] == 0
    print("  PASS: Zero fake matches returned for unrelated request")

    # Step 21: Real Reputation Hydration (Phase 9 review integration)
    log_step(21, "Connect Alice & Bob, complete interaction, and submit review")
    conn_resp = requests.post(f"{BASE_URL}/api/connections", headers=alice_headers, json={
        "request_id": req_id,
        "helper_id": bob_id,
        "initial_message": "Can you help me choose an ISP?"
    })
    assert_status(conn_resp, 201, "Connection created")
    conn_id = conn_resp.json()["id"]

    # Bob accepts connection
    requests.patch(f"{BASE_URL}/api/connections/{conn_id}", headers=bob_headers, json={"action": "accept"})
    # Alice marks connection completed
    requests.post(f"{BASE_URL}/api/connections/{conn_id}/complete", headers=alice_headers)
    # Alice submits 5-star review for Bob
    rev_resp = requests.post(f"{BASE_URL}/api/connections/{conn_id}/reviews", headers=alice_headers, json={
        "rating": 5,
        "comment": "Super helpful local advice on Baner internet!"
    })
    assert_status(rev_resp, 201, "5-star review created")

    # Now re-fetch Question 1 and check Bob's author trust signals
    q1_refetch = requests.get(f"{BASE_URL}/api/community/questions/{q1_id}").json()
    bob_ans_refetch = next(a for a in q1_refetch["answers"] if a["author_id"] == bob_id)
    bob_trust = bob_ans_refetch["author_trust_signals"]
    assert bob_trust["reputation_status"] == "AVAILABLE"
    assert bob_trust["average_rating"] == 5.0
    assert bob_trust["review_count"] == 1
    assert bob_trust["completed_interactions_count"] == 1
    print("  PASS: Bob's trust signals now dynamically hydrated to AVAILABLE (5.0 stars, 1 review)")

    # Step 22: Safety & Reporting — Carol reports Bob's answer
    log_step(22, "Carol reports Bob's answer for SPAM")
    rep_resp = requests.post(f"{BASE_URL}/api/reports", headers=carol_headers, json={
        "reported_user_id": bob_id,
        "question_id": q1_id,
        "answer_id": ans1_id,
        "reason": "SPAM",
        "description": "Suspicious ISP referral code mentioned."
    })
    assert_status(rep_resp, 201, "Report created with question_id and answer_id")
    rep_data = rep_resp.json()
    assert rep_data["question_id"] == q1_id
    assert rep_data["answer_id"] == ans1_id

    # Step 23: Anti-spam duplicate report prevention
    log_step(23, "Duplicate report on same answer rejected (409 Conflict)")
    dup_rep = requests.post(f"{BASE_URL}/api/reports", headers=carol_headers, json={
        "reported_user_id": bob_id,
        "question_id": q1_id,
        "answer_id": ans1_id,
        "reason": "SPAM"
    })
    assert_status(dup_rep, 409, "Anti-spam duplicate report rejected with 409 Conflict")

    # Step 24: Bidirectional Blocking exclusion
    log_step(24, "Alice blocks Carol -> Carol cannot post answers to Alice's questions")
    blk_resp = requests.post(f"{BASE_URL}/api/blocks/{carol_id}", headers=alice_headers)
    assert_status(blk_resp, 201, "Carol blocked by Alice")

    carol_blocked_ans = requests.post(f"{BASE_URL}/api/community/questions/{q1_id}/answers", headers=carol_headers, json={
        "body": "Blocked user attempting to answer."
    })
    assert_status(carol_blocked_ans, 403, "Blocked user forbidden from answering")

    # Step 25: Account suspension enforcement
    log_step(25, "Suspended user cannot post community questions")
    admin_id, admin_headers = register_and_login("Admin Community", f"admin_{uid}@example.test")
    from app.db.database import SessionLocal
    from app.models.user import User, UserRole
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.id == uuid.UUID(admin_id)).first()
        u.role = UserRole.ADMIN
        db.commit()
    finally:
        db.close()

    susp_resp = requests.post(f"{BASE_URL}/api/admin/users/{carol_id}/suspend", headers=admin_headers, json={
        "reason": "Safety violations"
    })
    assert_status(susp_resp, 200, "Carol suspended by admin")

    carol_susp_q = requests.post(f"{BASE_URL}/api/community/questions", headers=carol_headers, json={
        "title": "Suspended user question attempt",
        "body": "This question should fail because user account is suspended.",
        "category": "HOUSING"
    })
    assert_status(carol_susp_q, 403, "Suspended user forbidden from community interactions")

    print("\n" + "=" * 70)
    print("ALL 25 PHASE 12 LIVE VERIFICATION STEPS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    main()
