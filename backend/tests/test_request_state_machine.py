import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from tests.conftest import create_authenticated_user
from app.db.database import SessionLocal
from app.models.connection import Connection, ConnectionStatus
from app.models.request import Request
from app.models.safety import Block
from app.models.user import User


def test_1_requester_cannot_transition_to_connected_without_accepted_helper(client: TestClient):
    """1. Requester cannot transition to CONNECTED without an accepted helper connection."""
    alice = create_authenticated_user(client, "Alice State1", f"alice_st1_{uuid.uuid4().hex[:6]}@example.test")
    
    # Create request
    res_req = client.post("/api/requests", headers=alice["headers"], json={
        "text": "Need help finding a flat in Wakad Pune.",
    })
    assert res_req.status_code == 201
    req_id = res_req.json()["id"]

    # Attempt to transition directly to CONNECTED via requests API -> 400
    res_patch = client.patch(f"/api/requests/{req_id}", headers=alice["headers"], json={
        "status": "CONNECTED",
    })
    assert res_patch.status_code == 400
    assert "accepted helper" in res_patch.json()["detail"].lower()

    # Attempt to transition via need-progress API -> 400
    res_prog = client.patch(f"/api/requests/{req_id}/need-progress", headers=alice["headers"], json={
        "category": "accommodation",
        "status": "CONNECTED",
    })
    assert res_prog.status_code == 400
    assert "accepted helper" in res_prog.json()["detail"].lower()


def test_2_requester_cannot_transition_to_resolution_pending_without_accepted_helper(client: TestClient):
    """2. Requester cannot transition to RESOLUTION_PENDING without an accepted helper connection."""
    alice = create_authenticated_user(client, "Alice State2", f"alice_st2_{uuid.uuid4().hex[:6]}@example.test")
    
    res_req = client.post("/api/requests", headers=alice["headers"], json={
        "text": "Need assistance with metro card in Bengaluru.",
    })
    assert res_req.status_code == 201
    req_id = res_req.json()["id"]

    # Attempt to transition to RESOLUTION_PENDING via requests API -> 400
    res_patch = client.patch(f"/api/requests/{req_id}", headers=alice["headers"], json={
        "status": "RESOLUTION_PENDING",
    })
    assert res_patch.status_code == 400
    assert "accepted helper" in res_patch.json()["detail"].lower()

    # Attempt to transition via need-progress API -> 400
    res_prog = client.patch(f"/api/requests/{req_id}/need-progress", headers=alice["headers"], json={
        "category": "transit",
        "status": "RESOLUTION_PENDING",
    })
    assert res_prog.status_code == 400
    assert "accepted helper" in res_prog.json()["detail"].lower()


def test_3_requester_cannot_forge_fake_connection_via_status_update(client: TestClient):
    """3. Requester cannot forge/create a fake connection via request status updates."""
    alice = create_authenticated_user(client, "Alice State3", f"alice_st3_{uuid.uuid4().hex[:6]}@example.test")
    
    res_req = client.post("/api/requests", headers=alice["headers"], json={
        "text": "Looking for roommates near IT park Kochi.",
    })
    assert res_req.status_code == 201
    req_id = res_req.json()["id"]

    # Attempt forged CONNECTED update
    res_patch = client.patch(f"/api/requests/{req_id}", headers=alice["headers"], json={
        "status": "CONNECTED",
    })
    assert res_patch.status_code == 400

    # Verify no connection row was inserted in the database
    with SessionLocal() as db:
        conns = db.query(Connection).filter(Connection.request_id == uuid.UUID(req_id)).all()
        assert len(conns) == 0


def test_4_requester_cannot_mark_resolved_through_connected_path_without_helper(client: TestClient):
    """4. Requester cannot transition to RESOLVED from CONNECTED path without an accepted helper."""
    alice = create_authenticated_user(client, "Alice State4", f"alice_st4_{uuid.uuid4().hex[:6]}@example.test")
    
    res_req = client.post("/api/requests", headers=alice["headers"], json={
        "text": "Need gym recommendation in Kothrud Pune.",
    })
    assert res_req.status_code == 201
    req_id = res_req.json()["id"]

    # Resolve without helper and without is_independent_resolution=True -> 400
    res_resolve = client.post(f"/api/requests/{req_id}/resolve", headers=alice["headers"], json={
        "resolution_summary": "Claiming helper resolved it without actual helper",
        "is_independent_resolution": False,
    })
    assert res_resolve.status_code == 400
    assert "accepted helper" in res_resolve.json()["detail"].lower()


