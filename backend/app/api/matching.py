from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_active_user, get_db
from app.models.user import User
from app.schemas.matching import FindMatchesRequest, MatchingResponse
from app.services.matching_service import find_candidate_matches

router = APIRouter()


@router.post(
    "/find-matches",
    response_model=MatchingResponse,
    status_code=status.HTTP_200_OK,
    summary="Find candidate helpers using hybrid semantic, location, and experience matching",
)
def find_matches(
    payload: FindMatchesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> MatchingResponse:
    """
    Execute real hybrid matching for an authenticated user's request.
    - Requires authenticated user to own the request.
    - Uses native PostgreSQL pgvector cosine similarity.
    - Uses real GPS coordinates and Haversine distance.
    - Uses real profile tenure and skill records.
    - Excludes requesting user.
    - Does NOT manufacture mock values for reputation or availability.
    - Calculates a mathematically normalized final score across active dimensions.
    """
    return find_candidate_matches(
        db=db,
        request_id=payload.request_id,
        requesting_user=current_user,
        weights=payload.weights,
        limit=payload.limit or 10,
        min_score=payload.min_score or 0.0,
    )
