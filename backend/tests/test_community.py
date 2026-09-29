import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from tests.conftest import create_authenticated_user
from app.db.database import SessionLocal
from app.models.community import (
    CommunityAnswer,
    CommunityAnswerVote,
    CommunityQuestion,
    QuestionCategory,
    QuestionStatus,
    VoteType,
)
from app.models.connection import Connection, ConnectionStatus
from app.models.embedding import Embedding
from app.models.review import Review
from app.models.user import User, UserRole


# ============================================================================
# 1. Unauthenticated & Authorization Tests
# ============================================================================

def test_unauthenticated_community_access(client: TestClient):
    # Questions creation requires auth
    res = client.post("/api/community/questions", json={
        "title": "Unauthenticated Question",
        "body": "This question should fail without authentication.",
        "category": "ACCOMMODATION",
    })
    assert res.status_code == 401

    # Answer creation requires auth
    dummy_qid = uuid.uuid4()
    res = client.post(f"/api/community/questions/{dummy_qid}/answers", json={
        "body": "Unauthenticated answer body.",
    })
    assert res.status_code == 401

    # Vote requires auth
    dummy_aid = uuid.uuid4()
    res = client.post(f"/api/community/answers/{dummy_aid}/vote", json={
        "vote": "HELPFUL",
    })
    assert res.status_code == 401


# ============================================================================
# 2. Question Lifecycle, Validation & Embedding Generation
# ============================================================================

def test_question_lifecycle_and_embedding(client: TestClient):
    alice = create_authenticated_user(client, "Alice Q", f"alice_q_{uuid.uuid4().hex[:6]}@example.test")
    bob = create_authenticated_user(client, "Bob Q", f"bob_q_{uuid.uuid4().hex[:6]}@example.test")

    # 1. Validation failure: title too short
    res_bad = client.post("/api/community/questions", headers=alice["headers"], json={
        "title": "Hi",
        "body": "Valid body text with enough characters to pass validation.",
        "category": "TRANSPORT",
    })
    assert res_bad.status_code == 422

    # 2. Create valid question
    res = client.post("/api/community/questions", headers=alice["headers"], json={
        "title": "What is the best commute option from Baner to Hinjewadi?",
        "body": "Moving next month and wondering about bus frequency vs bike commute during peak hours.",
        "category": "TRANSPORT",
        "city": "Pune",
        "area": "Baner",
    })
    assert res.status_code == 201
    q_data = res.json()
    q_id = q_data["id"]
    assert q_data["title"] == "What is the best commute option from Baner to Hinjewadi?"
    assert q_data["category"] == "TRANSPORT"
    assert q_data["city"] == "Pune"
    assert q_data["area"] == "Baner"
    assert q_data["status"] == "OPEN"
    assert q_data["answers_count"] == 0

    # Verify embedding exists in embeddings table
    db = SessionLocal()
    try:
        emb = db.query(Embedding).filter(
            Embedding.owner_type == "community_question",
            Embedding.owner_id == uuid.UUID(q_id),
        ).first()
        assert emb is not None
        assert emb.dimension == 384
        orig_hash = emb.source_hash
    finally:
        db.close()

    # 3. List questions with filters
    res_list = client.get("/api/community/questions?category=TRANSPORT&city=Pune")
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert list_data["total"] >= 1
    assert any(q["id"] == q_id for q in list_data["questions"])

    # 4. Detail endpoint
    res_detail = client.get(f"/api/community/questions/{q_id}")
    assert res_detail.status_code == 200
    detail_data = res_detail.json()
    assert detail_data["id"] == q_id
    assert detail_data["answers"] == []

    # 5. Non-author edit -> 403 Forbidden
    res_unauth_edit = client.patch(
        f"/api/community/questions/{q_id}",
        headers=bob["headers"],
        json={"title": "Hacked Title Attempt"},
    )
    assert res_unauth_edit.status_code == 403

    # 6. Author edit -> regenerates embedding
    res_edit = client.patch(
        f"/api/community/questions/{q_id}",
        headers=alice["headers"],
        json={
            "title": "What is the best commute option from Baner to Hinjewadi Phase 1?",
            "area": "Baner / Balewadi",
        },
    )
    assert res_edit.status_code == 200
    assert res_edit.json()["title"] == "What is the best commute option from Baner to Hinjewadi Phase 1?"

    db = SessionLocal()
    try:
        emb_after = db.query(Embedding).filter(
            Embedding.owner_type == "community_question",
            Embedding.owner_id == uuid.UUID(q_id),
        ).first()
        assert emb_after is not None
        # Source hash changed because title and area changed
        assert emb_after.source_hash != orig_hash
    finally:
        db.close()

    # 7. Non-author delete -> 403 Forbidden
    res_unauth_del = client.delete(f"/api/community/questions/{q_id}", headers=bob["headers"])
    assert res_unauth_del.status_code == 403

    # 8. Author delete -> 204 No Content
    res_del = client.delete(f"/api/community/questions/{q_id}", headers=alice["headers"])
    assert res_del.status_code == 204

    # Verify deleted in DB and embeddings cleaned up
    db = SessionLocal()
    try:
        assert db.query(CommunityQuestion).filter(CommunityQuestion.id == uuid.UUID(q_id)).first() is None
        assert db.query(Embedding).filter(
            Embedding.owner_type == "community_question",
            Embedding.owner_id == uuid.UUID(q_id),
        ).first() is None
    finally:
        db.close()


