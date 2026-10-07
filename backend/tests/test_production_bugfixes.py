import hashlib
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password, create_access_token
from app.db.database import SessionLocal
from app.models.connection import Connection, ConnectionStatus
from app.models.conversation import Conversation
from app.models.email_notification import EmailNotification, EmailDeliveryStatus
from app.models.location import Location
from app.models.profile import Profile
from app.models.request import Request
from app.models.user import User, UserRole
from app.schemas.chat import MessageCreate
from app.schemas.connection import ConnectionCreate
from app.services.auth_service import authenticate_google_user, verify_email_token, resend_verification_email
from app.services.chat_service import send_message
from app.services.connection_service import create_connection_request, update_connection_status
from app.services.email_service import test_email_provider
from app.services.notification_service import (
    notify_nearby_helpers_for_request,
    set_user_online_override_for_testing,
    clear_test_online_overrides,
)
from app.services.translation_service import translation_service


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def cleanup_overrides():
    clear_test_online_overrides()
    test_email_provider.clear()
    yield
    clear_test_online_overrides()
    test_email_provider.clear()


def wait_for_notification(
    db_session: Session,
    notification_type: str,
    recipient_id: uuid.UUID,
    max_wait: float = 2.0,
) -> Optional[EmailNotification]:
    start = time.time()
    while time.time() - start < max_wait:
        db_session.expire_all()
        record = db_session.query(EmailNotification).filter(
            EmailNotification.notification_type == notification_type,
            EmailNotification.recipient_id == recipient_id,
        ).first()
        if record:
            return record
        time.sleep(0.05)
    return None


# ==============================================================================
# ISSUE 1: EMAIL NOTIFICATIONS
# ==============================================================================

def test_nearby_request_email_offline_helper(db_session: Session):
    """Offline eligible helper receives an asynchronous nearby request email notification."""
    newcomer = User(
        name="Newcomer Asha",
        email="newcomer.asha@example.test",
        password_hash=hash_password("SecurePass123!"),
        role=UserRole.NEWCOMER,
        is_active=True,
        email_verified=True,
    )
    helper = User(
        name="Helper Rahul",
        email="helper.rahul@example.test",
        password_hash=hash_password("SecurePass123!"),
        role=UserRole.HELPER,
        is_active=True,
        email_verified=True,
    )
    db_session.add_all([newcomer, helper])
    db_session.commit()

    # Create location for newcomer and helper in Kakkanad
    newcomer_loc = Location(
        user_id=newcomer.id,
        city="Kakkanad",
        area="Infopark",
        latitude=10.015,
        longitude=76.355,
        location_label="Primary",
    )
    helper_loc = Location(
        user_id=helper.id,
        city="Kakkanad",
        area="Infopark",
        latitude=10.016,
        longitude=76.356,
        location_label="Primary",
    )
    req = Request(
        user_id=newcomer.id,
        raw_text="I need help finding a PG in Kakkanad.",
        intent="HOUSING",
        city="Kakkanad",
        area="Infopark",
        status="OPEN",
    )
    db_session.add_all([newcomer_loc, helper_loc, req])
    db_session.commit()

    # Explicitly ensure helper is offline
    set_user_online_override_for_testing(helper.id, False)

    notified = notify_nearby_helpers_for_request(db_session, req, radius_km=10.0)
    assert len(notified) >= 1

    # Check DB email notification record asynchronously created
    record = wait_for_notification(db_session, "nearby_request", helper.id)
    assert record is not None
    assert record.status == EmailDeliveryStatus.SENT.value
    assert "New request near you" in record.subject


def test_nearby_request_email_skipped_when_helper_online(db_session: Session):
    """When eligible helper is actively online, email notification is skipped to avoid spam."""
    newcomer = User(
        name="Newcomer OnlineTest",
        email="newcomer.online@example.test",
        password_hash=hash_password("SecurePass123!"),
        role=UserRole.NEWCOMER,
        is_active=True,
        email_verified=True,
    )
    helper = User(
        name="Helper Active",
        email="helper.active@example.test",
        password_hash=hash_password("SecurePass123!"),
        role=UserRole.HELPER,
        is_active=True,
        email_verified=True,
    )
    db_session.add_all([newcomer, helper])
    db_session.commit()

    newcomer_loc = Location(
        user_id=newcomer.id,
        city="Kochi",
        area="Edappally",
        latitude=10.025,
        longitude=76.31,
        location_label="Primary",
    )
    helper_loc = Location(
        user_id=helper.id,
        city="Kochi",
        area="Edappally",
        latitude=10.026,
        longitude=76.311,
        location_label="Primary",
    )
    req = Request(
        user_id=newcomer.id,
        raw_text="Looking for accommodation in Edappally",
        intent="HOUSING",
        city="Kochi",
        area="Edappally",
        status="OPEN",
    )
    db_session.add_all([newcomer_loc, helper_loc, req])
    db_session.commit()

    # Explicitly mark helper as actively online
    set_user_online_override_for_testing(helper.id, True)

    notified = notify_nearby_helpers_for_request(db_session, req, radius_km=10.0)
    assert len(notified) >= 1

    time.sleep(0.2)
    # Record should not exist because helper is actively online
    record = db_session.query(EmailNotification).filter(
        EmailNotification.notification_type == "nearby_request",
        EmailNotification.recipient_id == helper.id,
    ).first()
    assert record is None


