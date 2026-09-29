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