# ============================================================================
# 3. Answer Lifecycle, Accepted Answer & Single Accepted Rule
# ============================================================================

def test_answers_and_accepted_answer(client: TestClient):
    alice = create_authenticated_user(client, "Alice Ans", f"alice_ans_{uuid.uuid4().hex[:6]}@example.test")
    bob = create_authenticated_user(client, "Bob Ans", f"bob_ans_{uuid.uuid4().hex[:6]}@example.test")
    carol = create_authenticated_user(client, "Carol Ans", f"carol_ans_{uuid.uuid4().hex[:6]}@example.test")

    # Alice asks a question
    res_q = client.post("/api/community/questions", headers=alice["headers"], json={
        "title": "Is Hinjewadi Phase 1 walkable from Blue Ridge?",
        "body": "Looking at renting in Blue Ridge, wondering if I can walk to Phase 1 offices.",
        "category": "LOCAL_SERVICES",
        "city": "Pune",
        "area": "Hinjewadi",
    })
    q_id = res_q.json()["id"]

    # Bob answers
    res_a1 = client.post(f"/api/community/questions/{q_id}/answers", headers=bob["headers"], json={
        "body": "Yes, Blue Ridge is right next to Phase 1 circle. It's about a 10-15 minute walk.",
    })
    assert res_a1.status_code == 201
    a1_data = res_a1.json()
    a1_id = a1_data["id"]
    assert a1_data["is_accepted"] is False
    assert a1_data["helpful_votes"] == 0

    # Carol answers
    res_a2 = client.post(f"/api/community/questions/{q_id}/answers", headers=carol["headers"], json={
        "body": "It's walkable during the day, but footpaths can be crowded in monsoon season.",
    })
    assert res_a2.status_code == 201
    a2_id = res_a2.json()["id"]

    # Verify answers list
    res_alist = client.get(f"/api/community/questions/{q_id}/answers")
    assert res_alist.status_code == 200
    assert res_alist.json()["total"] == 2

    # Non-question-author (Bob) tries to accept Carol's answer -> 403 Forbidden
    res_unauth_accept = client.post(
        f"/api/community/questions/{q_id}/accept/{a2_id}",
        headers=bob["headers"],
    )
    assert res_unauth_accept.status_code == 403

    # Question author (Alice) accepts Bob's answer
    res_accept1 = client.post(
        f"/api/community/questions/{q_id}/accept/{a1_id}",
        headers=alice["headers"],
    )
    assert res_accept1.status_code == 200
    assert res_accept1.json()["is_accepted"] is True

    # Alice accepts Carol's answer -> Bob's answer must automatically be unaccepted!
    res_accept2 = client.post(
        f"/api/community/questions/{q_id}/accept/{a2_id}",
        headers=alice["headers"],
    )
    assert res_accept2.status_code == 200
    assert res_accept2.json()["is_accepted"] is True

    # Check detail: only one answer is accepted
    res_detail = client.get(f"/api/community/questions/{q_id}")
    answers = res_detail.json()["answers"]
    accepted_answers = [a for a in answers if a["is_accepted"]]
    assert len(accepted_answers) == 1
    assert accepted_answers[0]["id"] == a2_id

    # Bob edits his answer
    res_edit_a = client.patch(
        f"/api/community/answers/{a1_id}",
        headers=bob["headers"],
        json={"body": "Updated: Yes, it is 10-15 minutes walk and there are shared autos too."},
    )
    assert res_edit_a.status_code == 200
    assert "shared autos" in res_edit_a.json()["body"]

    # Carol tries to edit Bob's answer -> 403 Forbidden
    res_bad_edit = client.patch(
        f"/api/community/answers/{a1_id}",
        headers=carol["headers"],
        json={"body": "Unauthorized edit"},
    )
    assert res_bad_edit.status_code == 403

    # Close question and verify no new answers can be posted
    client.patch(
        f"/api/community/questions/{q_id}",
        headers=alice["headers"],
        json={"status": "CLOSED"},
    )
    res_closed_ans = client.post(
        f"/api/community/questions/{q_id}/answers",
        headers=bob["headers"],
        json={"body": "Answer to closed question should fail."},
    )
    assert res_closed_ans.status_code == 400


