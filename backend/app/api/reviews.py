import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.review import ReputationSummary, ReviewListResponse
from app.services import review_service

router = APIRouter(prefix="/users", tags=["Reviews & Reputation"])


@router.get(
    "/{user_id}/reviews",
    response_model=ReviewListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get public reviews for a user",
)
def get_user_reviews(
    user_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReviewListResponse:
    """
    Retrieve all public reviews received by a user.
    """
    return review_service.get_user_reviews(db, user_id, limit=limit, skip=skip)


@router.get(
    "/{user_id}/reputation",
    response_model=ReputationSummary,
    status_code=status.HTTP_200_OK,
    summary="Get reputation summary for a user",
)
def get_user_reputation(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReputationSummary:
    """
    Calculate and retrieve real reputation metrics (average rating and review count).
    Returns null average_rating for users with zero reviews.
    """
    return review_service.get_user_reputation(db, user_id)