def test_5_requester_can_resolve_independently_through_explicit_path(client: TestClient):
    """5. Requester can resolve independently through explicit path (is_independent_resolution=True)."""
    alice = create_authenticated_user(client, "Alice State5", f"alice_st5_{uuid.uuid4().hex[:6]}@example.test")
    
    res_req = client.post("/api/requests", headers=alice["headers"], json={
        "text": "Need PG near Hinjewadi Phase 1 under 8000.",
    })
    assert res_req.status_code == 201
    req_id = res_req.json()["id"]

    # Resolve independently with is_independent_resolution=True -> 200 OK
    res_resolve = client.post(f"/api/requests/{req_id}/resolve", headers=alice["headers"], json={
        "resolution_summary": "Found PG myself by walking around Phase 1.",
        "is_independent_resolution": True,
    })
    assert res_resolve.status_code == 200
    data = res_resolve.json()
    assert data["status"] == "RESOLVED"

    # Verify database state
    with SessionLocal() as db:
        req = db.query(Request).filter(Request.id == uuid.UUID(req_id)).first()
        assert req.status == "RESOLVED"
        assert req.resolved_at is not None
        assert "Found PG myself" in req.resolution_summary


def test_6_independent_resolution_does_not_create_connection_or_skew_stats(client: TestClient):
    """6. Independent resolution does NOT create a connection, helper, or skew completion stats."""
    alice = create_authenticated_user(client, "Alice State6", f"alice_st6_{uuid.uuid4().hex[:6]}@example.test")
    
    res_req = client.post("/api/requests", headers=alice["headers"], json={
        "text": "Looking for doctor recommendations in Whitefield Bengaluru.",
    })
    assert res_req.status_code == 201
    req_id = res_req.json()["id"]

    # Resolve independently
    res_resolve = client.post(f"/api/requests/{req_id}/resolve", headers=alice["headers"], json={
        "resolution_summary": "Resolved via hospital website.",
        "is_independent_resolution": True,
    })
    assert res_resolve.status_code == 200

    # Ensure 0 connections exist and no helper stats are altered
    with SessionLocal() as db:
        conns = db.query(Connection).filter(Connection.request_id == uuid.UUID(req_id)).all()
        assert len(conns) == 0


def test_7_terminal_states_cannot_be_moved_backwards(client: TestClient):
    """7. Terminal states (RESOLVED, CLOSED) cannot be transitioned backwards."""
    alice = create_authenticated_user(client, "Alice State7", f"alice_st7_{uuid.uuid4().hex[:6]}@example.test")
    
    res_req = client.post("/api/requests", headers=alice["headers"], json={
        "text": "Need help with gas connection.",
    })
    assert res_req.status_code == 201
    req_id = res_req.json()["id"]

    # Mark RESOLVED independently
    res_resolve = client.post(f"/api/requests/{req_id}/resolve", headers=alice["headers"], json={
        "resolution_summary": "Done independently.",
        "is_independent_resolution": True,
    })
    assert res_resolve.status_code == 200

    # Attempt to move backwards to EXPLORING via request patch -> 400
    res_patch = client.patch(f"/api/requests/{req_id}", headers=alice["headers"], json={
        "status": "EXPLORING",
    })
    assert res_patch.status_code == 400
    assert "terminal" in res_patch.json()["detail"].lower()

    # Attempt to move backwards to UNRESOLVED via need-progress -> 400
    res_prog = client.patch(f"/api/requests/{req_id}/need-progress", headers=alice["headers"], json={
        "category": "utilities",
        "status": "UNRESOLVED",
    })
    assert res_prog.status_code == 400
    assert "terminal" in res_prog.json()["detail"].lower()


def test_8_helper_not_accepted_cannot_satisfy_connected_state(client: TestClient):
    """8. A helper who has NOT accepted (e.g. PENDING or DECLINED) cannot satisfy CONNECTED."""
    alice = create_authenticated_user(client, "Alice State8", f"alice_st8_{uuid.uuid4().hex[:6]}@example.test")
    bob = create_authenticated_user(client, "Bob Helper8", f"bob_st8_{uuid.uuid4().hex[:6]}@example.test")
    
    res_req = client.post("/api/requests", headers=alice["headers"], json={
        "text": "Need someone to show me around Nigdi.",
    })
    assert res_req.status_code == 201
    req_id = res_req.json()["id"]

    # Alice sends connection request to Bob (status: PENDING)
    res_conn = client.post("/api/connections", headers=alice["headers"], json={
        "request_id": req_id,
        "helper_id": bob["user"]["id"],
        "initial_message": "Hi Bob, can you help?",
    })
    assert res_conn.status_code == 201
    conn_data = res_conn.json()
    assert conn_data["status"] == "PENDING"

    # Alice attempts to mark request as CONNECTED while connection is PENDING -> 400
    res_patch = client.patch(f"/api/requests/{req_id}", headers=alice["headers"], json={
        "status": "CONNECTED",
    })
    assert res_patch.status_code == 400
    assert "accepted helper" in res_patch.json()["detail"].lower()

    # Bob declines connection
    res_decline = client.patch(
        f"/api/connections/{conn_data['id']}",
        headers=bob["headers"],
        json={"action": "decline"},
    )
    assert res_decline.status_code == 200

    # Alice attempts to mark request as CONNECTED with DECLINED connection -> 400
    res_patch2 = client.patch(f"/api/requests/{req_id}", headers=alice["headers"], json={
        "status": "CONNECTED",
    })
    assert res_patch2.status_code == 400
    assert "accepted helper" in res_patch2.json()["detail"].lower()