# ============================================================================
# 4. Voting on Answers (Helpful / Not Helpful)
# ============================================================================

def test_answer_voting(client: TestClient):
    alice = create_authenticated_user(client, "Alice Vote", f"alice_v_{uuid.uuid4().hex[:6]}@example.test")
    bob = create_authenticated_user(client, "Bob Vote", f"bob_v_{uuid.uuid4().hex[:6]}@example.test")
    carol = create_authenticated_user(client, "Carol Vote", f"carol_v_{uuid.uuid4().hex[:6]}@example.test")

    # Alice asks, Bob answers
    res_q = client.post("/api/community/questions", headers=alice["headers"], json={
        "title": "Where can I find vegetarian tiffin service in Baner?",
        "body": "Need monthly home-cooked vegetarian tiffin delivery near Pan Card Club road.",
        "category": "FOOD",
        "city": "Pune",
        "area": "Baner",
    })
    q_id = res_q.json()["id"]

    res_a = client.post(f"/api/community/questions/{q_id}/answers", headers=bob["headers"], json={
        "body": "Try Annapurna Tiffins near D-Mart, they deliver daily for around 3000/month.",
    })
    a_id = res_a.json()["id"]

    # 1. Author (Bob) tries to vote on own answer -> 400 Bad Request
    res_self_vote = client.post(f"/api/community/answers/{a_id}/vote", headers=bob["headers"], json={
        "vote": "HELPFUL",
    })
    assert res_self_vote.status_code == 400

    # 2. Alice votes HELPFUL
    res_vote_h = client.post(f"/api/community/answers/{a_id}/vote", headers=alice["headers"], json={
        "vote": "HELPFUL",
    })
    assert res_vote_h.status_code == 200
    v_data = res_vote_h.json()
    assert v_data["helpful_votes"] == 1
    assert v_data["not_helpful_votes"] == 0

    # 3. Carol votes HELPFUL
    client.post(f"/api/community/answers/{a_id}/vote", headers=carol["headers"], json={
        "vote": "HELPFUL",
    })

    # 4. Carol changes vote to NOT_HELPFUL
    res_vote_nh = client.post(f"/api/community/answers/{a_id}/vote", headers=carol["headers"], json={
        "vote": "NOT_HELPFUL",
    })
    assert res_vote_nh.status_code == 200
    v_data2 = res_vote_nh.json()
    assert v_data2["helpful_votes"] == 1
    assert v_data2["not_helpful_votes"] == 1

    # 5. Carol removes vote
    res_rm_vote = client.delete(f"/api/community/answers/{a_id}/vote", headers=carol["headers"])
    assert res_rm_vote.status_code == 200
    v_data3 = res_rm_vote.json()
    assert v_data3["helpful_votes"] == 1
    assert v_data3["not_helpful_votes"] == 0


# ============================================================================
# 5. Author Factual Trust Signals
# ============================================================================