def test_chat_message_email_offline_recipient(db_session: Session):
    """Chat message to offline user dispatches email notification."""
    sender = User(
        name="Sender User",
        email="sender.chat@example.test",
        password_hash=hash_password("SecurePass123!"),
        role=UserRole.NEWCOMER,
        is_active=True,
        email_verified=True,
    )
    recipient = User(
        name="Recipient Offline",
        email="recipient.offline@example.test",
        password_hash=hash_password("SecurePass123!"),
        role=UserRole.HELPER,
        is_active=True,
        email_verified=True,
    )
    db_session.add_all([sender, recipient])
    db_session.commit()

    req = Request(
        user_id=sender.id,
        raw_text="Chat request coordination",
        intent="GUIDANCE",
        city="Kochi",
        status="CONNECTED",
    )
    db_session.add(req)
    db_session.commit()

    conn = Connection(
        request_id=req.id,
        requester_id=sender.id,
        helper_id=recipient.id,
        status="ACCEPTED",
    )
    db_session.add(conn)
    db_session.commit()

    conv = Conversation(
        connection_id=conn.id,
    )
    db_session.add(conv)
    db_session.commit()

    # Ensure recipient is offline
    set_user_online_override_for_testing(recipient.id, False)

    msg = send_message(db_session, conv.id, sender.id, MessageCreate(content="Hello! Are you available to help?"))
    assert msg is not None

    record = wait_for_notification(db_session, "new_message", recipient.id)
    assert record is not None
    assert "new message on NEST" in record.subject


def test_connection_lifecycle_emails(db_session: Session):
    """Connection requested and accepted events trigger offline notification emails."""
    requester = User(
        name="Requester Conn",
        email="requester.conn@example.test",
        password_hash=hash_password("SecurePass123!"),
        role=UserRole.NEWCOMER,
        is_active=True,
        email_verified=True,
    )
    helper = User(
        name="Helper Conn",
        email="helper.conn@example.test",
        password_hash=hash_password("SecurePass123!"),
        role=UserRole.HELPER,
        is_active=True,
        email_verified=True,
    )
    db_session.add_all([requester, helper])
    db_session.commit()

    req = Request(
        user_id=requester.id,
        raw_text="Need help finding a flat",
        intent="HOUSING",
        city="Kochi",
        status="OPEN",
    )
    db_session.add(req)
    db_session.commit()

    set_user_online_override_for_testing(helper.id, False)
    set_user_online_override_for_testing(requester.id, False)

    # 1. Create connection request
    payload = ConnectionCreate(
        request_id=req.id,
        helper_id=helper.id,
        initial_message="Hi Rahul, could you guide me?",
    )
    conn_resp = create_connection_request(db_session, requester, payload)
    assert conn_resp.status.value == "PENDING"

    # Check connection_requested email
    conn_req_record = wait_for_notification(db_session, "connection_requested", helper.id)
    assert conn_req_record is not None
    assert "New connection request" in conn_req_record.subject

    # 2. Accept connection request
    accept_resp = update_connection_status(db_session, conn_resp.id, helper, "accept")
    assert accept_resp.status.value == "ACCEPTED"

    # Check connection_accepted email
    conn_acc_record = wait_for_notification(db_session, "connection_accepted", requester.id)
    assert conn_acc_record is not None
    assert "accepted your connection request" in conn_acc_record.subject


# ==============================================================================
# ISSUE 2: TRANSLATION ACCURACY & DYNAMIC SWITCHING
# ==============================================================================

def test_translation_pairs_and_repeated_switching(client: TestClient):
    """
    Test real translations across supported pairs:
    English -> Hindi -> Marathi -> Malayalam -> English
    and verify original text is preserved without stale caching.
    """
    user = User(
        name="Translator Tester",
        email="translator.test@example.test",
        password_hash=hash_password("SecurePass123!"),
        role=UserRole.NEWCOMER,
        is_active=True,
        email_verified=True,
    )
    db = SessionLocal()
    db.add(user)
    db.commit()
    token = create_access_token(subject=str(user.id), extra_claims={"email": user.email, "role": user.role.value})
    headers = {"Authorization": f"Bearer {token}"}
    db.close()

    original = "Hello, where can I find affordable accommodation in Kakkanad?"

    # 1. Translate to Hindi
    r1 = client.post("/api/chat/translate", json={"text": original, "target_language": "hi"}, headers=headers)
    assert r1.status_code == 200
    res1 = r1.json()
    assert res1["target_language"] == "hi"
    assert len(res1["translated_text"]) > 0
    assert res1["original_text"] == original

    # 2. Change target language to Marathi and translate from same original text
    r2 = client.post("/api/chat/translate", json={"text": original, "target_language": "mr"}, headers=headers)
    assert r2.status_code == 200
    res2 = r2.json()
    assert res2["target_language"] == "mr"
    assert len(res2["translated_text"]) > 0
    assert res2["original_text"] == original

    # 3. Change target language to Malayalam
    r3 = client.post("/api/chat/translate", json={"text": original, "target_language": "ml"}, headers=headers)
    assert r3.status_code == 200
    res3 = r3.json()
    assert res3["target_language"] == "ml"
    assert len(res3["translated_text"]) > 0
    assert res3["original_text"] == original

    # 4. Change back to English
    r4 = client.post("/api/chat/translate", json={"text": res1["translated_text"], "target_language": "en"}, headers=headers)
    assert r4.status_code == 200
    res4 = r4.json()
    assert res4["target_language"] == "en"
    assert "kakkanad" in res4["translated_text"].lower() or "accommodation" in res4["translated_text"].lower()


