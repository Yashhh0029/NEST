import math
import uuid
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from app.db.database import SessionLocal
from app.models.embedding import Embedding
from app.models.location import Location
from app.models.profile import Profile
from app.models.request import Request
from app.models.user import User, UserRole
from app.services.canonical_text_service import (
    build_profile_canonical_text,
    build_request_canonical_text,
    compute_source_hash,
)
from app.services.embedding_repository import search_similar_profiles, sync_user_profile_embedding
from app.services.embedding_service import embedding_service
from tests.conftest import create_authenticated_user


# ==========================================
# 1. Model & Vector Math Tests
# ==========================================

def test_embedding_model_loads():
    """1. Verify embedding model loads and reports model name."""
    assert embedding_service.model_name == "all-MiniLM-L6-v2"
    assert embedding_service._get_model() is not None


def test_embedding_dimension():
    """2. Verify output vector dimension is exactly 384."""
    vec = embedding_service.embed_text("Test sentence for dimension verification.")
    assert len(vec) == 384
    assert isinstance(vec[0], float)


def test_embedding_reproducibility():
    """3. Verify identical text yields identical embeddings within float tolerance."""
    text_sample = "Affordable PG accommodation near Hinjewadi Phase 1 Pune."
    vec1 = embedding_service.embed_text(text_sample)
    vec2 = embedding_service.embed_text(text_sample)
    assert len(vec1) == len(vec2)
    for v1, v2 in zip(vec1, vec2):
        assert abs(v1 - v2) < 1e-5


def test_different_texts_produce_different_embeddings():
    """4. Verify semantically distinct texts produce different vectors."""
    vec_housing = embedding_service.embed_text("PG room accommodation for rent.")
    vec_cooking = embedding_service.embed_text("Python programming and machine learning.")
    diff = sum(abs(a - b) for a, b in zip(vec_housing, vec_cooking))
    assert diff > 1.0


# ==========================================
# 2. Canonical Text & Hashing Tests
# ==========================================

def test_canonical_profile_text_generation():
    """5. Verify canonical profile text generation captures all semantic fields."""
    user = User(name="Kavita Rao", role=UserRole.HELPER)
    profile = Profile(
        headline="Local Hinjewadi Guide",
        bio="Living in Hinjewadi for 4 years.",
        occupation="Software Engineer",
        organization="Wipro",
        years_experience=4.0,
        languages=["English", "Hindi", "Marathi"],
        help_description="Can help with PG accommodation and bus transport.",
        needs_description=None,
    )
    location = Location(city="Pune", area="Hinjewadi", state="Maharashtra")
    skills = ["PG Accommodation", "Local Transport"]

    canon = build_profile_canonical_text(profile, user, location, skills)
    assert "Kavita Rao" in canon
    assert "Local Hinjewadi Guide" in canon
    assert "Hinjewadi, Pune, Maharashtra" in canon
    assert "Can Help With: Can help with PG accommodation and bus transport." in canon
    assert "Skills: PG Accommodation, Local Transport" in canon


def test_canonical_request_text_generation():
    """6. Verify canonical request text generation combines raw and extracted requirements."""
    req = Request(
        raw_text="Need PG near Whitefield under 10k with veg food.",
        city="Bengaluru",
        area="Whitefield",
        budget_amount=10000.0,
        budget_currency="INR",
        budget_operator="<=",
        budget_period="monthly",
        extracted_requirements={
            "needs": [
                {"category": "accommodation", "item": "PG accommodation"},
                {"category": "food", "item": "vegetarian food"},
            ]
        },
        preferences=["vegetarian", "affordable"],
        user_context=["first job"],
    )

    canon = build_request_canonical_text(req)
    assert "Request: Need PG near Whitefield under 10k with veg food." in canon
    assert "accommodation: PG accommodation" in canon
    assert "Preferences: vegetarian, affordable." in canon
    assert "Target Location: Whitefield, Bengaluru." in canon
    assert "Budget: <= INR 10000 monthly." in canon


def test_sha256_source_hash():
    """7. Verify deterministic SHA-256 hashing."""
    t1 = "Need a room in Wakad."
    t2 = "  Need a room in Wakad.   "
    h1 = compute_source_hash(t1)
    h2 = compute_source_hash(t2)
    assert h1 == h2
    assert len(h1) == 64


# ==========================================
# 3. Persistence, Staleness & Cache Tests
# ==========================================