def test_author_trust_signals(client: TestClient):
    alice = create_authenticated_user(client, "Alice Rep", f"alice_rep_{uuid.uuid4().hex[:6]}@example.test")
    bob = create_authenticated_user(client, "Bob Rep", f"bob_rep_{uuid.uuid4().hex[:6]}@example.test")

    # Bob has 0 reviews -> status UNAVAILABLE
    res_q = client.post("/api/community/questions", headers=alice["headers"], json={
        "title": "Need suggestions for internet providers in Baner",
        "body": "Is Airtel or JioFiber better in Baner area?",
        "category": "DAILY_LIFE",
        "city": "Pune",
        "area": "Baner",
    })
    q_id = res_q.json()["id"]

    res_a = client.post(f"/api/community/questions/{q_id}/answers", headers=bob["headers"], json={
        "body": "JioFiber is very stable near Balewadi High Street.",
    })
    a_id = res_a.json()["id"]

    res_detail = client.get(f"/api/community/questions/{q_id}")
    ans_item = res_detail.json()["answers"][0]
    trust = ans_item["author_trust_signals"]
    assert trust["reputation_status"] == "UNAVAILABLE"
    assert trust["average_rating"] is None
    assert trust["review_count"] == 0

    # Give Bob a completed interaction and review
    req_resp = client.post(
        "/api/requests",
        headers=alice["headers"],
        json={"text": "Need internet setup help in Baner."},
    )
    req_id = req_resp.json()["id"]

    db = SessionLocal()
    try:
        conn = Connection(
            id=uuid.uuid4(),
            request_id=uuid.UUID(req_id),
            requester_id=uuid.UUID(alice["user"]["id"]),
            helper_id=uuid.UUID(bob["user"]["id"]),
            status=ConnectionStatus.COMPLETED.value,
            completed_at=datetime.now(timezone.utc),
        )
        db.add(conn)
        db.flush()

        rev = Review(
            id=uuid.uuid4(),
            connection_id=conn.id,
            reviewer_id=uuid.UUID(alice["user"]["id"]),
            reviewee_id=uuid.UUID(bob["user"]["id"]),
            rating=5,
            comment="Excellent helper, very knowledgeable about Pune!",
        )
        db.add(rev)
        db.commit()
    finally:
        db.close()

    # Re-fetch question detail -> Bob should now show AVAILABLE reputation
    res_detail2 = client.get(f"/api/community/questions/{q_id}")
    trust2 = res_detail2.json()["answers"][0]["author_trust_signals"]
    assert trust2["reputation_status"] == "AVAILABLE"
    assert trust2["average_rating"] == 5.0
    assert trust2["review_count"] == 1
    assert trust2["completed_interactions_count"] == 1


# ============================================================================
# 6. Semantic Search with pgvector
# ============================================================================

def test_semantic_search_pgvector(client: TestClient):
    alice = create_authenticated_user(client, "Alice Sem", f"alice_sem_{uuid.uuid4().hex[:6]}@example.test")

    # Create questions with distinct semantic themes
    res_q1 = client.post("/api/community/questions", headers=alice["headers"], json={
        "title": "Affordable PG accommodation with food around Hinjewadi Phase 1",
        "body": "Looking for paying guest rooms under 8000 rupees with food facility near IT park.",
        "category": "ACCOMMODATION",
        "city": "Pune",
        "area": "Hinjewadi",
    })
    q1_id = res_q1.json()["id"]

    res_q2 = client.post("/api/community/questions", headers=alice["headers"], json={
        "title": "Best paediatrician clinic near Whitefield Bangalore",
        "body": "Need emergency child specialist recommendations near ITPL area.",
        "category": "HEALTHCARE",
        "city": "Bengaluru",
        "area": "Whitefield",
    })
    q2_id = res_q2.json()["id"]

    # Search query: "cheap rooms near Hinjewadi IT park"
    res_search = client.get("/api/community/search?q=cheap rooms near Hinjewadi IT park")
    assert res_search.status_code == 200
    search_data = res_search.json()
    assert search_data["total"] >= 1
    # Top result should be the Hinjewadi accommodation question
    top_result = search_data["results"][0]
    assert top_result["question"]["id"] == q1_id
    assert top_result["similarity_score"] > 0.4


# ============================================================================
# 7. Request-Driven Community Intelligence Integration
# ============================================================================

