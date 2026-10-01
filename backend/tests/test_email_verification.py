import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from app.core.config import settings
from app.core.security import create_access_token
from app.db.database import SessionLocal
from app.models.user import User, UserRole
from app.services.email_service import test_email_provider


def test_malformed_email_rejected_on_registration(client: TestClient):
    """Verify that clearly malformed email formats are rejected with 422."""
    malformed_emails = [
        "abc",
        "abc@",
        "@test.com",
        "hello",
        "test..test@example.com",
        "missingatsign.com",
    ]
    for email in malformed_emails:
        resp = client.post("/api/auth/register", json={
            "name": "Test User",
            "email": email,
            "password": "Password123!",
            "role": "newcomer",
        })
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_registration_creates_unverified_account_and_dispatches_email(client: TestClient):
    """Verify registration creates an unverified account, securely hashes token, and sends verification email."""
    test_email_provider.clear()
    email = "unverified.user@example.test"
    resp = client.post("/api/auth/register", json={
        "name": "Unverified User",
        "email": email,
        "password": "SecurePassword123!",
        "role": "newcomer",
    })
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()
    assert data["email"] == email
    assert data["email_verified"] is False
    assert data["is_active"] is True
    assert "password" not in data
    assert "password_hash" not in data

    # Verify DB state
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        assert user.email_verified is False
        assert user.email_verified_at is None
        assert user.email_verification_token_hash is not None
        assert len(user.email_verification_token_hash) == 64  # SHA-256 hex string
        assert user.email_verification_expires_at is not None
    finally:
        db.close()

    # Verify real verification email dispatched
    assert len(test_email_provider.sent_emails) == 1
    sent = test_email_provider.sent_emails[0]
    assert sent.to_email == email
    assert "Verify your email address" in sent.subject
    assert "verify-email?token=" in sent.html_body
    assert "verify-email?token=" in sent.text_body


def test_unverified_account_cannot_log_in(client: TestClient):
    """Verify that syntactically valid email account cannot log in until email ownership is proven."""
    email = "cannotlogin@example.test"
    client.post("/api/auth/register", json={
        "name": "Cannot Login",
        "email": email,
        "password": "SecurePassword123!",
        "role": "newcomer",
    })

    # Attempt login with correct password
    resp = client.post("/api/auth/login", json={
        "email": email,
        "password": "SecurePassword123!",
    })
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    assert "EMAIL_NOT_VERIFIED" in resp.json()["detail"]


def test_valid_token_verifies_account_and_allows_login(client: TestClient):
    """Verify that presenting the legitimate single-use verification token marks account verified and enables login."""
    test_email_provider.clear()
    email = "verify.me@example.test"
    client.post("/api/auth/register", json={
        "name": "Verify Me",
        "email": email,
        "password": "SecurePassword123!",
        "role": "helper",
    })

    # Extract token from dispatched email
    sent = test_email_provider.sent_emails[0]
    token = sent.html_body.split("token=")[1].split('"')[0].split("&")[0]

    # Verify via GET endpoint
    verify_resp = client.get(f"/api/auth/verify-email?token={token}")
    assert verify_resp.status_code == status.HTTP_200_OK
    assert verify_resp.json()["email_verified"] is True
    assert "successfully" in verify_resp.json()["message"].lower()

    # Verify DB state
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        assert user.email_verified is True
        assert user.email_verified_at is not None
        assert user.email_verification_token_hash is None
        assert user.email_verification_expires_at is None
    finally:
        db.close()

    # Now login must succeed
    login_resp = client.post("/api/auth/login", json={
        "email": email,
        "password": "SecurePassword123!",
    })
    assert login_resp.status_code == status.HTTP_200_OK
    assert "access_token" in login_resp.json()
    assert login_resp.json()["user"]["email_verified"] is True


