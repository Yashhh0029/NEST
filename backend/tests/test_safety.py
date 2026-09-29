import uuid
import pytest
from fastapi.testclient import TestClient
from tests.conftest import create_authenticated_user


def setup_users_and_connection(client: TestClient, prefix: str = "safety"):
    user_a = create_authenticated_user(
        client, f"{prefix} Alice", f"{prefix}_alice_{uuid.uuid4().hex[:6]}@example.test"
    )
    user_b = create_authenticated_user(
        client, f"{prefix} Bob", f"{prefix}_bob_{uuid.uuid4().hex[:6]}@example.test"
    )

    req_resp = client.post(
        "/api/requests",
        headers=user_a["headers"],
        json={"text": "Moving to Pune near Hinjewadi, need guidance on accommodation."},
    )
    request_id = req_resp.json()["id"]

    conn_resp = client.post(
        "/api/connections",
        headers=user_a["headers"],
        json={
            "request_id": request_id,
            "helper_id": str(user_b["user"]["id"]),
            "initial_message": "Hi Bob, can you help me with Hinjewadi?",
        },
    )
    connection_id = conn_resp.json()["id"]

    # Bob accepts
    client.patch(
        f"/api/connections/{connection_id}",
        headers=user_b["headers"],
        json={"action": "accept"},
    )

    # Alice initializes conversation
    conv_resp = client.post(
        "/api/conversations",
        headers=user_a["headers"],
        json={"connection_id": connection_id},
    )
    conversation_id = conv_resp.json()["id"]

    # Exchange a message
    msg_resp = client.post(
        f"/api/conversations/{conversation_id}/messages",
        headers=user_b["headers"],
        json={"content": "Sure Alice! I know Hinjewadi Phase 1 very well."},
    )
    message_id = msg_resp.json()["id"]

    return {
        "user_a": user_a,
        "user_b": user_b,
        "connection_id": connection_id,
        "conversation_id": conversation_id,
        "message_id": message_id,
        "request_id": request_id,
    }


# ============================================================================
# 1. Blocking Tests
# ============================================================================

def test_self_block_rejected(client: TestClient):
    user = create_authenticated_user(client, "Self Blocker", f"self_{uuid.uuid4().hex[:6]}@example.test")
    resp = client.post(
        f"/api/blocks/{user['user']['id']}",
        headers=user["headers"],
    )
    assert resp.status_code == 400
    assert "cannot block yourself" in resp.json()["detail"].lower()


def test_block_user_and_idempotency(client: TestClient):
    alice = create_authenticated_user(client, "Alice", f"a_{uuid.uuid4().hex[:6]}@example.test")
    bob = create_authenticated_user(client, "Bob", f"b_{uuid.uuid4().hex[:6]}@example.test")

    # First block -> 201 Created
    resp = client.post(f"/api/blocks/{bob['user']['id']}", headers=alice["headers"])
    assert resp.status_code == 201
    data = resp.json()
    assert data["blocker_id"] == str(alice["user"]["id"])
    assert data["blocked_id"] == str(bob["user"]["id"])
    assert data["blocked_user"]["name"] == "Bob"

    # Idempotent second block -> 201 returns existing block
    resp2 = client.post(f"/api/blocks/{bob['user']['id']}", headers=alice["headers"])
    assert resp2.status_code == 201
    assert resp2.json()["id"] == data["id"]


def test_unblock_user(client: TestClient):
    alice = create_authenticated_user(client, "Alice", f"a_{uuid.uuid4().hex[:6]}@example.test")
    bob = create_authenticated_user(client, "Bob", f"b_{uuid.uuid4().hex[:6]}@example.test")

    # Block
    client.post(f"/api/blocks/{bob['user']['id']}", headers=alice["headers"])

    # Unblock -> 204 No Content
    unblock_resp = client.delete(f"/api/blocks/{bob['user']['id']}", headers=alice["headers"])
    assert unblock_resp.status_code == 204

    # Second unblock -> 404 Not Found
    unblock_again = client.delete(f"/api/blocks/{bob['user']['id']}", headers=alice["headers"])
    assert unblock_again.status_code == 404


