import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.connection import Connection, ConnectionStatus
from app.models.request import Request
from app.services.presence_service import presence_service, PRESENCE_TTL_SECONDS
from tests.conftest import create_authenticated_user


def test_presence_service_unit():
    """Verify presence service offline/online, heartbeat TTL, and last_seen_at behavior."""
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()

    # 1. By default, user is offline
    assert presence_service.is_user_online(user_a) is False
    is_online, last_seen = presence_service.get_user_presence(user_a)
    assert is_online is False

    # 2. User A connects a socket -> Online
    socket_mock = object()
    presence_service.record_user_connected(user_a, socket_ref=socket_mock)
    assert presence_service.is_user_online(user_a) is True
    is_online, last_seen = presence_service.get_user_presence(user_a)
    assert is_online is True
    assert last_seen is not None

    # 3. User A connecting does NOT make User B online
    assert presence_service.is_user_online(user_b) is False

    # 4. User A sends heartbeat -> remains Online
    presence_service.record_user_heartbeat(user_a)
    assert presence_service.is_user_online(user_a) is True

    # 5. Heartbeat expiration simulation (> TTL)
    presence_service._last_heartbeat[user_a] = datetime.now(timezone.utc) - timedelta(seconds=PRESENCE_TTL_SECONDS + 5)
    assert presence_service.is_user_online(user_a) is False
    is_online, last_seen = presence_service.get_user_presence(user_a)
    assert is_online is False

    # 6. New heartbeat refreshes state -> Online again
    presence_service.record_user_heartbeat(user_a)
    assert presence_service.is_user_online(user_a) is True

    # 7. User A explicitly disconnects -> Offline, last_seen updated
    presence_service.record_user_disconnected(user_a, socket_ref=socket_mock)
    assert presence_service.is_user_online(user_a) is False
    is_online, last_seen = presence_service.get_user_presence(user_a)
    assert is_online is False
    assert last_seen is not None


def test_presence_rest_endpoint(client: TestClient, db_session: Session):
    """Verify GET /api/conversations/{id}/presence returns true partner presence and respects auth."""
    auth_u1 = create_authenticated_user(client, "User One Pres", "user1.pres@example.test", role="newcomer")
    auth_u2 = create_authenticated_user(client, "User Two Pres", "user2.pres@example.test", role="helper")

    u1_id = uuid.UUID(auth_u1["user"]["id"])
    u2_id = uuid.UUID(auth_u2["user"]["id"])

    req = Request(
        user_id=u1_id,
        raw_text="Need accommodation in Kochi",
        intent="HOUSING",
        city="Kochi",
        status="OPEN",
    )
    db_session.add(req)
    db_session.commit()

    conn = Connection(
        request_id=req.id,
        requester_id=u1_id,
        helper_id=u2_id,
        status=ConnectionStatus.ACCEPTED,
    )
    db_session.add(conn)
    db_session.commit()

    from app.services.chat_service import create_conversation
    conv = create_conversation(db_session, conn.id, u1_id)

    # 1. User 2 is currently offline
    res_offline = client.get(f"/api/conversations/{conv.id}/presence", headers=auth_u1["headers"])
    assert res_offline.status_code == 200
    data_offline = res_offline.json()
    assert data_offline["conversation_id"] == str(conv.id)
    assert data_offline["partner_id"] == str(u2_id)
    assert data_offline["is_online"] is False

    # 2. User 2 comes online
    sock2 = object()
    presence_service.record_user_connected(u2_id, socket_ref=sock2)

    res_online = client.get(f"/api/conversations/{conv.id}/presence", headers=auth_u1["headers"])
    assert res_online.status_code == 200
    data_online = res_online.json()
    assert data_online["is_online"] is True

    # 3. User 2 disconnects
    presence_service.record_user_disconnected(u2_id, socket_ref=sock2)
    res_after_disc = client.get(f"/api/conversations/{conv.id}/presence", headers=auth_u1["headers"])
    assert res_after_disc.status_code == 200
    assert res_after_disc.json()["is_online"] is False

    presence_service.clear_test_overrides()