def test_post_verify_email_endpoint(client: TestClient):
    """Verify that POST /api/auth/verify-email also functions identically."""
    test_email_provider.clear()
    email = "post.verify@example.test"
    client.post("/api/auth/register", json={
        "name": "Post Verify",
        "email": email,
        "password": "SecurePassword123!",
        "role": "both",
    })

    sent = test_email_provider.sent_emails[0]
    token = sent.html_body.split("token=")[1].split('"')[0].split("&")[0]

    verify_resp = client.post("/api/auth/verify-email", json={"token": token})
    assert verify_resp.status_code == status.HTTP_200_OK
    assert verify_resp.json()["email_verified"] is True


def test_reused_token_rejected_safely(client: TestClient):
    """Verify that replaying an already-used token is rejected with HTTP 400."""
    test_email_provider.clear()
    email = "reuse.token@example.test"
    client.post("/api/auth/register", json={
        "name": "Reuse Token",
        "email": email,
        "password": "SecurePassword123!",
    })
    token = test_email_provider.sent_emails[0].html_body.split("token=")[1].split('"')[0].split("&")[0]

    # First use succeeds
    resp1 = client.get(f"/api/auth/verify-email?token={token}")
    assert resp1.status_code == status.HTTP_200_OK

    # Replay attempt fails safely
    resp2 = client.get(f"/api/auth/verify-email?token={token}")
    assert resp2.status_code == status.HTTP_400_BAD_REQUEST
    assert "invalid or already used" in resp2.json()["detail"].lower()


def test_invalid_token_rejected(client: TestClient):
    """Verify completely bogus or fabricated tokens return HTTP 400."""
    resp = client.get("/api/auth/verify-email?token=completely_fake_token_12345")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "invalid or already used" in resp.json()["detail"].lower()


def test_expired_token_rejected_and_invalidated(client: TestClient):
    """Verify expired token returns HTTP 400 and is scrubbed."""
    test_email_provider.clear()
    email = "expired.user@example.test"
    client.post("/api/auth/register", json={
        "name": "Expired User",
        "email": email,
        "password": "SecurePassword123!",
    })
    token = test_email_provider.sent_emails[0].html_body.split("token=")[1].split('"')[0].split("&")[0]

    # Simulate token expiration in PostgreSQL
    db = SessionLocal()
    try:
        db.query(User).filter(User.email == email).update({
            "email_verification_expires_at": datetime.now(timezone.utc) - timedelta(hours=2),
        })
        db.commit()
    finally:
        db.close()

    # Verification must fail with expired message
    resp = client.get(f"/api/auth/verify-email?token={token}")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "expired" in resp.json()["detail"].lower()

    # Verify token was scrubbed
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        assert user.email_verification_token_hash is None
    finally:
        db.close()


def test_resend_verification_rotates_token_and_dispatches_email(client: TestClient):
    """Verify resend rotates token, refreshes expiration, and dispatches fresh email."""
    test_email_provider.clear()
    email = "resend.test@example.test"
    client.post("/api/auth/register", json={
        "name": "Resend Test",
        "email": email,
        "password": "SecurePassword123!",
    })
    orig_token = test_email_provider.sent_emails[0].html_body.split("token=")[1].split('"')[0].split("&")[0]
    test_email_provider.clear()

    # Fast forward cooldown so resend is allowed
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        # Set issued_at back by 70 seconds
        user.email_verification_expires_at = datetime.now(timezone.utc) + timedelta(hours=24) - timedelta(seconds=70)
        db.commit()
    finally:
        db.close()

    resend_resp = client.post("/api/auth/resend-verification", json={"email": email})
    assert resend_resp.status_code == status.HTTP_200_OK
    assert "verification link has been sent" in resend_resp.json()["message"]

    assert len(test_email_provider.sent_emails) == 1
    new_token = test_email_provider.sent_emails[0].html_body.split("token=")[1].split('"')[0].split("&")[0]
    assert new_token != orig_token

    # Old token must no longer work (rotated & invalidated)
    old_verify = client.get(f"/api/auth/verify-email?token={orig_token}")
    assert old_verify.status_code == status.HTTP_400_BAD_REQUEST

    # New token verifies account
    new_verify = client.get(f"/api/auth/verify-email?token={new_token}")
    assert new_verify.status_code == status.HTTP_200_OK
    assert new_verify.json()["email_verified"] is True


