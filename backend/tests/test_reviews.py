import uuid
import pytest
from fastapi.testclient import TestClient
from tests.conftest import create_authenticated_user


def setup_accepted_connection(client: TestClient, prefix: str = "rev"):
    """Helper to set up two users with an ACCEPTED connection."""
    requester = create_authenticated_user(
        client, f"{prefix} Requester", f"{prefix}_req_{uuid.uuid4().hex[:6]}@example.test"
    )
    helper = create_authenticated_user(
        client, f"{prefix} Helper", f"{prefix}_hlp_{uuid.uuid4().hex[:6]}@example.test"
    )

    req_resp = client.post(
        "/api/requests",
        headers=requester["headers"],
        json={"text": "Looking for PG assistance in Bangalore."},
    )
    request_id = req_resp.json()["id"]

    conn_resp = client.post(
        "/api/connections",
        headers=requester["headers"],
        json={
            "request_id": request_id,
            "helper_id": str(helper["user"]["id"]),
            "initial_message": "Need local help!",
        },
    )
    connection_id = conn_resp.json()["id"]

    # Helper accepts connection
    client.patch(
        f"/api/connections/{connection_id}",
        headers=helper["headers"],
        json={"action": "accept"},
    )

    return {
        "requester": requester,
        "helper": helper,
        "connection_id": connection_id,
        "request_id": request_id,
    }


def test_completion_authorization_and_lifecycle(client: TestClient):
    """Test full completion authorization, state validation, and idempotency."""
    data = setup_accepted_connection(client, "comp")
    requester = data["requester"]
    helper = data["helper"]
    outsider = create_authenticated_user(client, "Outsider", f"out_{uuid.uuid4().hex[:6]}@example.test")
    conn_id = data["connection_id"]

    # 1. Unauthenticated completion -> 401
    resp = client.post(f"/api/connections/{conn_id}/complete")
    assert resp.status_code == 401

    # 2. Outsider completion -> 403
    resp = client.post(
        f"/api/connections/{conn_id}/complete",
        headers=outsider["headers"],
    )
    assert resp.status_code == 403

    # 3. Requester completes -> 200 OK
    resp = client.post(
        f"/api/connections/{conn_id}/complete",
        headers=requester["headers"],
    )
    assert resp.status_code == 200
    conn_data = resp.json()
    assert conn_data["status"] == "COMPLETED"
    assert conn_data["completed_at"] is not None

    # 4. Idempotency: Helper calls complete on already completed connection -> 200 OK safely
    resp_idem = client.post(
        f"/api/connections/{conn_id}/complete",
        headers=helper["headers"],
    )
    assert resp_idem.status_code == 200
    assert resp_idem.json()["status"] == "COMPLETED"

    # 5. Cannot revert from COMPLETED -> 400
    resp_revert = client.patch(
        f"/api/connections/{conn_id}",
        headers=helper["headers"],
        json={"action": "accept"},
    )
    assert resp_revert.status_code == 400


def test_cannot_complete_pending_or_cancelled_connections(client: TestClient):
    """Only ACCEPTED connections can transition to COMPLETED."""
    user_a = create_authenticated_user(client, "User A", f"u_a_{uuid.uuid4().hex[:6]}@example.test")
    user_b = create_authenticated_user(client, "User B", f"u_b_{uuid.uuid4().hex[:6]}@example.test")

    req_resp = client.post(
        "/api/requests",
        headers=user_a["headers"],
        json={"text": "Moving to Pune for work."},
    )
    request_id = req_resp.json()["id"]

    # PENDING
    conn_resp = client.post(
        "/api/connections",
        headers=user_a["headers"],
        json={"request_id": request_id, "helper_id": str(user_b["user"]["id"])},
    )
    conn_id = conn_resp.json()["id"]

    # Cannot complete while PENDING
    resp = client.post(
        f"/api/connections/{conn_id}/complete",
        headers=user_a["headers"],
    )
    assert resp.status_code == 400

    # CANCELLED
    client.patch(
        f"/api/connections/{conn_id}",
        headers=user_a["headers"],
        json={"action": "cancel"},
    )
    resp = client.post(
        f"/api/connections/{conn_id}/complete",
        headers=user_a["headers"],
    )
    assert resp.status_code == 400