def test_request_community_knowledge_integration(client: TestClient):
    alice = create_authenticated_user(client, "Alice Req", f"alice_req_{uuid.uuid4().hex[:6]}@example.test")
    bob = create_authenticated_user(client, "Bob Req", f"bob_req_{uuid.uuid4().hex[:6]}@example.test")

    # Create a community question about Hinjewadi PGs
    res_q = client.post("/api/community/questions", headers=bob["headers"], json={
        "title": "PG rent rates and deposits in Hinjewadi Phase 1",
        "body": "Typical monthly rent for single sharing PG is 9000-11000 and double sharing is 6000-7500.",
        "category": "COST_OF_LIVING",
        "city": "Pune",
        "area": "Hinjewadi",
    })
    q_id = res_q.json()["id"]

    # Alice creates a natural language request
    res_req = client.post("/api/requests", headers=alice["headers"], json={
        "text": "Moving to Pune for work, looking for affordable accommodation and PG options near Hinjewadi Phase 1.",
    })
    req_id = res_req.json()["id"]

    # Fetch community knowledge for Alice's request
    res_comm = client.get(f"/api/community/for-request/{req_id}", headers=alice["headers"])
    assert res_comm.status_code == 200
    comm_data = res_comm.json()
    assert comm_data["total"] >= 1
    assert any(item["question"]["id"] == q_id for item in comm_data["items"])


# ============================================================================
# 8. Safety: Blocking & Suspension Enforcement
# ============================================================================

def test_safety_blocking_and_suspension_in_community(client: TestClient):
    alice = create_authenticated_user(client, "Alice Safe", f"alice_safe_{uuid.uuid4().hex[:6]}@example.test")
    bob = create_authenticated_user(client, "Bob Safe", f"bob_safe_{uuid.uuid4().hex[:6]}@example.test")
    admin = create_authenticated_user(client, "Admin Safe", f"admin_safe_{uuid.uuid4().hex[:6]}@example.test")

    # Promote admin
    db = SessionLocal()
    try:
        admin_u = db.query(User).filter(User.id == uuid.UUID(admin["user"]["id"])).first()
        admin_u.role = UserRole.ADMIN
        db.commit()
    finally:
        db.close()

    # Alice creates a question
    res_q = client.post("/api/community/questions", headers=alice["headers"], json={
        "title": "Safe late night commute options in Hinjewadi",
        "body": "Are cabs readily available past midnight near Phase 2?",
        "category": "SAFETY",
        "city": "Pune",
        "area": "Hinjewadi",
    })
    q_id = res_q.json()["id"]

    # Alice blocks Bob
    res_block = client.post(f"/api/blocks/{bob['user']['id']}", headers=alice["headers"])
    assert res_block.status_code in (200, 201)

    # 1. Bob cannot see Alice's question in listing
    res_bob_list = client.get("/api/community/questions", headers=bob["headers"])
    bob_questions = [q["id"] for q in res_bob_list.json()["questions"]]
    assert q_id not in bob_questions

    # 2. Bob cannot view Alice's question detail -> 403 Forbidden
    res_bob_detail = client.get(f"/api/community/questions/{q_id}", headers=bob["headers"])
    assert res_bob_detail.status_code == 403

    # 3. Bob cannot post answer to Alice's question -> 403 Forbidden
    res_bob_ans = client.post(
        f"/api/community/questions/{q_id}/answers",
        headers=bob["headers"],
        json={"body": "Blocked user answer attempt."},
    )
    assert res_bob_ans.status_code == 403

    # 4. Suspension test: Admin suspends Bob
    res_suspend = client.post(
        f"/api/admin/users/{bob['user']['id']}/suspend",
        headers=admin["headers"],
        json={"reason": "Safety violation"},
    )
    assert res_suspend.status_code == 200

    # Suspended Bob cannot create questions -> 403
    res_suspended_q = client.post("/api/community/questions", headers=bob["headers"], json={
        "title": "Suspended user question",
        "body": "This question should be rejected because user is suspended.",
        "category": "OTHER",
    })
    assert res_suspended_q.status_code in (401, 403)


# ============================================================================
# 9. Reporting Community Questions & Answers
# ============================================================================