def test_resend_rate_limiting_cooldown(client: TestClient):
    """Verify resend is rate-limited and rejects rapid successive calls with HTTP 429."""
    email = "cooldown.test@example.test"
    client.post("/api/auth/register", json={
        "name": "Cooldown Test",
        "email": email,
        "password": "SecurePassword123!",
    })

    # Immediate second call within 60s cooldown must fail with 429
    resp = client.post("/api/auth/resend-verification", json={"email": email})
    assert resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert "wait" in resp.json()["detail"].lower()


def test_resend_no_email_enumeration_leak(client: TestClient):
    """Verify requesting resend for nonexistent or already-verified email returns same generic message."""
    resp_nonexistent = client.post("/api/auth/resend-verification", json={"email": "nonexistent@example.test"})
    assert resp_nonexistent.status_code == status.HTTP_200_OK
    assert "verification link has been sent" in resp_nonexistent.json()["message"]


def test_duplicate_email_blocked_with_normalization(client: TestClient):
    """Verify email normalization and duplicate rejection across case variations."""
    resp1 = client.post("/api/auth/register", json={
        "name": "Case Test",
        "email": "Case.Test@Example.Test",
        "password": "Password123!",
    })
    assert resp1.status_code == status.HTTP_201_CREATED

    resp2 = client.post("/api/auth/register", json={
        "name": "Case Test 2",
        "email": "case.test@example.test",
        "password": "Password123!",
    })
    assert resp2.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in resp2.json()["detail"]


def test_unverified_account_cannot_access_protected_endpoints(client: TestClient):
    """Verify that an unverified user cannot access protected endpoints even if they possess a JWT token."""
    db = SessionLocal()
    try:
        user = User(
            name="Unverified Bearer",
            email="bearer.unverified@example.test",
            password_hash="fakehash",
            role=UserRole.NEWCOMER,
            is_active=True,
            is_verified=False,
            email_verified=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        token = create_access_token(subject=str(user.id), extra_claims={"email": user.email, "role": user.role.value})
    finally:
        db.close()

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    assert "EMAIL_NOT_VERIFIED" in resp.json()["detail"]


def test_google_auth_verifies_email_and_links_account(client: TestClient):
    """Verify Google OAuth server-side verification marks account email_verified=True and links identity."""
    email = "google.verified@example.test"

    mock_id_info = {
        "iss": "accounts.google.com",
        "email": email,
        "email_verified": True,
        "name": "Google Verified User",
        "sub": "google-123456789",
    }

    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_id_info):
        resp = client.post("/api/auth/google", json={"id_token": "valid_google_token"})
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["user"]["email"] == email
        assert data["user"]["email_verified"] is True

        # Check DB
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).first()
            assert user.email_verified is True
            assert user.email_verified_at is not None
        finally:
            db.close()


def test_google_auth_rejects_unverified_google_email(client: TestClient):
    """Verify Google account whose email is not verified by Google is rejected."""
    mock_id_info = {
        "iss": "accounts.google.com",
        "email": "unverified_by_google@example.test",
        "email_verified": False,
        "name": "Google Unverified",
    }

    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_id_info):
        resp = client.post("/api/auth/google", json={"id_token": "valid_token_unverified_email"})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "not verified" in resp.json()["detail"].lower()


def test_google_auth_rejects_invalid_issuer(client: TestClient):
    """Verify Google token from invalid issuer is rejected with 401."""
    mock_id_info = {
        "iss": "https://evil-issuer.com",
        "email": "hacker@example.test",
        "email_verified": True,
    }

    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_id_info):
        resp = client.post("/api/auth/google", json={"id_token": "token_from_evil_issuer"})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
        assert "invalid google token issuer" in resp.json()["detail"].lower()