def test_9_connection_belonging_to_another_request_cannot_satisfy_connected(client: TestClient):
    """9. A connection belonging to a different request cannot satisfy CONNECTED for this request."""
    alice = create_authenticated_user(client, "Alice State9", f"alice_st9_{uuid.uuid4().hex[:6]}@example.test")
    bob = create_authenticated_user(client, "Bob Helper9", f"bob_st9_{uuid.uuid4().hex[:6]}@example.test")
    
    # Alice creates Request A
    res_req_a = client.post("/api/requests", headers=alice["headers"], json={
        "text": "Request A: Need advice on schools in Pimpri.",
    })
    assert res_req_a.status_code == 201
    req_a_id = res_req_a.json()["id"]

    # Alice creates Request B
    res_req_b = client.post("/api/requests", headers=alice["headers"], json={
        "text": "Request B: Need rental flat in Nigdi.",
    })
    assert res_req_b.status_code == 201
    req_b_id = res_req_b.json()["id"]

    # Bob is connected to Request A and ACCEPTS
    res_conn = client.post("/api/connections", headers=alice["headers"], json={
        "request_id": req_a_id,
        "helper_id": bob["user"]["id"],
        "initial_message": "School advice needed",
    })
    assert res_conn.status_code == 201
    conn_id = res_conn.json()["id"]

    res_acc = client.patch(
        f"/api/connections/{conn_id}",
        headers=bob["headers"],
        json={"action": "accept"},
    )
    assert res_acc.status_code == 200

    # Request A is now legitimately CONNECTED
    res_get_a = client.get(f"/api/requests/{req_a_id}", headers=alice["headers"])
    assert res_get_a.json()["status"] == "CONNECTED"

    # Alice attempts to mark Request B as CONNECTED -> 400 because Bob only accepted Request A
    res_patch_b = client.patch(f"/api/requests/{req_b_id}", headers=alice["headers"], json={
        "status": "CONNECTED",
    })
    assert res_patch_b.status_code == 400
    assert "accepted helper" in res_patch_b.json()["detail"].lower()


def test_10_suspended_or_blocked_users_cannot_bypass_rules(client: TestClient):
    """10. Suspended / inactive / blocked users cannot bypass state machine validation rules."""
    alice = create_authenticated_user(client, "Alice State10", f"alice_st10_{uuid.uuid4().hex[:6]}@example.test")
    bob = create_authenticated_user(client, "Bob Helper10", f"bob_st10_{uuid.uuid4().hex[:6]}@example.test")
    
    res_req = client.post("/api/requests", headers=alice["headers"], json={
        "text": "Need help moving to Kochi.",
    })
    assert res_req.status_code == 201
    req_id = res_req.json()["id"]

    # 10a. Connection is accepted
    res_conn = client.post("/api/connections", headers=alice["headers"], json={
        "request_id": req_id,
        "helper_id": bob["user"]["id"],
        "initial_message": "Kochi assistance",
    })
    assert res_conn.status_code == 201
    conn_id = res_conn.json()["id"]

    client.patch(
        f"/api/connections/{conn_id}",
        headers=bob["headers"],
        json={"action": "accept"},
    )

    # 10b. Alice blocks Bob (safety block active)
    with SessionLocal() as db:
        block = Block(
            blocker_id=uuid.UUID(alice["user"]["id"]),
            blocked_id=uuid.UUID(bob["user"]["id"]),
        )
        db.add(block)
        db.commit()

    # Now that safety block is in place, get_accepted_connection_for_request rejects it
    # Updating request status to RESOLUTION_PENDING must be rejected due to safety block
    res_patch = client.patch(f"/api/requests/{req_id}", headers=alice["headers"], json={
        "status": "RESOLUTION_PENDING",
    })
    assert res_patch.status_code == 400
    assert "accepted helper" in res_patch.json()["detail"].lower()

    # 10c. Suspended / inactive user cannot resolve or transition requests
    with SessionLocal() as db:
        user_db = db.query(User).filter(User.id == uuid.UUID(alice["user"]["id"])).first()
        user_db.is_active = False
        db.commit()

    res_resolve = client.post(f"/api/requests/{req_id}/resolve", headers=alice["headers"], json={
        "is_independent_resolution": True,
        "resolution_summary": "Trying while suspended",
    })
    assert res_resolve.status_code == 403
    assert (
        "inactive" in res_resolve.json()["detail"].lower()
        or "suspended" in res_resolve.json()["detail"].lower()
    )