def test_cannot_manipulate_other_users_block(client: TestClient):
    alice = create_authenticated_user(client, "Alice", f"a_{uuid.uuid4().hex[:6]}@example.test")
    bob = create_authenticated_user(client, "Bob", f"b_{uuid.uuid4().hex[:6]}@example.test")
    charlie = create_authenticated_user(client, "Charlie", f"c_{uuid.uuid4().hex[:6]}@example.test")

    # Alice blocks Bob
    client.post(f"/api/blocks/{bob['user']['id']}", headers=alice["headers"])

    # Charlie attempts to unblock Bob from Alice's block -> 404 (Charlie has no block on Bob)
    unblock_resp = client.delete(f"/api/blocks/{bob['user']['id']}", headers=charlie["headers"])
    assert unblock_resp.status_code == 404


def test_list_blocks(client: TestClient):
    alice = create_authenticated_user(client, "Alice", f"a_{uuid.uuid4().hex[:6]}@example.test")
    bob = create_authenticated_user(client, "Bob", f"b_{uuid.uuid4().hex[:6]}@example.test")
    charlie = create_authenticated_user(client, "Charlie", f"c_{uuid.uuid4().hex[:6]}@example.test")

    client.post(f"/api/blocks/{bob['user']['id']}", headers=alice["headers"])
    client.post(f"/api/blocks/{charlie['user']['id']}", headers=alice["headers"])

    list_resp = client.get("/api/blocks", headers=alice["headers"])
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["total"] == 2
    blocked_ids = {b["blocked_id"] for b in data["blocks"]}
    assert str(bob["user"]["id"]) in blocked_ids
    assert str(charlie["user"]["id"]) in blocked_ids


# ============================================================================
# 2. Enforcement: Matching, Connections, Chat
# ============================================================================

def test_bidirectional_connection_creation_rejection(client: TestClient):
    alice = create_authenticated_user(client, "Alice", f"a_{uuid.uuid4().hex[:6]}@example.test")
    bob = create_authenticated_user(client, "Bob", f"b_{uuid.uuid4().hex[:6]}@example.test")

    # Alice creates request
    req = client.post(
        "/api/requests",
        headers=alice["headers"],
        json={"text": "Looking for PG in Hinjewadi Phase 1 Pune."},
    ).json()

    # Alice blocks Bob
    client.post(f"/api/blocks/{bob['user']['id']}", headers=alice["headers"])

    # Alice tries to connect to Bob -> 403 Forbidden
    conn_resp1 = client.post(
        "/api/connections",
        headers=alice["headers"],
        json={"request_id": req["id"], "helper_id": str(bob["user"]["id"])},
    )
    assert conn_resp1.status_code == 403
    assert "safety restrictions" in conn_resp1.json()["detail"].lower()

    # Bob creates request and tries to connect to Alice (reverse direction) -> 403 Forbidden
    bob_req = client.post(
        "/api/requests",
        headers=bob["headers"],
        json={"text": "Looking for flatmate in Hinjewadi."},
    ).json()

    conn_resp2 = client.post(
        "/api/connections",
        headers=bob["headers"],
        json={"request_id": bob_req["id"], "helper_id": str(alice["user"]["id"])},
    )
    assert conn_resp2.status_code == 403
    assert "safety restrictions" in conn_resp2.json()["detail"].lower()


