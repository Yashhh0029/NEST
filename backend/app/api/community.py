from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import (
    get_current_user,
    get_db,
    get_optional_current_user,
)
from app.models.community import QuestionCategory, QuestionStatus
from app.models.user import User
from app.schemas.community import (
    AnswerCreate,
    AnswerListResponse,
    AnswerResponse,
    AnswerUpdate,
    CommunitySearchResponse,
    QuestionCreate,
    QuestionDetailResponse,
    QuestionListResponse,
    QuestionResponse,
    QuestionUpdate,
    RequestCommunityKnowledgeResponse,
    VotePayload,
    VoteResponse,
)
from app.services import community_service

router = APIRouter(prefix="/community", tags=["Community Intelligence"])


# ============================================================================
# Question Endpoints
# ============================================================================

@router.post(
    "/questions",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a community question",
)
def create_question_endpoint(
    payload: QuestionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new community question with category and location context.
    Suspended accounts cannot create questions.
    Generates a dense semantic embedding for pgvector search.
    """
    return community_service.create_question(db, current_user, payload)


@router.get(
    "/questions",
    response_model=QuestionListResponse,
    summary="List community questions",
)
def list_questions_endpoint(
    q: Optional[str] = Query(None, description="Search keyword in title or body"),
    category: Optional[QuestionCategory] = Query(None, description="Filter by category"),
    city: Optional[str] = Query(None, description="Filter by city"),
    area: Optional[str] = Query(None, description="Filter by area / locality"),
    status: Optional[QuestionStatus] = Query(None, description="Filter by status (OPEN, RESOLVED, CLOSED)"),
    author_id: Optional[uuid.UUID] = Query(None, description="Filter by author ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """
    List community questions with filters and pagination.
    Excludes questions from users blocked by or who blocked the current user.
    """
    return community_service.list_questions(
        db=db,
        current_user=current_user,
        q=q,
        category=category,
        city=city,
        area=area,
        status_filter=status,
        author_id=author_id,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/questions/{question_id}",
    response_model=QuestionDetailResponse,
    summary="Get question detail with answers and trust signals",
)
def get_question_detail_endpoint(
    question_id: uuid.UUID,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve full question details including answers, author trust signals,
    and current user's vote state.
    """
    return community_service.get_question_detail(db, question_id, current_user)


@router.patch(
    "/questions/{question_id}",
    response_model=QuestionResponse,
    summary="Update a question (author only)",
)
def update_question_endpoint(
    question_id: uuid.UUID,
    payload: QuestionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update question content. Only the author can update their own questions.
    Regenerates semantic embeddings if content or location changes.
    """
    return community_service.update_question(db, question_id, current_user, payload)


@router.delete(
    "/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a question (author only)",
)
def delete_question_endpoint(
    question_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a question. Only the author can delete their own questions.
    Cascades answers, votes, and cleans up semantic embeddings.
    """
    community_service.delete_question(db, question_id, current_user)


# ============================================================================
# Answer Endpoints
# ============================================================================

@router.post(
    "/questions/{question_id}/answers",
    response_model=AnswerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Post an answer to a question",
)
def create_answer_endpoint(
    question_id: uuid.UUID,
    payload: AnswerCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Post an answer to a community question.
    Only authenticated, active users can answer.
    Closed questions cannot receive new answers.
    """
    return community_service.create_answer(db, question_id, current_user, payload)


@router.get(
    "/questions/{question_id}/answers",
    response_model=AnswerListResponse,
    summary="List answers for a question",
)
def list_answers_endpoint(
    question_id: uuid.UUID,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """
    List all answers for a question with trust signals and usefulness scores.
    """
    detail = community_service.get_question_detail(db, question_id, current_user)
    return AnswerListResponse(total=len(detail.answers), answers=detail.answers)


@router.patch(
    "/answers/{answer_id}",
    response_model=AnswerResponse,
    summary="Edit an answer (author only)",
)
def update_answer_endpoint(
    answer_id: uuid.UUID,
    payload: AnswerUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update answer body. Only the author can edit their own answer.
    """
    return community_service.update_answer(db, answer_id, current_user, payload)


@router.delete(
    "/answers/{answer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an answer (author only)",
)
def delete_answer_endpoint(
    answer_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete an answer. Only the author can delete their own answer.
    """
    community_service.delete_answer(db, answer_id, current_user)


@router.post(
    "/questions/{question_id}/accept/{answer_id}",
    response_model=AnswerResponse,
    summary="Mark an answer as accepted (question author only)",
)
@router.post(
    "/questions/{question_id}/answers/{answer_id}/accept",
    response_model=AnswerResponse,
    include_in_schema=False,
)
def accept_answer_endpoint(
    question_id: uuid.UUID,
    answer_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Mark an answer as accepted. Only the question author can accept an answer.
    Only one answer can be accepted per question; accepting an answer automatically
    unaccepts any previously accepted answer.
    """
    return community_service.accept_answer(db, question_id, answer_id, current_user)


# ============================================================================
# Voting Endpoints
# ============================================================================

@router.post(
    "/answers/{answer_id}/vote",
    response_model=VoteResponse,
    summary="Vote on answer usefulness (HELPFUL or NOT_HELPFUL)",
)
@router.post(
    "/questions/{question_id}/answers/{answer_id}/vote",
    response_model=VoteResponse,
    include_in_schema=False,
)
def vote_answer_endpoint(
    answer_id: uuid.UUID,
    payload: VotePayload,
    question_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Mark an answer as helpful or not helpful.
    Authors cannot vote on their own answers.
    Users can change their vote.
    """
    return community_service.vote_answer(db, answer_id, current_user, payload.get_vote())


@router.delete(
    "/answers/{answer_id}/vote",
    response_model=VoteResponse,
    summary="Remove vote on answer",
)
@router.delete(
    "/questions/{question_id}/answers/{answer_id}/vote",
    response_model=VoteResponse,
    include_in_schema=False,
)
def remove_vote_endpoint(
    answer_id: uuid.UUID,
    question_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove user's vote from an answer.
    """
    return community_service.remove_vote(db, answer_id, current_user)


# ============================================================================
# Semantic Search & Request Intelligence
# ============================================================================

@router.get(
    "/search",
    response_model=CommunitySearchResponse,
    summary="Semantic community knowledge search via pgvector",
)
def search_community_endpoint(
    q: str = Query(..., min_length=2, description="Search query string"),
    category: Optional[QuestionCategory] = Query(None, description="Optional category filter"),
    city: Optional[str] = Query(None, description="Optional city filter"),
    area: Optional[str] = Query(None, description="Optional area filter"),
    limit: int = Query(15, ge=1, le=50),
    skip: int = Query(0, ge=0),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """
    Perform semantic search across community questions using pgvector cosine distance.
    Filters by optional category, city, area, and excludes content by blocked users.
    Returns ranked questions with similarity scores and top answers.
    """
    return community_service.search_community(
        db=db,
        query_text=q,
        current_user=current_user,
        category=category,
        city=city,
        area=area,
        limit=limit,
        skip=skip,
    )


@router.get(
    "/for-request/{request_id}",
    response_model=RequestCommunityKnowledgeResponse,
    summary="Retrieve relevant community knowledge for a request",
)
def get_community_for_request_endpoint(
    request_id: uuid.UUID,
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Surface relevant community knowledge based on the user's actual stored request,
    extracted need, and location context. Returns honest empty results if none exist.
    """
    return community_service.get_community_knowledge_for_request(
        db=db,
        request_id=request_id,
        current_user=current_user,
        limit=limit,
    )
