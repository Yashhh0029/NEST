import uuid
import pytest
from fastapi.testclient import TestClient
from tests.conftest import create_authenticated_user


def test_connection_endpoints_require_authentication(client: TestClient):
    """Unauthenticated requests must be rejected with 401."""
    resp = client.post("/api/connections", json={
        "request_id": str(uuid.uuid4()),
        "helper_id": str(uuid.uuid4()),
    })
    assert resp.status_code == 401

    resp_list = client.get("/api/connections")
    assert resp_list.status_code == 401


def test_requester_cannot_connect_to_self(client: TestClient):
    """A user cannot create a connection to themselves."""
    user = create_authenticated_user(client, "Self User", "self_conn@example.test")
    req_resp = client.post(
        "/api/requests",
        headers=user["headers"],
        json={"text": "Need help in Koramangala Bengaluru"},
    )
    req_id = req_resp.json()["id"]

    resp = client.post(
        "/api/connections",
        headers=user["headers"],
        json={"request_id": req_id, "helper_id": str(user["user"]["id"])},
    )
    assert resp.status_code == 400
    assert "yourself" in resp.json()["detail"].lower()


def test_cannot_connect_for_other_users_request(client: TestClient):
    """A user cannot initiate connections for requests they do not own."""
    user_a = create_authenticated_user(client, "User A", "owner_req@example.test")
    user_b = create_authenticated_user(client, "User B", "other_req@example.test")
    helper = create_authenticated_user(client, "Helper", "helper_other@example.test")

    # User A creates request
    req_resp = client.post(
        "/api/requests",
        headers=user_a["headers"],
        json={"text": "Moving to Pune for new job"},
    )
    req_id = req_resp.json()["id"]

    # User B tries to connect helper to User A's request
    resp = client.post(
        "/api/connections",
        headers=user_b["headers"],
        json={"request_id": req_id, "helper_id": str(helper["user"]["id"])},
    )
    assert resp.status_code == 403


def test_full_connection_lifecycle(client: TestClient):
    """
    Test complete lifecycle:
    1. Requester creates request
    2. Requester sends connection request to helper -> PENDING
    3. Helper views incoming connection
    4. Helper accepts connection -> ACCEPTED with timestamp
    5. Requester and helper can view active connection
    """
    requester = create_authenticated_user(client, "Newcomer Life", "newcomer_life@example.test")
    helper = create_authenticated_user(client, "Helper Life", "helper_life@example.test")

    # Requester creates request
    req_resp = client.post(
        "/api/requests",
        headers=requester["headers"],
        json={"text": "Looking for PG near Indiranagar, Bengaluru"},
    )
    req_id = req_resp.json()["id"]

    # Requester sends connection
    conn_resp = client.post(
        "/api/connections",
        headers=requester["headers"],
        json={
            "request_id": req_id,
            "helper_id": str(helper["user"]["id"]),
            "initial_message": "Hi, saw your profile! Would appreciate guidance on PGs in Indiranagar.",
        },
    )
    assert conn_resp.status_code == 201
    conn_data = conn_resp.json()
    conn_id = conn_data["id"]
    assert conn_data["status"] == "PENDING"
    assert conn_data["requester_id"] == str(requester["user"]["id"])
    assert conn_data["helper_id"] == str(helper["user"]["id"])
    assert conn_data["initial_message"] is not None

    # Helper lists incoming connections
    helper_list = client.get("/api/connections?role=helper", headers=helper["headers"])
    assert helper_list.status_code == 200
    h_conns = helper_list.json()["connections"]
    assert any(c["id"] == conn_id for c in h_conns)

    # Helper accepts connection
    accept_resp = client.patch(
        f"/api/connections/{conn_id}",
        headers=helper["headers"],
        json={"action": "accept"},
    )
    assert accept_resp.status_code == 200
    accepted_data = accept_resp.json()
    assert accepted_data["status"] == "ACCEPTED"
    assert accepted_data["accepted_at"] is not None
    assert accepted_data["declined_at"] is None

    # Verify both parties can view the single connection
    get_req = client.get(f"/api/connections/{conn_id}", headers=requester["headers"])
    assert get_req.status_code == 200
    assert get_req.json()["status"] == "ACCEPTED"

    get_hlp = client.get(f"/api/connections/{conn_id}", headers=helper["headers"])
    assert get_hlp.status_code == 200
    assert get_hlp.json()["status"] == "ACCEPTED"


