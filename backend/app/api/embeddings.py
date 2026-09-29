import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.embedding import (
    EmbeddingResponse,
    SemanticSearchQuery,
    SemanticSearchResponse,
    SemanticSearchResultItem,
)
from app.services.embedding_repository import (
    search_similar_profiles,
    sync_user_profile_embedding,
    sync_user_request_embedding,
)
from app.services.embedding_service import embedding_service

router = APIRouter(prefix="/embeddings", tags=["Embeddings & Semantic Search"])


@router.post(
    "/profile/me",
    response_model=EmbeddingResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate or synchronize profile vector embedding",
    description="Builds canonical profile text, checks SHA-256 staleness, generates 384-dimensional vector, and stores in PostgreSQL pgvector.",
)
def embed_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EmbeddingResponse:
    """Synchronize authenticated user's profile embedding."""
    embedding, created_or_updated = sync_user_profile_embedding(db, current_user)
    return EmbeddingResponse(
        embedding_id=embedding.id,
        owner_type=embedding.owner_type,
        owner_id=embedding.owner_id,
        model_name=embedding.model_name,
        dimension=embedding.dimension,
        source_hash=embedding.source_hash,
        created_or_updated=created_or_updated,
        created_at=embedding.created_at,
    )


@router.post(
    "/request/{request_id}",
    response_model=EmbeddingResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate or synchronize request vector embedding",
    description="Builds canonical request text, enforces ownership, generates 384-dimensional vector, and stores in PostgreSQL pgvector.",
)
def embed_my_request(
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EmbeddingResponse:
    """Synchronize authenticated user's request embedding."""
    embedding, created_or_updated = sync_user_request_embedding(db, current_user, request_id)
    return EmbeddingResponse(
        embedding_id=embedding.id,
        owner_type=embedding.owner_type,
        owner_id=embedding.owner_id,
        model_name=embedding.model_name,
        dimension=embedding.dimension,
        source_hash=embedding.source_hash,
        created_or_updated=created_or_updated,
        created_at=embedding.created_at,
    )


@router.post(
    "/search/profiles",
    response_model=SemanticSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute semantic search against profile embeddings using pgvector",
    description="Embeds query text and runs native PostgreSQL pgvector cosine similarity search against stored profiles.",
)
def search_profiles_endpoint(
    payload: SemanticSearchQuery,
    db: Session = Depends(get_db),
) -> SemanticSearchResponse:
    """Perform real pgvector semantic search across profiles."""
    query_vector = embedding_service.embed_text(payload.query_text)
    raw_results = search_similar_profiles(
        db=db,
        query_embedding=query_vector,
        limit=payload.limit or 10,
        min_similarity=payload.min_similarity if payload.min_similarity is not None else 0.0,
    )

    items = [
        SemanticSearchResultItem(
            user_id=r["user_id"],
            similarity=round(r["similarity"], 4),
            canonical_text=r["canonical_text"],
        )
        for r in raw_results
    ]

    return SemanticSearchResponse(
        query=payload.query_text,
        total_matches=len(items),
        results=items,
    )