def test_community_content_reporting(client: TestClient):
    alice = create_authenticated_user(client, "Alice RepQ", f"alice_repq_{uuid.uuid4().hex[:6]}@example.test")
    bob = create_authenticated_user(client, "Bob RepQ", f"bob_repq_{uuid.uuid4().hex[:6]}@example.test")

    # Bob posts a spam question
    res_q = client.post("/api/community/questions", headers=bob["headers"], json={
        "title": "Cheap cryptocurrency investment scheme call this number",
        "body": "Call +91 9999999999 for instant loan and crypto guaranteed returns.",
        "category": "OTHER",
        "city": "Pune",
    })
    q_id = res_q.json()["id"]

    # Alice reports the question
    res_rep = client.post("/api/reports", headers=alice["headers"], json={
        "reported_user_id": bob["user"]["id"],
        "question_id": q_id,
        "reason": "SCAM",
        "description": "Obvious crypto investment financial scam post.",
    })
    assert res_rep.status_code == 201
    rep_data = res_rep.json()
    assert rep_data["question_id"] == q_id
    assert rep_data["reason"] == "SCAM"
    assert rep_data["question_title"] == "Cheap cryptocurrency investment scheme call this number"


# ============================================================================
# 10. Hardening Audit: IDOR, DB Invariant, Search Threshold, Suspension Lifecycle
# ============================================================================