def test_helper_can_decline_connection(client: TestClient):
    """Helper can decline connection request."""
    requester = create_authenticated_user(client, "Req Decline", "req_dec@example.test")
    helper = create_authenticated_user(client, "Help Decline", "hlp_dec@example.test")

    req_resp = client.post(
        "/api/requests",
        headers=requester["headers"],
        json={"text": "Need roommate near Baner Pune"},
    )
    req_id = req_resp.json()["id"]

    conn_resp = client.post(
        "/api/connections",
        headers=requester["headers"],
        json={"request_id": req_id, "helper_id": str(helper["user"]["id"])},
    )
    conn_id = conn_resp.json()["id"]

    # Helper declines
    dec_resp = client.patch(
        f"/api/connections/{conn_id}",
        headers=helper["headers"],
        json={"action": "decline"},
    )
    assert dec_resp.status_code == 200
    assert dec_resp.json()["status"] == "DECLINED"
    assert dec_resp.json()["declined_at"] is not None


def test_requester_can_cancel_connection(client: TestClient):
    """Requester can cancel outgoing connection request."""
    requester = create_authenticated_user(client, "Req Cancel", "req_canc@example.test")
    helper = create_authenticated_user(client, "Help Cancel", "hlp_canc@example.test")

    req_resp = client.post(
        "/api/requests",
        headers=requester["headers"],
        json={"text": "Need advice on Whitefield commute"},
    )
    req_id = req_resp.json()["id"]

    conn_resp = client.post(
        "/api/connections",
        headers=requester["headers"],
        json={"request_id": req_id, "helper_id": str(helper["user"]["id"])},
    )
    conn_id = conn_resp.json()["id"]

    # Requester cancels
    canc_resp = client.patch(
        f"/api/connections/{conn_id}",
        headers=requester["headers"],
        json={"action": "cancel"},
    )
    assert canc_resp.status_code == 200
    assert canc_resp.json()["status"] == "CANCELLED"


def test_duplicate_connection_prevention(client: TestClient):
    """Cannot create duplicate active/pending connections for the same request and helper."""
    requester = create_authenticated_user(client, "Req Dup", "req_dup@example.test")
    helper = create_authenticated_user(client, "Help Dup", "hlp_dup@example.test")

    req_resp = client.post(
        "/api/requests",
        headers=requester["headers"],
        json={"text": "Need housing help in HSR Layout"},
    )
    req_id = req_resp.json()["id"]

    first = client.post(
        "/api/connections",
        headers=requester["headers"],
        json={"request_id": req_id, "helper_id": str(helper["user"]["id"])},
    )
    assert first.status_code == 201

    # Second attempt should return 409 Conflict
    dup = client.post(
        "/api/connections",
        headers=requester["headers"],
        json={"request_id": req_id, "helper_id": str(helper["user"]["id"])},
    )
    assert dup.status_code == 409
    assert "already exists" in dup.json()["detail"].lower()


def test_unauthorized_user_cannot_modify_or_view(client: TestClient):
    """Third-party user cannot view or modify connections."""
    requester = create_authenticated_user(client, "Req Auth", "req_auth@example.test")
    helper = create_authenticated_user(client, "Help Auth", "hlp_auth@example.test")
    intruder = create_authenticated_user(client, "Intruder", "intruder@example.test")

    req_resp = client.post(
        "/api/requests",
        headers=requester["headers"],
        json={"text": "Need housing guidance"},
    )
    req_id = req_resp.json()["id"]

    conn = client.post(
        "/api/connections",
        headers=requester["headers"],
        json={"request_id": req_id, "helper_id": str(helper["user"]["id"])},
    ).json()

    # Intruder tries to view
    view_resp = client.get(f"/api/connections/{conn['id']}", headers=intruder["headers"])
    assert view_resp.status_code == 403

    # Intruder tries to accept
    mod_resp = client.patch(
        f"/api/connections/{conn['id']}",
        headers=intruder["headers"],
        json={"action": "accept"},
    )
    assert mod_resp.status_code == 403


def test_cannot_accept_already_accepted_connection(client: TestClient):
    """Cannot accept an already accepted connection."""
    requester = create_authenticated_user(client, "Req Double", "req_double@example.test")
    helper = create_authenticated_user(client, "Help Double", "hlp_double@example.test")

    req_resp = client.post(
        "/api/requests",
        headers=requester["headers"],
        json={"text": "Moving assistance"},
    )
    req_id = req_resp.json()["id"]

    conn = client.post(
        "/api/connections",
        headers=requester["headers"],
        json={"request_id": req_id, "helper_id": str(helper["user"]["id"])},
    ).json()

    # Helper accepts
    client.patch(f"/api/connections/{conn['id']}", headers=helper["headers"], json={"action": "accept"})

    # Helper tries to accept again
    re_accept = client.patch(f"/api/connections/{conn['id']}", headers=helper["headers"], json={"action": "accept"})
    assert re_accept.status_code == 400
    assert "already accepted" in re_accept.json()["detail"].lower()


