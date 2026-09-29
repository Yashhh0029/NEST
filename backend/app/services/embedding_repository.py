import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.embedding import Embedding
from app.models.location import Location
from app.models.profile import Profile
from app.models.request import Request
from app.models.skill import Skill, UserSkill
from app.models.user import User
from app.services.canonical_text_service import (
    build_profile_canonical_text,
    build_request_canonical_text,
    compute_source_hash,
)
from app.services.embedding_service import embedding_service


def upsert_entity_embedding(
    db: Session,
    owner_type: str,
    owner_id: uuid.UUID,
    canonical_text: str,
) -> Tuple[Embedding, bool]:
    """
    Persist or update an embedding for an entity (profile, request, etc.).
    Uses deterministic SHA-256 source hashing to avoid redundant model executions.
    Returns (Embedding, created_or_updated: bool).
    """
    source_hash = compute_source_hash(canonical_text)
    now = datetime.now(timezone.utc)

    existing = (
        db.query(Embedding)
        .filter(Embedding.owner_type == owner_type, Embedding.owner_id == owner_id)
        .first()
    )

    if existing and existing.source_hash == source_hash:
        # Cache hit: source text has not changed, reuse existing vector
        return existing, False

    # Generate new semantic embedding using local sentence-transformers model
    vector = embedding_service.embed_text(canonical_text)

    if existing:
        existing.embedding = vector
        existing.canonical_text = canonical_text
        existing.source_hash = source_hash
        existing.model_name = embedding_service.model_name
        existing.dimension = embedding_service.dimension
        existing.updated_at = now
        db.commit()
        db.refresh(existing)
        return existing, True
    else:
        new_embedding = Embedding(
            owner_type=owner_type,
            owner_id=owner_id,
            embedding_type="semantic_dense",
            model_name=embedding_service.model_name,
            dimension=embedding_service.dimension,
            source_hash=source_hash,
            embedding=vector,
            canonical_text=canonical_text,
            created_at=now,
            updated_at=now,
        )
        db.add(new_embedding)
        db.commit()
        db.refresh(new_embedding)
        return new_embedding, True


def sync_user_profile_embedding(db: Session, user: User) -> Tuple[Embedding, bool]:
    """
    Gather user profile, location, and skills, construct canonical text,
    and persist the resulting profile vector embedding.
    """
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    location = (
        db.query(Location)
        .filter(Location.user_id == user.id, Location.location_label == "Primary")
        .first()
    )
    user_skills_raw = (
        db.query(Skill.name)
        .join(UserSkill, UserSkill.skill_id == Skill.id)
        .filter(UserSkill.user_id == user.id)
        .all()
    )
    skills = [s[0] for s in user_skills_raw]

    canonical_text = build_profile_canonical_text(
        profile=profile,
        user=user,
        location=location,
        skills=skills,
    )

    return upsert_entity_embedding(
        db=db,
        owner_type="profile",
        owner_id=user.id,
        canonical_text=canonical_text,
    )


def sync_user_request_embedding(
    db: Session, user: User, request_id: uuid.UUID
) -> Tuple[Embedding, bool]:
    """
    Retrieve user request, verify ownership, construct canonical text,
    and persist the request vector embedding.
    """
    req = db.query(Request).filter(Request.id == request_id).first()
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found.",
        )
    if req.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this request.",
        )

    canonical_text = build_request_canonical_text(req)

    return upsert_entity_embedding(
        db=db,
        owner_type="request",
        owner_id=req.id,
        canonical_text=canonical_text,
    )


def search_similar_profiles(
    db: Session,
    query_embedding: List[float],
    limit: int = 10,
    min_similarity: float = 0.0,
    exclude_user_id: Optional[uuid.UUID] = None,
) -> List[Dict[str, Any]]:
    """
    Execute native PostgreSQL pgvector cosine distance query using pgvector comparator:
    Cosine similarity = 1.0 - Embedding.embedding.cosine_distance(query_embedding)
    """
    dist_expr = Embedding.embedding.cosine_distance(query_embedding)
    sim_expr = (1.0 - dist_expr).label("similarity")

    stmt = (
        select(Embedding.owner_id, sim_expr, Embedding.canonical_text)
        .filter(Embedding.owner_type == "profile")
    )

    if exclude_user_id:
        stmt = stmt.filter(Embedding.owner_id != exclude_user_id)

    stmt = stmt.order_by(dist_expr.asc()).limit(limit)

    results = db.execute(stmt).fetchall()

    matches = []
    for row in results:
        sim = float(row[1])
        if sim >= min_similarity:
            matches.append({
                "user_id": row[0],
                "similarity": sim,
                "canonical_text": row[2],
            })

    return matches
