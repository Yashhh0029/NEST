import json
import uuid
import pytest
from fastapi.testclient import TestClient
from tests.conftest import create_authenticated_user


def setup_active_connection(client: TestClient, prefix: str = "chat"):
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
        json={"text": "Moving to Bengaluru near Whitefield, need housing guidance."},
    )
    request_id = req_resp.json()["id"]

    conn_resp = client.post(
        "/api/connections",
        headers=requester["headers"],
        json={
            "request_id": request_id,
            "helper_id": str(helper["user"]["id"]),
            "initial_message": "Hello, need help!",
        },
    )
    connection_id = conn_resp.json()["id"]

    # Helper accepts connection
    accept_resp = client.patch(
        f"/api/connections/{connection_id}",
        headers=helper["headers"],
        json={"action": "accept"},
    )
    assert accept_resp.status_code == 200
    assert accept_resp.json()["status"] == "ACCEPTED"

    return {
        "requester": requester,
        "helper": helper,
        "connection_id": connection_id,
        "request_id": request_id,
    }


def test_chat_requires_authentication(client: TestClient):
    """Unauthenticated access to conversation endpoints must return 401."""
    resp = client.get("/api/conversations")
    assert resp.status_code == 401

    resp = client.post("/api/conversations", json={"connection_id": str(uuid.uuid4())})
    assert resp.status_code == 401

    resp = client.get(f"/api/conversations/{uuid.uuid4()}/messages")
    assert resp.status_code == 401


def test_conversation_creation_requires_active_connection(client: TestClient):
    """Conversations cannot be created for pending, declined, or cancelled connections."""
    user_a = create_authenticated_user(client, "User A", f"u_a_{uuid.uuid4().hex[:6]}@example.test")
    user_b = create_authenticated_user(client, "User B", f"u_b_{uuid.uuid4().hex[:6]}@example.test")

    req_resp = client.post(
        "/api/requests",
        headers=user_a["headers"],
        json={"text": "Need assistance in Pune Hinjewadi."},
    )
    request_id = req_resp.json()["id"]

    # 1. PENDING connection
    conn_resp = client.post(
        "/api/connections",
        headers=user_a["headers"],
        json={"request_id": request_id, "helper_id": str(user_b["user"]["id"])},
    )
    conn_id = conn_resp.json()["id"]

    # Attempt to create conversation while connection is PENDING
    create_resp = client.post(
        "/api/conversations",
        headers=user_a["headers"],
        json={"connection_id": conn_id},
    )
    assert create_resp.status_code == 403
    assert "active accepted" in create_resp.json()["detail"].lower()

    # 2. DECLINED connection
    client.patch(
        f"/api/connections/{conn_id}",
        headers=user_b["headers"],
        json={"action": "decline"},
    )
    create_resp = client.post(
        "/api/conversations",
        headers=user_a["headers"],
        json={"connection_id": conn_id},
    )
    assert create_resp.status_code == 403

    # Retrieve-only endpoint should also forbid / not found
    get_resp = client.get(
        f"/api/conversations/by-connection/{conn_id}",
        headers=user_a["headers"],
    )
    assert get_resp.status_code == 403


