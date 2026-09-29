import os
import sys
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.database import SessionLocal
from app.main import app
from app.models.skill import Skill
from app.models.user import User


@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_test_data():
    """Ensure test created users, skills, and related data are cleaned up before and after each test run."""
    def _cleanup():
        from app.models.embedding import Embedding
        db = SessionLocal()
        try:
            # Find test users
            test_users = db.query(User).filter(
                (User.email.like("%@example.test")) | (User.email.like("%@nest.local"))
            ).all()
            user_ids = [u.id for u in test_users]
            if user_ids:
                # Remove embeddings owned by test users or their requests
                db.query(Embedding).filter(Embedding.owner_id.in_(user_ids)).delete(synchronize_session=False)
                # Cascade deletes profiles, locations, user_skills for test accounts
                db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
                db.commit()
            # Clean any orphan profile embeddings
            valid_user_ids = [u[0] for u in db.query(User.id).all()]
            if valid_user_ids:
                db.query(Embedding).filter(
                    Embedding.owner_type == "profile",
                    ~Embedding.owner_id.in_(valid_user_ids)
                ).delete(synchronize_session=False)
            else:
                db.query(Embedding).filter(Embedding.owner_type == "profile").delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()

    _cleanup()
    yield
    _cleanup()


def create_authenticated_user(client: TestClient, name: str, email: str, role: str = "newcomer"):
    """Helper utility to register and log in a test user, returning auth headers and user info."""
    client.post("/api/auth/register", json={
        "name": name,
        "email": email,
        "password": "SecurePassword123!",
        "role": role,
    })
    login_resp = client.post("/api/auth/login", json={
        "email": email,
        "password": "SecurePassword123!",
    })
    token = login_resp.json()["access_token"]
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "user": login_resp.json()["user"],
        "token": token,
    }