def test_hardening_audit_suite(client: TestClient):
    alice = create_authenticated_user(client, "Alice Hard", f"alice_hard_{uuid.uuid4().hex[:6]}@example.test")
    bob = create_authenticated_user(client, "Bob Hard", f"bob_hard_{uuid.uuid4().hex[:6]}@example.test")
    carol = create_authenticated_user(client, "Carol Hard", f"carol_hard_{uuid.uuid4().hex[:6]}@example.test")
    admin = create_authenticated_user(client, "Admin Hard", f"admin_hard_{uuid.uuid4().hex[:6]}@example.test")

    # Promote admin
    db = SessionLocal()
    try:
        admin_u = db.query(User).filter(User.id == uuid.UUID(admin["user"]["id"])).first()
        admin_u.role = UserRole.ADMIN
        db.commit()
    finally:
        db.close()

    # 1. IDOR Prevention: Bob cannot access Alice's request community knowledge
    alice_req = client.post("/api/requests", headers=alice["headers"], json={
        "text": "Looking for 2BHK flat near Hinjewadi Phase 1 IT Park with parking.",
    })
    alice_req_id = alice_req.json()["id"]

    res_idor = client.get(f"/api/community/for-request/{alice_req_id}", headers=bob["headers"])
    assert res_idor.status_code == 403
    assert "permission" in res_idor.json()["detail"].lower()

    # Alice herself can access it
    res_owner = client.get(f"/api/community/for-request/{alice_req_id}", headers=alice["headers"])
    assert res_owner.status_code == 200

    # 2. Semantic Search Honesty & Thresholding: Unrelated query returns 0 results
    # Create an accommodation question
    client.post("/api/community/questions", headers=alice["headers"], json={
        "title": "Best society for families in Wakad Pune",
        "body": "Looking for gated communities with children play area near Bhumkar Chowk.",
        "category": "ACCOMMODATION",
        "city": "Pune",
        "area": "Wakad",
    })
    # Search for completely unrelated query
    res_unrel = client.get("/api/community/search?q=quantum physics satellite trajectory")
    assert res_unrel.status_code == 200
    assert res_unrel.json()["total"] == 0

    # 3. Database Invariant: Partial Unique Index enforces at most one accepted answer
    q_res = client.post("/api/community/questions", headers=alice["headers"], json={
        "title": "Need reliable plumber in Kothrud Pune",
        "body": "Need emergency plumbing service near MIT college.",
        "category": "LOCAL_SERVICES",
        "city": "Pune",
        "area": "Kothrud",
    })
    qid = uuid.UUID(q_res.json()["id"])

    ans1_res = client.post(f"/api/community/questions/{qid}/answers", headers=bob["headers"], json={
        "body": "Call Ramesh Plumbing at 9876543210.",
    })
    a1_id = uuid.UUID(ans1_res.json()["id"])

    ans2_res = client.post(f"/api/community/questions/{qid}/answers", headers=carol["headers"], json={
        "body": "Local UrbanClap plumbers are fast in Kothrud.",
    })
    a2_id = uuid.UUID(ans2_res.json()["id"])

    # Accept answer 1 via API
    client.post(f"/api/community/questions/{qid}/accept/{a1_id}", headers=alice["headers"])

    # Directly in DB, attempting to force answer 2 as accepted without unaccepting answer 1
    # MUST raise IntegrityError due to uq_question_accepted_answer partial unique index
    db = SessionLocal()
    from sqlalchemy.exc import IntegrityError
    try:
        a2_db = db.query(CommunityAnswer).filter(CommunityAnswer.id == a2_id).first()
        a2_db.is_accepted = True
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()
        db.close()

    # 4. Closed Question Invariant: Cannot answer closed question
    client.patch(f"/api/community/questions/{qid}", headers=alice["headers"], json={
        "status": "CLOSED",
    })
    res_closed_ans = client.post(f"/api/community/questions/{qid}/answers", headers=bob["headers"], json={
        "body": "Attempting to answer a closed question.",
    })
    assert res_closed_ans.status_code == 400
    assert "closed" in res_closed_ans.json()["detail"].lower()

    # Reopen question
    client.patch(f"/api/community/questions/{qid}", headers=alice["headers"], json={
        "status": "OPEN",
    })

    # 5. Suspension Full Lifecycle: Suspend Bob, verify blocked, reactivate, verify restored
    client.post(
        f"/api/admin/users/{bob['user']['id']}/suspend",
        headers=admin["headers"],
        json={"reason": "Audit suspension test"},
    )

    # Bob cannot post question (403)
    res_sq = client.post("/api/community/questions", headers=bob["headers"], json={
        "title": "Suspended question attempt",
        "body": "Should be rejected because user is suspended.",
        "category": "OTHER",
    })
    assert res_sq.status_code == 403

    # Bob cannot post answer (403)
    res_sa = client.post(f"/api/community/questions/{qid}/answers", headers=bob["headers"], json={
        "body": "Suspended answer attempt.",
    })
    assert res_sa.status_code == 403

    # Bob cannot vote (403)
    res_sv = client.post(f"/api/community/answers/{a2_id}/vote", headers=bob["headers"], json={
        "vote": "HELPFUL",
    })
    assert res_sv.status_code == 403

    # Reactivate Bob
    res_react = client.post(
        f"/api/admin/users/{bob['user']['id']}/reactivate",
        headers=admin["headers"],
        json={"reason": "Audit reactivation"},
    )
    assert res_react.status_code == 200

    # Bob can now vote
    res_rv = client.post(f"/api/community/answers/{a2_id}/vote", headers=bob["headers"], json={
        "vote": "HELPFUL",
    })
    assert res_rv.status_code == 200

    # 6. Reporting Honesty: Self report -> 400, duplicate report -> 409, mismatch -> 400, unauthorized -> 403
    # Self-report rejected
    res_self_rep = client.post("/api/reports", headers=alice["headers"], json={
        "reported_user_id": alice["user"]["id"],
        "reason": "HARASSMENT",
    })
    assert res_self_rep.status_code == 400

    # Mismatch author on question report rejected
    res_mismatch = client.post("/api/reports", headers=alice["headers"], json={
        "reported_user_id": carol["user"]["id"],  # Carol didn't author the question
        "question_id": str(qid),
        "reason": "SPAM",
    })
    assert res_mismatch.status_code == 400

    # Valid report on Bob's answer
    res_rep_ans = client.post("/api/reports", headers=alice["headers"], json={
        "reported_user_id": bob["user"]["id"],
        "answer_id": str(a1_id),
        "reason": "SPAM",
        "description": "Suspicious phone number advertising.",
    })
    assert res_rep_ans.status_code == 201
    rep_id = res_rep_ans.json()["id"]

    # Duplicate active report rejected with 409 Conflict
    res_dup = client.post("/api/reports", headers=alice["headers"], json={
        "reported_user_id": bob["user"]["id"],
        "answer_id": str(a1_id),
        "reason": "SPAM",
        "description": "Second identical report attempt.",
    })
    assert res_dup.status_code == 409

    # Unauthorized user (Carol) cannot view Alice's report
    res_unauth_view = client.get(f"/api/reports/{rep_id}", headers=carol["headers"])
    assert res_unauth_view.status_code == 403

    # Admin CAN view report
    res_admin_view = client.get(f"/api/reports/{rep_id}", headers=admin["headers"])
    assert res_admin_view.status_code == 200