def test_profile_embedding_persistence(client: TestClient):
    """8. Verify POST /api/embeddings/profile/me creates and stores vector in PostgreSQL."""
    auth = create_authenticated_user(client, "Deepak Joshi", "deepak.j@example.test", "helper")

    client.put("/api/profile/me", json={
        "headline": "Pune Hinjewadi PG Specialist",
        "help_description": "Helping newcomers find verified PGs in Hinjewadi.",
    }, headers=auth["headers"])
    client.put("/api/profile/me/location", json={"city": "Pune", "area": "Hinjewadi"}, headers=auth["headers"])

    resp = client.post("/api/embeddings/profile/me", headers=auth["headers"])
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()

    assert data["owner_type"] == "profile"
    assert data["model_name"] == "all-MiniLM-L6-v2"
    assert data["dimension"] == 384
    assert data["created_or_updated"] is True
    assert len(data["source_hash"]) == 64

    # Direct DB check
    db = SessionLocal()
    try:
        user_uuid = uuid.UUID(auth["user"]["id"])
        emb_in_db = db.query(Embedding).filter(Embedding.owner_type == "profile", Embedding.owner_id == user_uuid).first()
        assert emb_in_db is not None
        assert emb_in_db.dimension == 384
        # Verify vector is populated
        assert len(emb_in_db.embedding) == 384
    finally:
        db.close()


def test_request_embedding_persistence(client: TestClient):
    """9. Verify POST /api/embeddings/request/{id} stores vector in PostgreSQL."""
    auth = create_authenticated_user(client, "Ritu Sen", "ritu.s@example.test", "newcomer")
    req_resp = client.post(
        "/api/requests",
        json={"text": "Moving to Whitefield Bengaluru. Need PG under 12k with tiffin."},
        headers=auth["headers"],
    )
    req_id = req_resp.json()["id"]

    resp = client.post(f"/api/embeddings/request/{req_id}", headers=auth["headers"])
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["owner_type"] == "request"
    assert data["created_or_updated"] is True


def test_unchanged_source_does_not_regenerate(client: TestClient):
    """10. Verify repeated call with unchanged profile does not recompute embedding."""
    auth = create_authenticated_user(client, "Stale Test", "stale@example.test", "helper")
    client.put("/api/profile/me", json={"headline": "Constant Headline"}, headers=auth["headers"])

    # First call: generates
    resp1 = client.post("/api/embeddings/profile/me", headers=auth["headers"])
    assert resp1.status_code == status.HTTP_200_OK
    assert resp1.json()["created_or_updated"] is True

    # Second call without changes: cache hit
    resp2 = client.post("/api/embeddings/profile/me", headers=auth["headers"])
    assert resp2.status_code == status.HTTP_200_OK
    assert resp2.json()["created_or_updated"] is False
    assert resp1.json()["source_hash"] == resp2.json()["source_hash"]


def test_changed_source_regenerates(client: TestClient):
    """11. Verify updating profile detects hash change and regenerates embedding."""
    auth = create_authenticated_user(client, "Dynamic User", "dynamic@example.test", "helper")
    client.put("/api/profile/me", json={"headline": "Initial Headline"}, headers=auth["headers"])

    resp1 = client.post("/api/embeddings/profile/me", headers=auth["headers"])
    hash1 = resp1.json()["source_hash"]

    # Modify profile
    client.put("/api/profile/me", json={"headline": "Completely New Focus on Transport"}, headers=auth["headers"])

    resp2 = client.post("/api/embeddings/profile/me", headers=auth["headers"])
    hash2 = resp2.json()["source_hash"]

    assert hash1 != hash2
    assert resp2.json()["created_or_updated"] is True


def test_pgvector_similarity_query(client: TestClient):
    """12. Verify real PostgreSQL pgvector cosine similarity search endpoint."""
    auth = create_authenticated_user(client, "Search Profile", "search.prof@example.test", "helper")
    client.put("/api/profile/me", json={
        "headline": "Vegetarian Food & Tiffin Guide in Baner Pune",
        "help_description": "Can help newcomers find best veg thali and pure veg tiffin in Baner.",
    }, headers=auth["headers"])
    client.post("/api/embeddings/profile/me", headers=auth["headers"])

    # Query semantic search endpoint
    search_payload = {
        "query_text": "Looking for pure vegetarian tiffin and meals in Baner",
        "limit": 5,
        "min_similarity": 0.3,
    }
    resp = client.post("/api/embeddings/search/profiles", json=search_payload)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["total_matches"] >= 1
    top_match = data["results"][0]
    assert top_match["similarity"] > 0.4
    assert "Vegetarian" in top_match["canonical_text"]


