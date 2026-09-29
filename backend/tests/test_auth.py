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
    """Verify valid login returns signed JWT access token and user info."""
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
    response = client.post("/api/auth/login", json=login_payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "login.tester@example.test"
    assert data["user"]["role"] == "both"
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
    reg_payload = {
        "name": "Priya Nair",
        "email": "priya.nair@example.test",
        "password": "Password123!",
        "role": "helper",
    }
    client.post("/api/auth/register", json=reg_payload)

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