def test_conversation_creation_and_idempotency(client: TestClient):
    """POST /api/conversations succeeds for ACCEPTED connection and is idempotent."""
    data = setup_active_connection(client, "idemp")
    requester = data["requester"]
    conn_id = data["connection_id"]

    # 1. First creation
    resp = client.post(
        "/api/conversations",
        headers=requester["headers"],
        json={"connection_id": conn_id},
    )
    assert resp.status_code == 201
    conv_data = resp.json()
    conv_id = conv_data["id"]
    assert conv_data["connection_id"] == conn_id
    assert conv_data["partner"]["name"] == data["helper"]["user"]["name"]

    # 2. Second creation returns same conversation without creating duplicate
    resp2 = client.post(
        "/api/conversations",
        headers=requester["headers"],
        json={"connection_id": conn_id},
    )
    assert resp2.status_code == 201
    assert resp2.json()["id"] == conv_id

    # 3. Retrieve-only endpoint returns existing conversation
    get_resp = client.get(
        f"/api/conversations/by-connection/{conn_id}",
        headers=requester["headers"],
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == conv_id


def test_non_participant_forbidden_from_conversation(client: TestClient):
    """An outsider user cannot access or message a conversation."""
    data = setup_active_connection(client, "perm")
    outsider = create_authenticated_user(client, "Outsider", f"out_{uuid.uuid4().hex[:6]}@example.test")

    # Create conversation
    create_resp = client.post(
        "/api/conversations",
        headers=data["requester"]["headers"],
        json={"connection_id": data["connection_id"]},
    )
    conv_id = create_resp.json()["id"]

    # Outsider tries to access conversation
    get_resp = client.get(
        f"/api/conversations/{conv_id}",
        headers=outsider["headers"],
    )
    assert get_resp.status_code == 403

    # Outsider tries to send message
    send_resp = client.post(
        f"/api/conversations/{conv_id}/messages",
        headers=outsider["headers"],
        json={"content": "I am eavesdropping!"},
    )
    assert send_resp.status_code == 403


def test_send_message_lifecycle_and_validation(client: TestClient):
    """Sending message derives sender from JWT, rejects empty/long messages, and saves content."""
    data = setup_active_connection(client, "msg")
    requester = data["requester"]
    helper = data["helper"]

    # Create conversation
    create_resp = client.post(
        "/api/conversations",
        headers=requester["headers"],
        json={"connection_id": data["connection_id"]},
    )
    conv_id = create_resp.json()["id"]

    # Empty message rejection
    resp_empty = client.post(
        f"/api/conversations/{conv_id}/messages",
        headers=requester["headers"],
        json={"content": "   "},
    )
    assert resp_empty.status_code == 422

    # Message exceeds 2000 chars rejection
    resp_toolong = client.post(
        f"/api/conversations/{conv_id}/messages",
        headers=requester["headers"],
        json={"content": "A" * 2005},
    )
    assert resp_toolong.status_code == 422

    # Valid message from Requester
    send_resp = client.post(
        f"/api/conversations/{conv_id}/messages",
        headers=requester["headers"],
        json={"content": "Hi! Can you recommend good PGs in Whitefield?"},
    )
    assert send_resp.status_code == 201
    msg_data = send_resp.json()
    assert msg_data["content"] == "Hi! Can you recommend good PGs in Whitefield?"
    assert msg_data["sender_id"] == str(requester["user"]["id"])
    assert msg_data["is_mine"] is True

    # Helper retrieves message and replies
    get_msgs = client.get(
        f"/api/conversations/{conv_id}/messages",
        headers=helper["headers"],
    )
    assert get_msgs.status_code == 200
    msg_list = get_msgs.json()["messages"]
    assert len(msg_list) == 1
    assert msg_list[0]["content"] == "Hi! Can you recommend good PGs in Whitefield?"
    assert msg_list[0]["is_mine"] is False

    # Helper replies
    reply_resp = client.post(
        f"/api/conversations/{conv_id}/messages",
        headers=helper["headers"],
        json={"content": "Sure, check out ITPL main road!"},
    )
    assert reply_resp.status_code == 201
    assert reply_resp.json()["sender_id"] == str(helper["user"]["id"])


def test_edit_and_soft_delete_message(client: TestClient):
    """Author can edit and soft delete; other participant cannot."""
    data = setup_active_connection(client, "editdel")
    requester = data["requester"]
    helper = data["helper"]

    create_resp = client.post(
        "/api/conversations",
        headers=requester["headers"],
        json={"connection_id": data["connection_id"]},
    )
    conv_id = create_resp.json()["id"]

    # Requester posts message
    msg_resp = client.post(
        f"/api/conversations/{conv_id}/messages",
        headers=requester["headers"],
        json={"content": "Initial message with typo"},
    )
    msg_id = msg_resp.json()["id"]

    # Helper attempts to edit -> 403 Forbidden
    resp = client.patch(
        f"/api/messages/{msg_id}",
        headers=helper["headers"],
        json={"content": "Hacked content"},
    )
    assert resp.status_code == 403

    # Requester edits message -> Success
    edit_resp = client.patch(
        f"/api/messages/{msg_id}",
        headers=requester["headers"],
        json={"content": "Corrected message without typo"},
    )
    assert edit_resp.status_code == 200
    assert edit_resp.json()["content"] == "Corrected message without typo"
    assert edit_resp.json()["edited_at"] is not None

    # Helper attempts to delete -> 403 Forbidden
    del_forbidden = client.delete(
        f"/api/messages/{msg_id}",
        headers=helper["headers"],
    )
    assert del_forbidden.status_code == 403

    # Requester deletes message -> Soft delete
    del_resp = client.delete(
        f"/api/messages/{msg_id}",
        headers=requester["headers"],
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["content"] == "Message deleted"
    assert del_resp.json()["deleted_at"] is not None

    # When helper views conversation, deleted message displays "Message deleted"
    get_msgs = client.get(
        f"/api/conversations/{conv_id}/messages",
        headers=helper["headers"],
    )
    assert get_msgs.status_code == 200
    assert get_msgs.json()["messages"][0]["content"] == "Message deleted"


def test_pagination_and_conversation_list(client: TestClient):
    """Pagination limits messages and lists user conversations."""
    data = setup_active_connection(client, "pag")
    requester = data["requester"]
    conn_id = data["connection_id"]

    create_resp = client.post(
        "/api/conversations",
        headers=requester["headers"],
        json={"connection_id": conn_id},
    )
    conv_id = create_resp.json()["id"]

    # Send 5 messages
    for i in range(5):
        client.post(
            f"/api/conversations/{conv_id}/messages",
            headers=requester["headers"],
            json={"content": f"Message number {i}"},
        )

    # Fetch with limit=3
    pag_resp = client.get(
        f"/api/conversations/{conv_id}/messages?limit=3",
        headers=requester["headers"],
    )
    assert pag_resp.status_code == 200
    body = pag_resp.json()
    assert len(body["messages"]) == 3
    assert body["has_more"] is True
    assert body["total"] == 5

    # Check conversation list
    list_resp = client.get(
        "/api/conversations",
        headers=requester["headers"],
    )
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1


def test_websocket_authorization_and_message_delivery(client: TestClient):
    """WebSocket enforces token verification, participant verification, and persists before broadcast."""
    data = setup_active_connection(client, "ws")
    requester = data["requester"]
    helper = data["helper"]
    outsider = create_authenticated_user(client, "WS Outsider", f"ws_out_{uuid.uuid4().hex[:6]}@example.test")

    create_resp = client.post(
        "/api/conversations",
        headers=requester["headers"],
        json={"connection_id": data["connection_id"]},
    )
    conv_id = create_resp.json()["id"]

    # 1. Connect without token -> rejected with 1008 policy violation
    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws/conversations/{conv_id}"):
            pass

    # 2. Connect with invalid token -> rejected
    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws/conversations/{conv_id}?token=invalid.jwt.token"):
            pass

    # 3. Connect with outsider token -> rejected
    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws/conversations/{conv_id}?token={outsider['token']}"):
            pass

    # 4. Valid participant connects -> accepted
    with client.websocket_connect(f"/ws/conversations/{conv_id}?token={requester['token']}") as ws:
        ack = json.loads(ws.receive_text())
        assert ack["type"] == "connected"
        assert ack["conversation_id"] == conv_id

        # Send ping -> receive pong
        ws.send_text(json.dumps({"type": "ping"}))
        pong = json.loads(ws.receive_text())
        assert pong["type"] == "pong"

        # Send real message
        ws.send_text(json.dumps({
            "type": "message",
            "content": "Real-time message over WebSocket!",
        }))
        broadcast = json.loads(ws.receive_text())
        assert broadcast["type"] == "message"
        assert broadcast["message"]["content"] == "Real-time message over WebSocket!"

    # 5. Verify message was persisted to PostgreSQL
    get_msgs = client.get(
        f"/api/conversations/{conv_id}/messages",
        headers=helper["headers"],
    )
    assert get_msgs.status_code == 200
    persisted_texts = [m["content"] for m in get_msgs.json()["messages"]]
    assert "Real-time message over WebSocket!" in persisted_texts


def test_chat_translation_endpoint(client: TestClient):
    """Test translating chat messages across languages."""
    user = create_authenticated_user(client, "Translate User", f"trans_{uuid.uuid4().hex[:6]}@example.test")

    # Unauthenticated fails
    resp = client.post("/api/chat/translate", json={"text": "Hello", "target_language": "ml"})
    assert resp.status_code == 401

    # Authenticated translation from English to Malayalam
    resp = client.post(
        "/api/chat/translate",
        headers=user["headers"],
        json={
            "text": "Hello, how are you?",
            "target_language": "ml",
            "source_language": "en",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["original_text"] == "Hello, how are you?"
    assert len(data["translated_text"]) > 0
    assert data["target_language"] == "ml"

    # Hindi to English
    resp2 = client.post(
        "/api/chat/translate",
        headers=user["headers"],
        json={
            "text": "मुझे मदद चाहिए",
            "target_language": "en",
        },
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert "help" in data2["translated_text"].lower() or "need" in data2["translated_text"].lower()
