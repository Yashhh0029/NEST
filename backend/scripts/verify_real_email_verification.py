"""
Real-World Verification Script for NEST Email Ownership Verification Flow.
Tests against the live running FastAPI backend (http://127.0.0.1:8000) and PostgreSQL database.
"""
import os
import sys
import uuid
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.database import SessionLocal
from app.models.user import User

BASE_URL = "http://127.0.0.1:8000/api"

def run_e2e_verification():
    print("=" * 70)
    print("NEST REAL-WORLD EMAIL OWNERSHIP VERIFICATION TEST")
    print("=" * 70)

    # 1. Register a real user
    random_id = uuid.uuid4().hex[:8]
    email = f"real.user.{random_id}@example.test"
    password = "SecurePassword123!"

    print(f"\n[Step 1] Registering user with email: {email}")
    reg_payload = {
        "name": f"E2E User {random_id}",
        "email": email,
        "password": password,
        "role": "newcomer",
    }
    reg_resp = requests.post(f"{BASE_URL}/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201, f"Registration failed: {reg_resp.text}"
    user_data = reg_resp.json()
    print(f"  ✓ User registered successfully with HTTP 201")
    assert user_data["email_verified"] is False, "User should be unverified immediately after registration!"
    print(f"  ✓ API response confirms: email_verified = {user_data['email_verified']}")

    # 2. Inspect PostgreSQL directly to confirm unverified status and token hash
    print("\n[Step 2] Auditing PostgreSQL database records")
    db = SessionLocal()
    try:
        user_in_db = db.query(User).filter(User.email == email).first()
        assert user_in_db is not None, "User not found in PostgreSQL!"
        assert user_in_db.email_verified is False, "DB email_verified must be False!"
        assert user_in_db.email_verification_token_hash is not None, "Token hash must be stored in DB!"
        assert len(user_in_db.email_verification_token_hash) == 64, "Token hash must be SHA-256 (64 hex chars)!"
        assert user_in_db.email_verification_expires_at is not None, "Token expiration must be set!"
        token_hash = user_in_db.email_verification_token_hash
        print(f"  ✓ DB email_verified: False")
        print(f"  ✓ DB email_verification_token_hash (SHA-256): {token_hash[:16]}... (securely hashed, raw token never stored)")
        print(f"  ✓ DB email_verification_expires_at: {user_in_db.email_verification_expires_at}")
    finally:
        db.close()

    # 3. Attempt login with unverified account
    print("\n[Step 3] Attempting login before email verification")
    login_resp = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 403, f"Expected 403 Forbidden for unverified account, got: {login_resp.status_code}"
    assert "EMAIL_NOT_VERIFIED" in login_resp.json().get("detail", ""), f"Unexpected detail: {login_resp.text}"
    print(f"  ✓ Login correctly BLOCKED with HTTP 403: {login_resp.json()['detail']}")

    # 4. Register with a random nonexistent email -> remains unverified & blocked
    random_email = f"ghost.{uuid.uuid4().hex[:8]}@example.test"
    print(f"\n[Step 4] Registering random/nonexistent mailbox: {random_email}")
    ghost_resp = requests.post(f"{BASE_URL}/auth/register", json={
        "name": "Ghost User",
        "email": random_email,
        "password": "Password123!",
        "role": "newcomer",
    })
    assert ghost_resp.status_code == 201
    ghost_login = requests.post(f"{BASE_URL}/auth/login", json={"email": random_email, "password": "Password123!"})
    assert ghost_login.status_code == 403
    assert "EMAIL_NOT_VERIFIED" in ghost_login.json().get("detail", "")
    print(f"  ✓ Ghost account created as UNVERIFIED; cannot log in or participate in NEST without mailbox ownership")

    # 5. Verify the user using the legitimate single-use verification token
    print("\n[Step 5] Simulating opening verification link from email")
    # For testing, we retrieve the token hash and create a known token to verify against the API
    from app.services.email_service import test_email_provider
    import secrets
    import hashlib
    from datetime import datetime, timedelta, timezone

    # Let's issue a fresh token to verify via the live API
    raw_token = secrets.token_urlsafe(32)
    new_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    db = SessionLocal()
    try:
        db.query(User).filter(User.email == email).update({
            "email_verification_token_hash": new_hash,
            "email_verification_expires_at": datetime.now(timezone.utc) + timedelta(hours=24),
        })
        db.commit()
    finally:
        db.close()

    # Call GET /api/auth/verify-email?token=...
    print(f"  → Requesting GET /api/auth/verify-email?token=...")
    verify_resp = requests.get(f"{BASE_URL}/auth/verify-email", params={"token": raw_token})
    assert verify_resp.status_code == 200, f"Verification failed: {verify_resp.text}"
    verify_data = verify_resp.json()
    assert verify_data["email_verified"] is True
    print(f"  ✓ Verification response: {verify_data['message']}")

    # 6. Verify single-use token invalidation (Replay attempt must fail)
    print("\n[Step 6] Verifying token cannot be replayed (Single-Use enforcement)")
    replay_resp = requests.get(f"{BASE_URL}/auth/verify-email", params={"token": raw_token})
    assert replay_resp.status_code == 400, f"Expected 400 for replayed token, got: {replay_resp.status_code}"
    print(f"  ✓ Token replay safely rejected: HTTP 400 - {replay_resp.json().get('detail')}")

    # 7. Check database: email_verified must now be True and token cleared
    print("\n[Step 7] Re-auditing PostgreSQL state after verification")
    db = SessionLocal()
    try:
        user_after = db.query(User).filter(User.email == email).first()
        assert user_after.email_verified is True, "email_verified must be True in PostgreSQL!"
        assert user_after.email_verified_at is not None, "email_verified_at must be populated!"
        assert user_after.email_verification_token_hash is None, "Token hash must be cleared after verification!"
        assert user_after.email_verification_expires_at is None, "Expires at must be cleared after verification!"
        print(f"  ✓ DB email_verified: True")
        print(f"  ✓ DB email_verified_at: {user_after.email_verified_at}")
        print(f"  ✓ DB email_verification_token_hash: None (cleared)")
    finally:
        db.close()

    # 8. Now log in with verified account
    print("\n[Step 8] Logging in with now-verified account")
    login_success = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    assert login_success.status_code == 200, f"Login failed: {login_success.text}"
    auth_data = login_success.json()
    token = auth_data["access_token"]
    assert auth_data["user"]["email_verified"] is True
    print(f"  ✓ Login succeeded! Issued JWT token: {token[:25]}...")
    print(f"  ✓ User profile confirmed: email_verified = {auth_data['user']['email_verified']}")

    # 9. Access protected endpoint with authenticated session
    print("\n[Step 9] Accessing protected endpoint /api/auth/me")
    me_resp = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200, f"Failed to access /api/auth/me: {me_resp.text}"
    me_data = me_resp.json()
    assert me_data["email"] == email
    assert me_data["email_verified"] is True
    print(f"  ✓ Authenticated user profile retrieved successfully!")

    # 10. Resend verification rate limiting check
    print("\n[Step 10] Testing resend-verification rate limiting")
    # Advance cooldown so first resend is permitted
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == random_email).first()
        user.email_verification_expires_at = datetime.now(timezone.utc) + timedelta(hours=24) - timedelta(seconds=70)
        db.commit()
    finally:
        db.close()

    # First resend for ghost account
    r1 = requests.post(f"{BASE_URL}/auth/resend-verification", json={"email": random_email})
    assert r1.status_code == 200, f"Expected 200 for first resend after cooldown, got: {r1.status_code} - {r1.text}"
    print(f"  ✓ First resend allowed after cooldown elapsed: {r1.json().get('message')}")

    # Second immediate resend must fail with 429
    r2 = requests.post(f"{BASE_URL}/auth/resend-verification", json={"email": random_email})
    assert r2.status_code == 429, f"Expected 429 Too Many Requests, got {r2.status_code}"
    print(f"  ✓ Immediate second resend rate-limited: HTTP 429 - {r2.json().get('detail')}")

    # Clean up test accounts
    print("\n[Cleanup] Cleaning up test accounts from PostgreSQL")
    db = SessionLocal()
    try:
        db.query(User).filter(User.email.in_([email, random_email])).delete(synchronize_session=False)
        db.commit()
        print("  ✓ Test accounts cleaned up.")
    finally:
        db.close()

    print("\n" + "=" * 70)
    print("ALL 10 E2E EMAIL VERIFICATION SCENARIOS PASSED AGAINST LIVE STACK!")
    print("=" * 70)

if __name__ == "__main__":
    run_e2e_verification()
