import os
import sys
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ==============================================================================
# CRITICAL TEST DATABASE SAFETY GUARD
# ==============================================================================
PROD_NEON_IDENTIFIERS = [
    "ep-crimson-butterfly",
    "b5pgmqnv",
    "us-east-2.aws.neon.tech",
]

raw_test_db_url = os.environ.get("TEST_DATABASE_URL")

# Rule 1: Never silently inherit production DATABASE_URL from backend/.env
if not raw_test_db_url or not raw_test_db_url.strip():
    pytest.exit(
        "\n"
        "==============================================================================\n"
        "CRITICAL TEST DATABASE SAFETY GUARD: TEST_DATABASE_URL IS NOT SET!\n"
        "Tests are strictly forbidden from inheriting DATABASE_URL from backend/.env\n"
        "to prevent accidental connection or mutation of the production Neon database.\n"
        "\n"
        "To run tests, you must explicitly provide a dedicated TEST database URL:\n"
        "  Linux / CI:    export TEST_DATABASE_URL='postgresql://user:pass@testhost/nest_test'\n"
        "  Windows PS:    $env:TEST_DATABASE_URL='postgresql://user:pass@testhost/nest_test'\n"
        "==============================================================================\n",
        returncode=1,
    )

test_db_url = raw_test_db_url.strip()

# Rule 2: Hard failure if test_db_url contains any production Neon identifiers
for identifier in PROD_NEON_IDENTIFIERS:
    if identifier in test_db_url.lower():
        pytest.exit(
            "\n"
            "==============================================================================\n"
            "CRITICAL SAFETY GUARD TRIGGERED: Attempted to run pytest against PRODUCTION!\n"
            f"Found production identifier '{identifier}' in TEST_DATABASE_URL.\n"
            "Tests are strictly forbidden from connecting to the production database.\n"
            "==============================================================================\n",
            returncode=1,
        )

# Explicitly configure environment and settings for the dedicated test database
os.environ["DATABASE_URL"] = test_db_url
os.environ["EMAIL_PROVIDER"] = "test"
os.environ["GOOGLE_MAPS_SERVER_API_KEY"] = ""
os.environ["GOOGLE_MAPS_API_KEY"] = ""

from app.core.config import settings
settings.DATABASE_URL = test_db_url
settings.TEST_DATABASE_URL = test_db_url
settings.EMAIL_PROVIDER = "test"
settings.GOOGLE_MAPS_SERVER_API_KEY = ""
settings.GOOGLE_MAPS_API_KEY = ""

from app.services.google_maps_service import google_maps_service
google_maps_service.api_key = ""

# Bind app database engine and session maker strictly to dedicated test database
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import database as app_db

test_engine = create_engine(test_db_url, pool_pre_ping=True)
app_db.engine = test_engine
app_db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

from app.db.database import SessionLocal, get_db
from app.main import app

def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

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
                (User.email.like("%@example.test")) | (User.email.like("%@nest.local")) | (User.email.like("%@example.com"))
            ).all()
            user_ids = [u.id for u in test_users]
            if user_ids:
                from sqlalchemy import text
                from app.models.request import Request
                from app.models.request_location import RequestLocation
                from app.models.connection import Connection
                from app.models.location import Location
                from app.models.profile import Profile
                req_ids = [str(r[0]) for r in db.query(Request.id).filter(Request.user_id.in_(user_ids)).all()]
                if req_ids:
                    formatted_ids = ", ".join(f"'{rid}'" for rid in req_ids)
                    db.execute(text(f"DELETE FROM connections WHERE request_id IN ({formatted_ids})"))
                    db.execute(text(f"DELETE FROM request_locations WHERE request_id IN ({formatted_ids})"))
                    db.execute(text(f"DELETE FROM requests WHERE id IN ({formatted_ids})"))
                db.query(Connection).filter((Connection.requester_id.in_(user_ids)) | (Connection.helper_id.in_(user_ids))).delete(synchronize_session=False)
                db.query(Location).filter(Location.user_id.in_(user_ids)).delete(synchronize_session=False)
                db.query(Profile).filter(Profile.user_id.in_(user_ids)).delete(synchronize_session=False)
                try:
                    db.query(Embedding).filter(Embedding.owner_id.in_(user_ids)).delete(synchronize_session=False)
                except Exception:
                    db.rollback()
                # Cascade deletes profiles, locations, user_skills for test accounts
                db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
                db.commit()
            try:
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
            except Exception:
                db.rollback()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            db.close()

    _cleanup()
    from app.services.email_service import test_email_provider
    test_email_provider.clear()

    try:
        yield
    finally:
        _cleanup()
        test_email_provider.clear()


def create_authenticated_user(client: TestClient, name: str, email: str, role: str = "newcomer"):
    """Helper utility to register and log in a test user, returning auth headers and user info."""
    from datetime import datetime, timezone

    client.post("/api/auth/register", json={
        "name": name,
        "email": email,
        "password": "SecurePassword123!",
        "role": role,
    })

    # Legitimate verification simulation: set email_verified = True in DB
    db = SessionLocal()
    try:
        db.query(User).filter(User.email == email.strip().lower()).update({
            "email_verified": True,
            "email_verified_at": datetime.now(timezone.utc),
            "email_verification_token_hash": None,
            "email_verification_expires_at": None,
        })
        db.commit()
    finally:
        db.close()

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