def test_embedding_security_ownership(client: TestClient):
    """13. User A cannot embed or access User B's request."""
    user_a = create_authenticated_user(client, "Owner A", "owner.a@example.test")
    user_b = create_authenticated_user(client, "Attacker B", "attacker.b@example.test")

    create_resp = client.post("/api/requests", json={"text": "Private Request of User A"}, headers=user_a["headers"])
    req_id = create_resp.json()["id"]

    # User B attempts to trigger embedding for User A's request
    resp = client.post(f"/api/embeddings/request/{req_id}", headers=user_b["headers"])
    assert resp.status_code == status.HTTP_403_FORBIDDEN


# ==========================================
# 4. Mandatory Controlled Semantic Test
# ==========================================

def test_controlled_semantic_similarity_comparison(client: TestClient):
    """
    14. Create 3 realistic profiles and verify semantic relevance:
    Profile A: PG Accommodation around Hinjewadi and local transport
    Profile B: Python developer and machine learning mentor
    Profile C: Vegetarian restaurants and tiffin services in Baner
    Query: 'I need affordable accommodation around Hinjewadi and help understanding local transport.'
    Verify Profile A receives higher cosine similarity than unrelated Profile B.
    """
    # Helper A: Hinjewadi Accommodation & Transport
    user_a = create_authenticated_user(client, "Helper A (Housing)", "helper.a.semantic@example.test", "helper")
    client.put("/api/profile/me", json={
        "headline": "Hinjewadi Accommodation & Transport Guide",
        "bio": "4 years living near Hinjewadi Phase 1.",
        "help_description": "Can help newcomers find affordable PG accommodation around Hinjewadi and explain local transport.",
    }, headers=user_a["headers"])
    client.post("/api/embeddings/profile/me", headers=user_a["headers"])

    # Helper B: Machine Learning Mentor (Unrelated to newcomer housing)
    user_b = create_authenticated_user(client, "Helper B (ML Mentor)", "helper.b.semantic@example.test", "helper")
    client.put("/api/profile/me", json={
        "headline": "Machine Learning Engineer",
        "bio": "Passionate about PyTorch, LLMs, and Python mentoring.",
        "help_description": "Experienced Python developer who can mentor students in machine learning.",
    }, headers=user_b["headers"])
    client.post("/api/embeddings/profile/me", headers=user_b["headers"])

    # Helper C: Food & Tiffin
    user_c = create_authenticated_user(client, "Helper C (Food)", "helper.c.semantic@example.test", "helper")
    client.put("/api/profile/me", json={
        "headline": "Pune Foodie & Baner Resident",
        "bio": "Lived in Baner for 8 years.",
        "help_description": "Can recommend vegetarian restaurants and tiffin services around Baner.",
    }, headers=user_c["headers"])
    client.post("/api/embeddings/profile/me", headers=user_c["headers"])

    # Query
    query = "I need affordable accommodation around Hinjewadi and help understanding local transport."
    search_resp = client.post("/api/embeddings/search/profiles", json={"query_text": query, "limit": 50})
    assert search_resp.status_code == status.HTTP_200_OK
    results = search_resp.json()["results"]

    # Locate scores for Helper A and Helper B
    sim_a = next((r["similarity"] for r in results if str(r["user_id"]) == user_a["user"]["id"]), None)
    sim_b = next((r["similarity"] for r in results if str(r["user_id"]) == user_b["user"]["id"]), None)

    # If Helper B fell outside top results due to low semantic relevance, query its stored vector directly
    if sim_b is None:
        from app.db.database import SessionLocal
        from app.models.embedding import Embedding
        from app.services.embedding_service import get_embedding_service

        emb_svc = get_embedding_service()
        q_vec = emb_svc.embed_text(query)
        with SessionLocal() as db_session:
            b_emb_record = db_session.query(Embedding).filter(
                Embedding.owner_type == "profile",
                Embedding.owner_id == uuid.UUID(user_b["user"]["id"]),
            ).first()
            assert b_emb_record is not None, "Helper B embedding was not saved in DB"
            b_vec = [float(x) for x in b_emb_record.embedding]
            sim_b = emb_svc.cosine_similarity(q_vec, b_vec)

    assert sim_a is not None, "Helper A was not found in search results"
    assert sim_b is not None, "Helper B similarity could not be evaluated"

    print(f"\n[Semantic Relevance Check] Helper A (Housing): {sim_a:.4f} vs Helper B (ML Mentor): {sim_b:.4f}")
    # Profile A must have significantly higher similarity than Profile B for a housing/transport query
    assert sim_a > sim_b
    assert sim_a >= 0.50
    assert (sim_a - sim_b) > 0.40