def test_nonexistent_connection_returns_404(client: TestClient):
    """Nonexistent connection IDs return 404."""
    user = create_authenticated_user(client, "Any User", "any_user@example.test")
    fake_id = str(uuid.uuid4())

    resp = client.get(f"/api/connections/{fake_id}", headers=user["headers"])
    assert resp.status_code == 404

    resp_patch = client.patch(f"/api/connections/{fake_id}", headers=user["headers"], json={"action": "accept"})
    assert resp_patch.status_code == 404


def test_reactivate_completed_connection_by_finder_and_helper(client: TestClient):
    """
    Finder or Helper can reactivate a completed connection.
    Both users can message each other again and history is preserved.
    """
    finder = create_authenticated_user(client, "Finder User", "finder_react@example.test")
    helper = create_authenticated_user(client, "Helper User", "helper_react@example.test")

    # 1. Create request & connection
    req_resp = client.post(
        "/api/requests",
        headers=finder["headers"],
        json={"text": "Looking for advice in Baner Pune"},
    )
    req_id = req_resp.json()["id"]

    conn_resp = client.post(
        "/api/connections",
        headers=finder["headers"],
        json={"request_id": req_id, "helper_id": str(helper["user"]["id"])},
    )
    conn_id = conn_resp.json()["id"]

    # 2. Accept connection
    client.patch(
        f"/api/connections/{conn_id}",
        headers=helper["headers"],
        json={"action": "accept"},
    )

    # 3. Create conversation and send first message
    conv_resp = client.post(
        "/api/conversations",
        headers=finder["headers"],
        json={"connection_id": conn_id},
    )
    conv_id = conv_resp.json()["id"]

    msg1_resp = client.post(
        f"/api/conversations/{conv_id}/messages",
        headers=finder["headers"],
        json={"content": "Hello helper, need some local tips!"},
    )
    assert msg1_resp.status_code == 201
    msg1_id = msg1_resp.json()["id"]

    # 4. Mark completed
    complete_resp = client.post(
        f"/api/connections/{conn_id}/complete",
        headers=finder["headers"],
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json()["status"] == "COMPLETED"

    # 5. Verify messaging is blocked while COMPLETED
    blocked_msg = client.post(
        f"/api/conversations/{conv_id}/messages",
        headers=helper["headers"],
        json={"content": "Can I still reply?"},
    )
    assert blocked_msg.status_code == 400
    assert "completed" in blocked_msg.json()["detail"].lower()

    # 6. Reactivate conversation via POST /api/connections/{id}/reactivate
    reactivate_resp = client.post(
        f"/api/connections/{conn_id}/reactivate",
        headers=helper["headers"],
    )
    assert reactivate_resp.status_code == 200
    assert reactivate_resp.json()["status"] == "ACCEPTED"

    # 7. Verify messages can be sent again by both users
    msg2_resp = client.post(
        f"/api/conversations/{conv_id}/messages",
        headers=helper["headers"],
        json={"content": "Reactivated! Happy to help further."},
    )
    assert msg2_resp.status_code == 201

    msg3_resp = client.post(
        f"/api/conversations/{conv_id}/messages",
        headers=finder["headers"],
        json={"content": "Awesome, thanks!"},
    )
    assert msg3_resp.status_code == 201

    # 8. Verify message history remains fully intact
    msgs = client.get(
        f"/api/conversations/{conv_id}/messages",
        headers=finder["headers"],
    ).json()["messages"]
    msg_ids = [m["id"] for m in msgs]
    assert msg1_id in msg_ids
    assert msg2_resp.json()["id"] in msg_ids
    assert msg3_resp.json()["id"] in msg_ids


def test_reactivate_blocked_connection_forbidden(client: TestClient):
    """Reactivation is forbidden if either user blocked the other."""
    finder = create_authenticated_user(client, "BlockFinder", "block_finder@example.test")
    helper = create_authenticated_user(client, "BlockHelper", "block_helper@example.test")

    req_resp = client.post(
        "/api/requests",
        headers=finder["headers"],
        json={"text": "Help in Indiranagar Bengaluru"},
    )
    conn_resp = client.post(
        "/api/connections",
        headers=finder["headers"],
        json={"request_id": req_resp.json()["id"], "helper_id": str(helper["user"]["id"])},
    )
    conn_id = conn_resp.json()["id"]

    client.patch(f"/api/connections/{conn_id}", headers=helper["headers"], json={"action": "accept"})
    client.post(f"/api/connections/{conn_id}/complete", headers=finder["headers"])

    # Finder blocks helper
    block_resp = client.post(
        f"/api/blocks/{helper['user']['id']}",
        headers=finder["headers"],
    )
    assert block_resp.status_code == 201

    # Attempt reactivate should be rejected with 403
    react_resp = client.post(
        f"/api/connections/{conn_id}/reactivate",
        headers=finder["headers"],
    )
    assert react_resp.status_code == 403
    assert "safety restrictions" in react_resp.json()["detail"].lower()


def test_reactivate_non_completed_connection_rejected(client: TestClient):
    """Only COMPLETED connections can be reactivated."""
    user_a = create_authenticated_user(client, "User AA", "user_aa@example.test")
    user_b = create_authenticated_user(client, "User BB", "user_bb@example.test")

    req_resp = client.post(
        "/api/requests",
        headers=user_a["headers"],
        json={"text": "Need help in Aundh Pune"},
    )
    conn_resp = client.post(
        "/api/connections",
        headers=user_a["headers"],
        json={"request_id": req_resp.json()["id"], "helper_id": str(user_b["user"]["id"])},
    )
    conn_id = conn_resp.json()["id"]

    # Try to reactivate while PENDING
    react_resp = client.post(
        f"/api/connections/{conn_id}/reactivate",
        headers=user_a["headers"],
    )
    assert react_resp.status_code == 400
    assert "completed" in react_resp.json()["detail"].lower()


def test_reactivate_safety_restricted_connection_forbidden(client: TestClient):
    """Reactivation is forbidden if connection is flagged/restricted by safety report."""
    finder = create_authenticated_user(client, "SafetyFinder", "safe_finder@example.test")
    helper = create_authenticated_user(client, "SafetyHelper", "safe_helper@example.test")

    req_resp = client.post(
        "/api/requests",
        headers=finder["headers"],
        json={"text": "Help in Whitefield Bengaluru"},
    )
    conn_resp = client.post(
        "/api/connections",
        headers=finder["headers"],
        json={"request_id": req_resp.json()["id"], "helper_id": str(helper["user"]["id"])},
    )
    conn_id = conn_resp.json()["id"]

    client.patch(f"/api/connections/{conn_id}", headers=helper["headers"], json={"action": "accept"})
    client.post(f"/api/connections/{conn_id}/complete", headers=finder["headers"])

    # Finder reports helper with connection_id
    rep_resp = client.post(
        "/api/reports",
        headers=finder["headers"],
        json={
            "reported_user_id": str(helper["user"]["id"]),
            "connection_id": conn_id,
            "reason": "HARASSMENT",
            "description": "Inappropriate interaction conduct",
        },
    )
    assert rep_resp.status_code == 201

    # Reactivate fails with 403
    react_resp = client.post(
        f"/api/connections/{conn_id}/reactivate",
        headers=finder["headers"],
    )
    assert react_resp.status_code == 403
    assert "safety" in react_resp.json()["detail"].lower() and "restrictions" in react_resp.json()["detail"].lower()


def test_reactivate_unauthorized_user_forbidden(client: TestClient):
    """An outsider cannot reactivate another user's connection."""
    finder = create_authenticated_user(client, "User 1", "u1@example.test")
    helper = create_authenticated_user(client, "User 2", "u2@example.test")
    outsider = create_authenticated_user(client, "User 3", "u3@example.test")

    req_resp = client.post(
        "/api/requests",
        headers=finder["headers"],
        json={"text": "Help in Viman Nagar"},
    )
    conn_resp = client.post(
        "/api/connections",
        headers=finder["headers"],
        json={"request_id": req_resp.json()["id"], "helper_id": str(helper["user"]["id"])},
    )
    conn_id = conn_resp.json()["id"]

    client.patch(f"/api/connections/{conn_id}", headers=helper["headers"], json={"action": "accept"})
    client.post(f"/api/connections/{conn_id}/complete", headers=finder["headers"])

    # Outsider attempts reactivation
    react_resp = client.post(
        f"/api/connections/{conn_id}/reactivate",
        headers=outsider["headers"],
    )
    assert react_resp.status_code == 403


