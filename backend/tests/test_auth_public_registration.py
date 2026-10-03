import pytest
from fastapi.testclient import TestClient
from app.db.database import SessionLocal
from app.models.user import User, UserRole
from app.core.security import hash_password, create_access_token
from tests.conftest import create_authenticated_user


def test_public_registration_without_auth_header(client: TestClient):
    """1. Fresh registration request without Authorization header."""
    reg_payload = {
        "name": "Public User No Auth",
        "email": "public_no_auth@example.test",
        "password": "Password123!",
        "role": "newcomer"
    }
    resp = client.post("/api/auth/register", json=reg_payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["email"] == "public_no_auth@example.test"
    assert data["is_active"] is True
    assert data["email_verified"] is False


def test_public_registration_with_stale_or_deactivated_auth_header(client: TestClient):
    """2. Fresh registration request while an old/stale/deactivated JWT is present in Authorization header."""
    # Create a deactivated user to simulate a stale deactivated JWT
    db = SessionLocal()
    try:
        pw = hash_password("OldPassword123!")
        deactivated_user = User(
            name="Deactivated User",
            email="stale_deactivated@example.test",
            password_hash=pw,
            role=UserRole.NEWCOMER,
            is_active=False,
            email_verified=True
        )
        db.add(deactivated_user)
        db.commit()
        db.refresh(deactivated_user)
        stale_token = create_access_token(
            subject=str(deactivated_user.id),
            extra_claims={"email": deactivated_user.email, "role": "newcomer"}
        )
    finally:
        db.close()

    # Attempt to register a brand new user while passing the stale deactivated token
    reg_payload = {
        "name": "New Fresh User",
        "email": "new_fresh_with_stale_jwt@example.test",
        "password": "Password123!",
        "role": "helper"
    }
    headers = {"Authorization": f"Bearer {stale_token}"}
    resp = client.post("/api/auth/register", json=reg_payload, headers=headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["email"] == "new_fresh_with_stale_jwt@example.test"
    assert data["is_active"] is True
    assert data["email_verified"] is False


def test_login_behavior_matrix(client: TestClient):
    """
    3. Verify existing login behavior:
    - active verified user -> login succeeds
    - unverified user -> blocked with EMAIL_NOT_VERIFIED
    - deactivated user -> blocked with "User account is deactivated."
    """
    # A. Active Verified User
    user_a = create_authenticated_user(client, "Active Verified", "active_verified@example.test")
    login_resp_a = client.post("/api/auth/login", json={
        "email": "active_verified@example.test",
        "password": "SecurePassword123!"
    })
    assert login_resp_a.status_code == 200
    assert "access_token" in login_resp_a.json()

    # B. Unverified User
    client.post("/api/auth/register", json={
        "name": "Unverified User",
        "email": "unverified_login@example.test",
        "password": "Password123!",
        "role": "newcomer"
    })
    login_resp_b = client.post("/api/auth/login", json={
        "email": "unverified_login@example.test",
        "password": "Password123!"
    })
    assert login_resp_b.status_code == 403
    assert "EMAIL_NOT_VERIFIED" in login_resp_b.json()["detail"]

    # C. Deactivated User
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.email == "active_verified@example.test").first()
        db_user.is_active = False
        db.commit()
    finally:
        db.close()

    login_resp_c = client.post("/api/auth/login", json={
        "email": "active_verified@example.test",
        "password": "SecurePassword123!"
    })
    assert login_resp_c.status_code == 403
    assert login_resp_c.json()["detail"] == "User account is deactivated."