def test_bidirectional_chat_rejection_and_history_readability(client: TestClient):
    data = setup_users_and_connection(client, "block_chat")
    alice = data["user_a"]
    bob = data["user_b"]
    conv_id = data["conversation_id"]

    # Prior to block: Bob can send message
    msg_before = client.post(
        f"/api/conversations/{conv_id}/messages",
        headers=bob["headers"],
        json={"content": "Here is some Hinjewadi PG info."},
    )
    assert msg_before.status_code == 201

    # Alice blocks Bob
    block_resp = client.post(f"/api/blocks/{bob['user']['id']}", headers=alice["headers"])
    assert block_resp.status_code == 201

    # 1. New message from Alice to Bob -> 403 Forbidden
    msg_from_alice = client.post(
        f"/api/conversations/{conv_id}/messages",
        headers=alice["headers"],
        json={"content": "Trying to message blocked user."},
    )
    assert msg_from_alice.status_code == 403
    assert "safety restrictions" in msg_from_alice.json()["detail"].lower()

    # 2. New message from Bob to Alice (reverse direction) -> 403 Forbidden
    msg_from_bob = client.post(
        f"/api/conversations/{conv_id}/messages",
        headers=bob["headers"],
        json={"content": "Trying to message user who blocked me."},
    )
    assert msg_from_bob.status_code == 403
    assert "safety restrictions" in msg_from_bob.json()["detail"].lower()

    # 3. New conversation creation -> 403 Forbidden
    new_conv = client.post(
        "/api/conversations",
        headers=alice["headers"],
        json={"connection_id": data["connection_id"]},
    )
    assert new_conv.status_code == 403

    # 4. Existing chat history REMAINS READABLE for both participants
    history_alice = client.get(f"/api/conversations/{conv_id}/messages", headers=alice["headers"])
    assert history_alice.status_code == 200
    assert history_alice.json()["total"] >= 2

    history_bob = client.get(f"/api/conversations/{conv_id}/messages", headers=bob["headers"])
    assert history_bob.status_code == 200
    assert history_bob.json()["total"] >= 2


def test_bidirectional_matching_exclusion(client: TestClient):
    alice = create_authenticated_user(client, "Alice", f"a_{uuid.uuid4().hex[:6]}@example.test")
    bob = create_authenticated_user(client, "Bob", f"b_{uuid.uuid4().hex[:6]}@example.test", role="helper")

    # Set up profile for Bob
    client.post(
        "/api/profile",
        headers=bob["headers"],
        json={
            "headline": "Pune Local Guide",
            "bio": "Expert in Hinjewadi rentals",
            "skills": ["Local Guidance", "Housing"],
            "city": "Pune",
            "area": "Hinjewadi",
        },
    )

    req = client.post(
        "/api/requests",
        headers=alice["headers"],
        json={"text": "Need housing help in Hinjewadi Pune."},
    ).json()

    # Alice blocks Bob
    client.post(f"/api/blocks/{bob['user']['id']}", headers=alice["headers"])

    # 1. Matching query for Alice's request -> Bob MUST NOT be present
    match_resp = client.post(
        "/api/matching/find-matches",
        headers=alice["headers"],
        json={"request_id": req["id"]},
    )
    assert match_resp.status_code == 200
    match_ids = [m["user_id"] for m in match_resp.json()["matches"]]
    assert str(bob["user"]["id"]) not in match_ids

    # 2. Reverse direction: Bob creates request -> Alice MUST NOT be present
    bob_req = client.post(
        "/api/requests",
        headers=bob["headers"],
        json={"text": "Need someone to show me Hinjewadi Phase 1."},
    ).json()

    bob_match_resp = client.post(
        "/api/matching/find-matches",
        headers=bob["headers"],
        json={"request_id": bob_req["id"]},
    )
    assert bob_match_resp.status_code == 200
    bob_match_ids = [m["user_id"] for m in bob_match_resp.json()["matches"]]
    assert str(alice["user"]["id"]) not in bob_match_ids


# ============================================================================
# 3. Reporting Tests
# ============================================================================

def test_self_report_rejected(client: TestClient):
    user = create_authenticated_user(client, "User", f"u_{uuid.uuid4().hex[:6]}@example.test")
    resp = client.post(
        "/api/reports",
        headers=user["headers"],
        json={
            "reported_user_id": str(user["user"]["id"]),
            "reason": "SPAM",
            "description": "Reporting myself",
        },
    )
    assert resp.status_code == 400
    assert "cannot report yourself" in resp.json()["detail"].lower()


