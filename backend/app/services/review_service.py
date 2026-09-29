from datetime import datetime, timezone
from typing import List, Optional, Tuple
import uuid
from fastapi import HTTPException, status
from sqlalchemy import desc, func
from sqlalchemy.orm import Session
from app.models.connection import Connection, ConnectionStatus
from app.models.review import Review
from app.models.user import User
from app.schemas.connection import ConnectionResponse
from app.schemas.review import (
    ReputationSummary,
    ReviewCreate,
    ReviewListResponse,
    ReviewResponse,
)
from app.services.connection_service import _hydrate_connection_response


def complete_connection(
    db: Session,
    connection_id: uuid.UUID,
    current_user: User,
) -> ConnectionResponse:
    """
    Mark an ACCEPTED connection as COMPLETED.
    - Either participant (requester or helper) may mark as completed.
    - Non-participants receive 403 Forbidden.
    - Idempotent: If already COMPLETED, returns existing completed state.
    - Terminal: Cannot complete from PENDING, DECLINED, or CANCELLED.
    """
    conn = db.query(Connection).filter(Connection.id == connection_id).first()
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found.",
        )

    # 1. Authorization: user must be participant
    if conn.requester_id != current_user.id and conn.helper_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only participants in this connection can mark it as completed.",
        )

    # 2. Idempotency: if already completed, return safely
    if conn.status == ConnectionStatus.COMPLETED.value:
        return _hydrate_connection_response(db, conn)

    # 3. Transition check: only ACCEPTED can become COMPLETED
    if conn.status != ConnectionStatus.ACCEPTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only accepted connections can be completed. Current status: {conn.status}.",
        )

    now = datetime.now(timezone.utc)
    conn.status = ConnectionStatus.COMPLETED.value
    conn.completed_at = now
    conn.updated_at = now

    db.commit()
    db.refresh(conn)
    return _hydrate_connection_response(db, conn)


def format_review_response(review: Review) -> ReviewResponse:
    reviewer_name = review.reviewer.name if review.reviewer else "Community Member"
    reviewee_name = review.reviewee.name if review.reviewee else "Community Member"

    return ReviewResponse(
        id=review.id,
        connection_id=review.connection_id,
        reviewer_id=review.reviewer_id,
        reviewer_name=reviewer_name,
        reviewee_id=reviewee_id if (reviewee_id := review.reviewee_id) else review.reviewee_id,
        reviewee_name=reviewee_name,
        rating=review.rating,
        comment=review.comment,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


def create_review(
    db: Session,
    connection_id: uuid.UUID,
    current_user: User,
    payload: ReviewCreate,
) -> ReviewResponse:
    """
    Create a review for a completed connection.
    - Connection must be COMPLETED.
    - Current user must be a participant.
    - Cannot review self.
    - Duplicate review for the same connection by the same reviewer returns 409 Conflict.
    """
    conn = db.query(Connection).filter(Connection.id == connection_id).first()
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found.",
        )

    # 1. Authorization: participant check
    if conn.requester_id != current_user.id and conn.helper_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only participants in this connection can submit a review.",
        )

    # 2. Connection must be COMPLETED
    if conn.status != ConnectionStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A review can only be submitted after the interaction has been completed. Current status: {conn.status}.",
        )

    # 3. Determine reviewee
    if current_user.id == conn.requester_id:
        reviewee_id = conn.helper_id
    else:
        reviewee_id = conn.requester_id

    # 4. Self-review check
    if current_user.id == reviewee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot review yourself.",
        )

    # 5. Duplicate review check (Unique constraint protection)
    existing = (
        db.query(Review)
        .filter(
            Review.connection_id == conn.id,
            Review.reviewer_id == current_user.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already submitted a review for this completed connection.",
        )

    now = datetime.now(timezone.utc)
    review = Review(
        id=uuid.uuid4(),
        connection_id=conn.id,
        reviewer_id=current_user.id,
        reviewee_id=reviewee_id,
        rating=payload.rating,
        comment=payload.comment,
        created_at=now,
        updated_at=now,
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    return format_review_response(review)


def get_connection_reviews(
    db: Session,
    connection_id: uuid.UUID,
    current_user: User,
) -> List[ReviewResponse]:
    """
    Get all reviews submitted for a specific connection.
    Only participants or system queries can view connection reviews.
    """
    conn = db.query(Connection).filter(Connection.id == connection_id).first()
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found.",
        )

    if conn.requester_id != current_user.id and conn.helper_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this connection.",
        )

    reviews = (
        db.query(Review)
        .filter(Review.connection_id == conn.id)
        .order_by(desc(Review.created_at))
        .all()
    )
    return [format_review_response(r) for r in reviews]


def get_user_reviews(
    db: Session,
    user_id: uuid.UUID,
    limit: int = 50,
    skip: int = 0,
) -> ReviewListResponse:
    """
    Retrieve public reviews received by a user.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    query = db.query(Review).filter(Review.reviewee_id == user_id)
    total = query.count()
    reviews = query.order_by(desc(Review.created_at)).offset(skip).limit(limit).all()

    return ReviewListResponse(
        total=total,
        reviews=[format_review_response(r) for r in reviews],
    )


def get_user_reputation(
    db: Session,
    user_id: uuid.UUID,
) -> ReputationSummary:
    """
    Calculate real reputation metrics from reviews received by the user.
    If review_count == 0, average_rating is None (no fake defaults).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    count = (
        db.query(func.count(Review.id))
        .filter(Review.reviewee_id == user_id)
        .scalar()
        or 0
    )

    if count == 0:
        return ReputationSummary(
            user_id=user_id,
            average_rating=None,
            review_count=0,
            status="UNAVAILABLE",
        )

    avg_rating = (
        db.query(func.avg(Review.rating))
        .filter(Review.reviewee_id == user_id)
        .scalar()
    )

    avg_val = round(float(avg_rating), 2) if avg_rating is not None else None

    return ReputationSummary(
        user_id=user_id,
        average_rating=avg_val,
        review_count=count,
        status="AVAILABLE",
    )
