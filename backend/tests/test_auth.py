import uuid
from fastapi import status
from fastapi.testclient import TestClient
from app.core.security import verify_password
from app.db.database import SessionLocal
from app.models.user import User, UserRole


def test_health_check(client: TestClient):
    """Verify health endpoint reports online and database connected."""
    response = client.get("/api/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"
    assert data["api"] == "online"


def test_root_endpoint(client: TestClient):
    """Verify root endpoint metadata."""
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["tagline"] == "Find Your People. Find Your Place."
    assert data["status"] == "operational"


def test_register_user_success(client: TestClient):
    """Verify valid user registration produces HTTP 201, hashes password, and creates DB record."""
    payload = {
        "name": "Aarav Sharma",
        "email": "aarav.sharma@example.test",
        "password": "SecurePassword123!",
        "role": "newcomer",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    assert data["name"] == "Aarav Sharma"
    assert data["email"] == "aarav.sharma@example.test"
    assert data["role"] == "newcomer"
    assert data["is_active"] is True
    assert data["email_verified"] is False
    assert "id" in data
    # Critical security check: password_hash must NEVER be exposed in response
    assert "password" not in data
    assert "password_hash" not in data

    # Verify directly in PostgreSQL
    db = SessionLocal()
    try:
        user_in_db = db.query(User).filter(User.email == "aarav.sharma@example.test").first()
        assert user_in_db is not None
        assert user_in_db.name == "Aarav Sharma"
        assert user_in_db.password_hash != "SecurePassword123!"
        assert verify_password("SecurePassword123!", user_in_db.password_hash) is True
        assert user_in_db.email_verified is False
        assert user_in_db.email_verification_token_hash is not None
        assert user_in_db.email_verification_expires_at is not None
    finally:
        db.close()


def test_register_duplicate_email(client: TestClient):
    """Verify registration rejects duplicate email addresses."""
    payload = {
        "name": "Duplicate User",
        "email": "duplicate@example.test",
        "password": "Password123!",
        "role": "helper",
    }
    resp1 = client.post("/api/auth/register", json=payload)
    assert resp1.status_code == status.HTTP_201_CREATED

    # Attempt second registration with same email
    resp2 = client.post("/api/auth/register", json=payload)
    assert resp2.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in resp2.json()["detail"]


def test_register_invalid_email(client: TestClient):
    """Verify registration rejects malformed email."""
    payload = {
        "name": "Invalid Email",
        "email": "not-an-email",
        "password": "Password123!",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_register_weak_password_short(client: TestClient):
    """Verify password shorter than 8 characters is rejected."""
    payload = {
        "name": "Short Password",
        "email": "short@example.test",
        "password": "Pass1",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_register_password_no_numbers(client: TestClient):
    """Verify password without numerical digit is rejected."""
    payload = {
        "name": "No Number",
        "email": "nonumber@example.test",
        "password": "PasswordOnlyLetters",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_login_success(client: TestClient):
    """Verify unverified login is rejected, and verified login returns signed JWT access token."""
    from datetime import datetime, timezone

    register_payload = {
        "name": "Login Tester",
        "email": "login.tester@example.test",
        "password": "Password123!",
        "role": "both",
    }
    client.post("/api/auth/register", json=register_payload)

    login_payload = {
        "email": "login.tester@example.test",
        "password": "Password123!",
    }
    # 1. Unverified account must be blocked
    resp_unverified = client.post("/api/auth/login", json=login_payload)
    assert resp_unverified.status_code == status.HTTP_403_FORBIDDEN
    assert "EMAIL_NOT_VERIFIED" in resp_unverified.json()["detail"]

    # 2. Verify account
    db = SessionLocal()
    try:
        db.query(User).filter(User.email == "login.tester@example.test").update({
            "email_verified": True,
            "email_verified_at": datetime.now(timezone.utc),
            "email_verification_token_hash": None,
            "email_verification_expires_at": None,
        })
        db.commit()
    finally:
        db.close()

    # 3. Verified login succeeds
    response = client.post("/api/auth/login", json=login_payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "login.tester@example.test"
    assert data["user"]["role"] == "both"
    assert data["user"]["email_verified"] is True
    # Never expose password hash
    assert "password_hash" not in data["user"]


def test_login_wrong_password(client: TestClient):
    """Verify login with incorrect password returns 401."""
    register_payload = {
        "name": "Wrong Pass User",
        "email": "wrongpass@example.test",
        "password": "CorrectPass123!",
    }
    client.post("/api/auth/register", json=register_payload)

    login_payload = {
        "email": "wrongpass@example.test",
        "password": "IncorrectPass999!",
    }
    response = client.post("/api/auth/login", json=login_payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid email or password" in response.json()["detail"]


def test_login_unknown_user(client: TestClient):
    """Verify login with non-existent email returns 401."""
    login_payload = {
        "email": "nonexistent@example.test",
        "password": "Password123!",
    }
    response = client.post("/api/auth/login", json=login_payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid email or password" in response.json()["detail"]


def test_get_me_authenticated(client: TestClient):
    """Verify /api/auth/me returns current user profile when valid bearer token is supplied."""
    from datetime import datetime, timezone

    reg_payload = {
        "name": "Priya Nair",
        "email": "priya.nair@example.test",
        "password": "Password123!",
        "role": "helper",
    }
    client.post("/api/auth/register", json=reg_payload)

    # Verify user
    db = SessionLocal()
    try:
        db.query(User).filter(User.email == "priya.nair@example.test").update({
            "email_verified": True,
            "email_verified_at": datetime.now(timezone.utc),
            "email_verification_token_hash": None,
            "email_verification_expires_at": None,
        })
        db.commit()
    finally:
        db.close()

    login_resp = client.post("/api/auth/login", json={
        "email": "priya.nair@example.test",
        "password": "Password123!",
    })
    token = login_resp.json()["access_token"]

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Priya Nair"
    assert data["email"] == "priya.nair@example.test"
    assert data["role"] == "helper"
    assert data["email_verified"] is True
    assert "password_hash" not in data


def test_get_me_unauthorized_missing_token(client: TestClient):
    """Verify /api/auth/me returns 401 when Authorization header is absent."""
    response = client.get("/api/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_me_unauthorized_invalid_token(client: TestClient):
    """Verify /api/auth/me returns 401 when token is tampered or invalid."""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid.jwt.token"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_google_auth_missing_token_returns_400(client: TestClient):
    """Verify POST /api/auth/google returns 400 when token string is empty or absent."""
    response = client.post("/api/auth/google", json={})
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    response2 = client.post("/api/auth/google", json={"id_token": ""})
    assert response2.status_code == status.HTTP_400_BAD_REQUEST


def test_google_auth_invalid_token_returns_401(client: TestClient):
    """Verify POST /api/auth/google returns 401 for fabricated token."""
    response = client.post("/api/auth/google", json={"id_token": "fabricated_google_token"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