def test_valid_user_report(client: TestClient):
    alice = create_authenticated_user(client, "Alice", f"a_{uuid.uuid4().hex[:6]}@example.test")
    bob = create_authenticated_user(client, "Bob", f"b_{uuid.uuid4().hex[:6]}@example.test")

    resp = client.post(
        "/api/reports",
        headers=alice["headers"],
        json={
            "reported_user_id": str(bob["user"]["id"]),
            "reason": "HARASSMENT",
            "description": "Inappropriate and threatening behavior in messages.",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["reporter_id"] == str(alice["user"]["id"])
    assert data["reported_user_id"] == str(bob["user"]["id"])
    assert data["reason"] == "HARASSMENT"
    assert data["status"] == "OPEN"
    assert data["reported_user"]["name"] == "Bob"


def test_valid_message_report(client: TestClient):
    data = setup_users_and_connection(client, "report_msg")
    alice = data["user_a"]
    bob = data["user_b"]
    msg_id = data["message_id"]

    resp = client.post(
        "/api/reports",
        headers=alice["headers"],
        json={
            "reported_user_id": str(bob["user"]["id"]),
            "message_id": msg_id,
            "connection_id": data["connection_id"],
            "reason": "INAPPROPRIATE_CONTENT",
            "description": "This message is offensive.",
        },
    )
    assert resp.status_code == 201
    rep = resp.json()
    assert rep["message_id"] == msg_id
    assert rep["message_snippet"] is not None


def test_unauthorized_message_report_rejected(client: TestClient):
    data = setup_users_and_connection(client, "unauth_msg")
    msg_id = data["message_id"]
    charlie = create_authenticated_user(client, "Charlie", f"c_{uuid.uuid4().hex[:6]}@example.test")

    # Charlie was not participant in Alice and Bob's chat
    resp = client.post(
        "/api/reports",
        headers=charlie["headers"],
        json={
            "reported_user_id": str(data["user_b"]["user"]["id"]),
            "message_id": msg_id,
            "reason": "SCAM",
            "description": "Attempting to snoop and report third-party message.",
        },
    )
    assert resp.status_code == 403
    assert "not part of" in resp.json()["detail"].lower()


def test_duplicate_active_report_throttling(client: TestClient):
    alice = create_authenticated_user(client, "Alice", f"a_{uuid.uuid4().hex[:6]}@example.test")
    bob = create_authenticated_user(client, "Bob", f"b_{uuid.uuid4().hex[:6]}@example.test")

    # First report
    resp1 = client.post(
        "/api/reports",
        headers=alice["headers"],
        json={"reported_user_id": str(bob["user"]["id"]), "reason": "SPAM", "description": "Spam bot"},
    )
    assert resp1.status_code == 201

    # Second identical report while first is OPEN -> 409 Conflict
    resp2 = client.post(
        "/api/reports",
        headers=alice["headers"],
        json={"reported_user_id": str(bob["user"]["id"]), "reason": "SPAM", "description": "Spam bot duplicate"},
    )
    assert resp2.status_code == 409
    assert "already have an active report" in resp2.json()["detail"].lower()


def test_private_report_isolation(client: TestClient):
    alice = create_authenticated_user(client, "Alice", f"a_{uuid.uuid4().hex[:6]}@example.test")
    bob = create_authenticated_user(client, "Bob", f"b_{uuid.uuid4().hex[:6]}@example.test")
    charlie = create_authenticated_user(client, "Charlie", f"c_{uuid.uuid4().hex[:6]}@example.test")

    # Alice reports Bob
    rep = client.post(
        "/api/reports",
        headers=alice["headers"],
        json={"reported_user_id": str(bob["user"]["id"]), "reason": "SAFETY_CONCERN"},
    ).json()

    # Alice can view own report
    own_resp = client.get(f"/api/reports/{rep['id']}", headers=alice["headers"])
    assert own_resp.status_code == 200

    # Charlie attempts to view Alice's report -> 403 Forbidden
    other_resp = client.get(f"/api/reports/{rep['id']}", headers=charlie["headers"])
    assert other_resp.status_code == 403


# ============================================================================
# 4. Admin Moderation & User Suspension Tests
# ============================================================================

def test_normal_user_admin_forbidden(client: TestClient):
    user = create_authenticated_user(client, "Normal User", f"norm_{uuid.uuid4().hex[:6]}@example.test")

    # Attempting to access admin reports
    resp1 = client.get("/api/admin/reports", headers=user["headers"])
    assert resp1.status_code == 403

    # Attempting to access admin audit logs
    resp2 = client.get("/api/admin/audit-logs", headers=user["headers"])
    assert resp2.status_code == 403

    # Attempting to suspend a user
    resp3 = client.post(
        f"/api/admin/users/{uuid.uuid4()}/suspend",
        headers=user["headers"],
        json={"reason": "Malicious attempt"},
    )
    assert resp3.status_code == 403


def test_admin_report_review_and_resolution(client: TestClient):
    alice = create_authenticated_user(client, "Alice", f"a_{uuid.uuid4().hex[:6]}@example.test")
    bob = create_authenticated_user(client, "Bob", f"b_{uuid.uuid4().hex[:6]}@example.test")
    admin = create_authenticated_user(client, "Admin", f"adm_{uuid.uuid4().hex[:6]}@example.test", role="admin")

    # Alice reports Bob
    rep = client.post(
        "/api/reports",
        headers=alice["headers"],
        json={"reported_user_id": str(bob["user"]["id"]), "reason": "THREAT", "description": "Violent threats"},
    ).json()

    # Admin lists reports
    admin_list = client.get("/api/admin/reports", headers=admin["headers"])
    assert admin_list.status_code == 200
    assert any(r["id"] == rep["id"] for r in admin_list.json()["reports"])

    # Admin updates report status to UNDER_REVIEW
    patch_resp1 = client.patch(
        f"/api/admin/reports/{rep['id']}",
        headers=admin["headers"],
        json={"status": "UNDER_REVIEW", "resolution_note": "Investigating logs and message history."},
    )
    assert patch_resp1.status_code == 200
    assert patch_resp1.json()["status"] == "UNDER_REVIEW"

    # Admin resolves report
    patch_resp2 = client.patch(
        f"/api/admin/reports/{rep['id']}",
        headers=admin["headers"],
        json={"status": "RESOLVED", "resolution_note": "Target warned and interaction concluded."},
    )
    assert patch_resp2.status_code == 200
    assert patch_resp2.json()["status"] == "RESOLVED"
    assert patch_resp2.json()["resolved_at"] is not None

    # Verify audit logs record this
    audit_resp = client.get("/api/admin/audit-logs", headers=admin["headers"])
    assert audit_resp.status_code == 200
    actions = [a["action"] for a in audit_resp.json()["actions"]]
    assert "REPORT_RESOLVED" in actions


def test_admin_suspension_and_reactivation(client: TestClient):
    alice = create_authenticated_user(client, "Alice", f"a_{uuid.uuid4().hex[:6]}@example.test")
    bad_actor = create_authenticated_user(client, "Bad Actor", f"bad_{uuid.uuid4().hex[:6]}@example.test")
    admin = create_authenticated_user(client, "Admin", f"adm_{uuid.uuid4().hex[:6]}@example.test", role="admin")

    # Admin suspends Bad Actor
    susp_resp = client.post(
        f"/api/admin/users/{bad_actor['user']['id']}/suspend",
        headers=admin["headers"],
        json={"reason": "Terms of service violation for persistent harassment."},
    )
    assert susp_resp.status_code == 200

    # Bad Actor tries to create request -> 403 Inactive user account
    req_resp = client.post(
        "/api/requests",
        headers=bad_actor["headers"],
        json={"text": "Trying to post after suspension."},
    )
    assert req_resp.status_code == 403
    assert "inactive user" in req_resp.json()["detail"].lower()

    # Bad Actor tries to list connections -> 403 Forbidden
    conn_resp = client.get("/api/connections", headers=bad_actor["headers"])
    assert conn_resp.status_code == 403

    # Admin reactivates Bad Actor
    react_resp = client.post(
        f"/api/admin/users/{bad_actor['user']['id']}/reactivate",
        headers=admin["headers"],
        json={"reason": "Appeal accepted with conditional probation."},
    )
    assert react_resp.status_code == 200

    # Bad Actor can now make requests again
    req_after = client.post(
        "/api/requests",
        headers=bad_actor["headers"],
        json={"text": "Posting after successful reactivation."},
    )
    assert req_after.status_code == 201

    # Verify audit entries exist for both suspension and reactivation
    audit_resp = client.get("/api/admin/audit-logs", headers=admin["headers"])
    actions = [a["action"] for a in audit_resp.json()["actions"]]
    assert "USER_SUSPENDED" in actions
    assert "USER_REACTIVATED" in actions