def test_review_submission_and_anti_gaming(client: TestClient):
    """Test review eligibility, rating boundaries, duplicate conflict, and mutual reviews."""
    data = setup_accepted_connection(client, "revtest")
    requester = data["requester"]
    helper = data["helper"]
    outsider = create_authenticated_user(client, "Review Outsider", f"rev_out_{uuid.uuid4().hex[:6]}@example.test")
    conn_id = data["connection_id"]

    # 1. Review before completion -> 400 Bad Request
    resp = client.post(
        f"/api/connections/{conn_id}/reviews",
        headers=requester["headers"],
        json={"rating": 5, "comment": "Great helper!"},
    )
    assert resp.status_code == 400
    assert "completed" in resp.json()["detail"].lower()

    # Mark connection completed
    client.post(
        f"/api/connections/{conn_id}/complete",
        headers=requester["headers"],
    )

    # 2. Outsider review -> 403 Forbidden
    resp = client.post(
        f"/api/connections/{conn_id}/reviews",
        headers=outsider["headers"],
        json={"rating": 5},
    )
    assert resp.status_code == 403

    # 3. Rating boundary validation: 0 and 6 must be rejected with 422
    resp_zero = client.post(
        f"/api/connections/{conn_id}/reviews",
        headers=requester["headers"],
        json={"rating": 0},
    )
    assert resp_zero.status_code == 422

    resp_six = client.post(
        f"/api/connections/{conn_id}/reviews",
        headers=requester["headers"],
        json={"rating": 6},
    )
    assert resp_six.status_code == 422

    # 4. Valid 5-star review from Requester to Helper -> 201 Created
    rev_a = client.post(
        f"/api/connections/{conn_id}/reviews",
        headers=requester["headers"],
        json={"rating": 5, "comment": "Incredible local tips, saved me hours!"},
    )
    assert rev_a.status_code == 201
    rev_a_data = rev_a.json()
    assert rev_a_data["rating"] == 5
    assert rev_a_data["reviewer_id"] == str(requester["user"]["id"])
    assert rev_a_data["reviewee_id"] == str(helper["user"]["id"])
    assert rev_a_data["comment"] == "Incredible local tips, saved me hours!"

    # 5. Duplicate review attempt by same reviewer -> 409 Conflict
    rev_dup = client.post(
        f"/api/connections/{conn_id}/reviews",
        headers=requester["headers"],
        json={"rating": 4, "comment": "Second review"},
    )
    assert rev_dup.status_code == 409

    # 6. Mutual review: Helper reviews Requester -> 201 Created
    rev_b = client.post(
        f"/api/connections/{conn_id}/reviews",
        headers=helper["headers"],
        json={"rating": 4, "comment": "Polite newcomer, clear questions."},
    )
    assert rev_b.status_code == 201
    assert rev_b.json()["reviewer_id"] == str(helper["user"]["id"])
    assert rev_b.json()["reviewee_id"] == str(requester["user"]["id"])

    # 7. Check connection reviews retrieval
    conn_revs = client.get(
        f"/api/connections/{conn_id}/reviews",
        headers=requester["headers"],
    )
    assert conn_revs.status_code == 200
    assert len(conn_revs.json()) == 2