def test_translation_validation_and_error_handling(client: TestClient):
    """Unsupported languages return 400 Bad Request."""
    user = User(
        name="Validation Tester",
        email="val.trans@example.test",
        password_hash=hash_password("SecurePass123!"),
        role=UserRole.NEWCOMER,
        is_active=True,
        email_verified=True,
    )
    db = SessionLocal()
    db.add(user)
    db.commit()
    token = create_access_token(subject=str(user.id), extra_claims={"email": user.email, "role": user.role.value})
    headers = {"Authorization": f"Bearer {token}"}
    db.close()

    resp = client.post(
        "/api/chat/translate",
        json={"text": "Hello world", "target_language": "klingon_unsupported"},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "Unsupported target language" in resp.json()["detail"]


# ==============================================================================
# ISSUE 3: GOOGLE AUTH & MANUAL EMAIL VERIFICATION
# ==============================================================================

def test_google_auth_sub_and_account_linking(db_session: Session):
    """Google auth uses sub as primary identifier and safely links to existing registered email."""
    # Create an existing unlinked user
    existing_user = User(
        name="Priya Existing",
        email="priya.googlelink@example.test",
        password_hash=hash_password("OldPassword123!"),
        role=UserRole.HELPER,
        is_active=True,
        email_verified=False,
    )
    db_session.add(existing_user)
    db_session.commit()

    google_sub = "google_sub_1092837465"

    fake_id_info = {
        "iss": "https://accounts.google.com",
        "sub": google_sub,
        "email": "priya.googlelink@example.test",
        "email_verified": True,
        "name": "Priya Linked",
    }

    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=fake_id_info):
        token_resp = authenticate_google_user(db_session, "fake_valid_google_token")
        assert token_resp.access_token is not None
        assert token_resp.user.email == "priya.googlelink@example.test"
        assert token_resp.user.google_id == google_sub
        assert token_resp.user.email_verified is True
        assert token_resp.user.role == UserRole.HELPER

        # Subsequent login uses google_sub directly
        token_resp2 = authenticate_google_user(db_session, "fake_valid_google_token")
        assert token_resp2.user.id == token_resp.user.id


def test_google_auth_deactivated_account_with_reason(db_session: Session):
    """Deactivated accounts cannot authenticate via Google and return clear reason."""
    deactivated_user = User(
        name="Deactivated User",
        email="deactivated.user@example.test",
        password_hash=hash_password("Password123!"),
        role=UserRole.NEWCOMER,
        google_id="deactivated_sub_9999",
        is_active=False,
        deactivated_reason="Account suspended for policy violation.",
        email_verified=True,
    )
    db_session.add(deactivated_user)
    db_session.commit()

    fake_id_info = {
        "iss": "https://accounts.google.com",
        "sub": "deactivated_sub_9999",
        "email": "deactivated.user@example.test",
        "email_verified": True,
        "name": "Deactivated User",
    }

    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=fake_id_info):
        with pytest.raises(Exception) as excinfo:
            authenticate_google_user(db_session, "fake_token")
        assert "deactivated" in str(excinfo.value.detail).lower()
        assert "policy violation" in str(excinfo.value.detail)


def test_manual_email_verification_idempotent_and_cooldown(db_session: Session):
    """Email verification succeeds on first call and returns already-verified on repeat calls without 400 error."""
    raw_token = "secure_verification_token_abc123"
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    user = User(
        name="Manual Verify",
        email="manual.verify@example.test",
        password_hash=hash_password("Password123!"),
        role=UserRole.NEWCOMER,
        is_active=True,
        email_verified=False,
        email_verification_token_hash=token_hash,
        email_verification_expires_at=expires_at,
    )
    db_session.add(user)
    db_session.commit()

    # 1. First verification: marks verified
    res1 = verify_email_token(db_session, raw_token)
    assert res1["email_verified"] is True
    assert "successfully" in res1["message"].lower()

    db_session.refresh(user)
    assert user.email_verified is True

    # 2. Second verification (simulating React StrictMode or browser reload):
    # Must NOT fail with 400 'Invalid or already used verification link'
    res2 = verify_email_token(db_session, raw_token)
    assert res2["email_verified"] is True
    assert "already verified" in res2["message"].lower()