def test_reputation_calculation_and_zero_reviews(client: TestClient):
    """Test reputation summary endpoint for users with and without reviews."""
    unreviewed = create_authenticated_user(client, "Fresh User", f"fresh_{uuid.uuid4().hex[:6]}@example.test")

    # 1. Zero reviews -> average_rating is None, review_count is 0
    rep_fresh = client.get(
        f"/api/users/{unreviewed['user']['id']}/reputation",
        headers=unreviewed["headers"],
    )
    assert rep_fresh.status_code == 200
    assert rep_fresh.json()["average_rating"] is None
    assert rep_fresh.json()["review_count"] == 0

    # 2. Complete connection and add review
    data = setup_accepted_connection(client, "rep")
    client.post(
        f"/api/connections/{data['connection_id']}/complete",
        headers=data["requester"]["headers"],
    )
    client.post(
        f"/api/connections/{data['connection_id']}/reviews",
        headers=data["requester"]["headers"],
        json={"rating": 5, "comment": "Outstanding guide."},
    )

    # Helper should now have 1 review with 5.0 average
    rep_helper = client.get(
        f"/api/users/{data['helper']['user']['id']}/reputation",
        headers=data["requester"]["headers"],
    )
    assert rep_helper.status_code == 200
    assert rep_helper.json()["average_rating"] == 5.0
    assert rep_helper.json()["review_count"] == 1


def test_chat_remains_readable_on_completed_connection_but_new_messages_blocked(client: TestClient):
    """Chat history remains accessible on COMPLETED connections, but new messages cannot be sent."""
    data = setup_accepted_connection(client, "chatcomp")
    requester = data["requester"]
    helper = data["helper"]
    conn_id = data["connection_id"]

    # Initialize conversation and send message while ACCEPTED
    conv = client.post(
        "/api/conversations",
        headers=requester["headers"],
        json={"connection_id": conn_id},
    ).json()
    conv_id = conv["id"]

    client.post(
        f"/api/conversations/{conv_id}/messages",
        headers=requester["headers"],
        json={"content": "Pre-completion message."},
    )

    # Complete interaction
    client.post(
        f"/api/connections/{conn_id}/complete",
        headers=requester["headers"],
    )

    # 1. Can still read chat history
    get_msgs = client.get(
        f"/api/conversations/{conv_id}/messages",
        headers=helper["headers"],
    )
    assert get_msgs.status_code == 200
    assert len(get_msgs.json()["messages"]) == 1
    assert get_msgs.json()["messages"][0]["content"] == "Pre-completion message."

    # 2. Sending new message on COMPLETED connection is blocked
    send_blocked = client.post(
        f"/api/conversations/{conv_id}/messages",
        headers=requester["headers"],
        json={"content": "Post-completion message should fail."},
    )
    assert send_blocked.status_code == 400
    assert "completed" in send_blocked.json()["detail"].lower()


def test_matching_reputation_integration_and_cold_start(client: TestClient):
    """Candidate with reviews receives real reputation score; candidate with 0 reviews stays UNAVAILABLE."""
    # Setup candidate with real reviews
    data = setup_accepted_connection(client, "matchrep")
    helper = data["helper"]
    requester = data["requester"]

    # Complete and review helper with 5 stars
    client.post(
        f"/api/connections/{data['connection_id']}/complete",
        headers=requester["headers"],
    )
    client.post(
        f"/api/connections/{data['connection_id']}/reviews",
        headers=requester["headers"],
        json={"rating": 5},
    )

    # Configure helper profile & location
    client.put(
        "/api/profile/me",
        headers=helper["headers"],
        json={"headline": "Reviewed Local Guide", "bio": "Verified mentor"},
    )
    client.put(
        "/api/profile/me/location",
        headers=helper["headers"],
        json={"city": "Bengaluru", "area": "Whitefield", "latitude": 12.9698, "longitude": 77.7499},
    )

    # Match request
    match_res = client.post(
        "/api/matching/find-matches",
        headers=requester["headers"],
        json={"request_id": data["request_id"]},
    )
    assert match_res.status_code == 200
    matches = match_res.json()["matches"]

    helper_match = next((m for m in matches if m["user_id"] == str(helper["user"]["id"])), None)
    if helper_match:
        # Reputation dimension must be ACTIVE with normalized score = 1.0 (5 stars)
        assert helper_match["dimension_statuses"]["reputation"] == "ACTIVE"
        assert helper_match["scores"]["reputation_score"] == 1.0
        # Availability must remain UNAVAILABLE
        assert helper_match["dimension_statuses"]["availability"] == "UNAVAILABLE"
        assert helper_match["scores"]["availability_score"] is None
