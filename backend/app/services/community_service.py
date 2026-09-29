import hashlib
from datetime import datetime, timezone
from typing import List, Optional, Set, Tuple
import uuid

from fastapi import HTTPException, status
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from app.models.community import (
    CommunityAnswer,
    CommunityAnswerVote,
    CommunityQuestion,
    QuestionCategory,
    QuestionStatus,
    VoteType,
)
from app.models.connection import Connection, ConnectionStatus
from app.models.embedding import Embedding
from app.models.request import Request
from app.models.review import Review
from app.models.user import User
from app.schemas.community import (
    AnswerCreate,
    AnswerListResponse,
    AnswerResponse,
    AnswerUpdate,
    AuthorTrustSignals,
    CommunitySearchItem,
    CommunitySearchResponse,
    QuestionAuthorSummary,
    QuestionCreate,
    QuestionDetailResponse,
    QuestionListResponse,
    QuestionResponse,
    QuestionUpdate,
    RequestCommunityKnowledgeItem,
    RequestCommunityKnowledgeResponse,
    VoteResponse,
)
from app.services.embedding_service import EmbeddingService
from app.services.review_service import get_user_reputation
from app.services.safety_service import get_blocked_user_ids


# ============================================================================
# Helpers
# ============================================================================

def _compute_canonical_text(
    title: str, body: str, category: str, city: Optional[str], area: Optional[str]
) -> str:
    loc_parts = [p for p in [area, city] if p]
    loc_str = ", ".join(loc_parts) if loc_parts else "India"
    return f"Title: {title.strip()}\nCategory: {category}\nLocation: {loc_str}\nBody: {body.strip()}"


def _compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _get_author_trust_signals(db: Session, author: User) -> AuthorTrustSignals:
    reputation = get_user_reputation(db, author.id)
    completed_count = (
        db.query(func.count(Connection.id))
        .filter(
            Connection.status == ConnectionStatus.COMPLETED.value,
            or_(Connection.helper_id == author.id, Connection.requester_id == author.id),
        )
        .scalar()
        or 0
    )
    return AuthorTrustSignals(
        user_id=author.id,
        name=author.name,
        average_rating=reputation.average_rating,
        review_count=reputation.review_count,
        completed_interactions_count=completed_count,
        reputation_status=reputation.status,
    )


def _hydrate_answer_response(
    db: Session,
    answer: CommunityAnswer,
    current_user: Optional[User] = None,
) -> AnswerResponse:
    # Vote counts
    helpful_count = (
        db.query(func.count(CommunityAnswerVote.id))
        .filter(
            CommunityAnswerVote.answer_id == answer.id,
            CommunityAnswerVote.vote == VoteType.HELPFUL.value,
        )
        .scalar()
        or 0
    )
    not_helpful_count = (
        db.query(func.count(CommunityAnswerVote.id))
        .filter(
            CommunityAnswerVote.answer_id == answer.id,
            CommunityAnswerVote.vote == VoteType.NOT_HELPFUL.value,
        )
        .scalar()
        or 0
    )

    user_vote = None
    if current_user:
        v = (
            db.query(CommunityAnswerVote)
            .filter(
                CommunityAnswerVote.answer_id == answer.id,
                CommunityAnswerVote.voter_id == current_user.id,
            )
            .first()
        )
        if v:
            user_vote = VoteType(v.vote)

    author_user = db.query(User).filter(User.id == answer.author_id).first()
    author_summary = (
        QuestionAuthorSummary(id=author_user.id, name=author_user.name)
        if author_user
        else None
    )
    trust_signals = _get_author_trust_signals(db, author_user) if author_user else None

    return AnswerResponse(
        id=answer.id,
        question_id=answer.question_id,
        author_id=answer.author_id,
        author=author_summary,
        author_trust_signals=trust_signals,
        body=answer.body,
        is_accepted=answer.is_accepted,
        accepted_at=answer.accepted_at,
        helpful_votes=helpful_count,
        not_helpful_votes=not_helpful_count,
        user_vote=user_vote,
        created_at=answer.created_at,
        updated_at=answer.updated_at,
    )


def _hydrate_question_response(
    db: Session, question: CommunityQuestion
) -> QuestionResponse:
    author = db.query(User).filter(User.id == question.author_id).first()
    author_summary = (
        QuestionAuthorSummary(id=author.id, name=author.name) if author else None
    )

    answers_count = (
        db.query(func.count(CommunityAnswer.id))
        .filter(CommunityAnswer.question_id == question.id)
        .scalar()
        or 0
    )
    has_accepted = (
        db.query(CommunityAnswer)
        .filter(
            CommunityAnswer.question_id == question.id,
            CommunityAnswer.is_accepted == True,  # noqa: E712
        )
        .first()
        is not None
    )

    return QuestionResponse(
        id=question.id,
        author_id=question.author_id,
        author=author_summary,
        title=question.title,
        body=question.body,
        category=QuestionCategory(question.category),
        status=QuestionStatus(question.status),
        city=question.city,
        area=question.area,
        answers_count=answers_count,
        has_accepted_answer=has_accepted,
        created_at=question.created_at,
        updated_at=question.updated_at,
    )


# ============================================================================
# Question Services
# ============================================================================

def create_question(
    db: Session, author: User, payload: QuestionCreate
) -> QuestionResponse:
    if not author.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Suspended accounts cannot post community questions.",
        )

    now = datetime.now(timezone.utc)
    question = CommunityQuestion(
        id=uuid.uuid4(),
        author_id=author.id,
        title=payload.title.strip(),
        body=payload.body.strip(),
        category=payload.category.value,
        status=QuestionStatus.OPEN.value,
        city=payload.city.strip() if payload.city else None,
        area=payload.area.strip() if payload.area else None,
        created_at=now,
        updated_at=now,
    )
    db.add(question)
    db.flush()

    # Generate semantic embedding in generic embeddings table
    canonical_text = _compute_canonical_text(
        question.title, question.body, question.category, question.city, question.area
    )
    src_hash = _compute_hash(canonical_text)
    try:
        embedding_service = EmbeddingService()
        vector = embedding_service.embed_text(canonical_text)
        emb = Embedding(
            id=uuid.uuid4(),
            owner_type="community_question",
            owner_id=question.id,
            embedding_type="semantic_dense",
            model_name=embedding_service.model_name,
            dimension=embedding_service.dimension,
            source_hash=src_hash,
            embedding=vector,
            canonical_text=canonical_text,
            created_at=now,
            updated_at=now,
        )
        db.add(emb)
    except Exception as exc:
        # Embedding failure should not crash question creation if model is offline,
        # but in test/prod it logs and continues
        pass

    db.commit()
    db.refresh(question)
    return _hydrate_question_response(db, question)


def list_questions(
    db: Session,
    current_user: Optional[User] = None,
    q: Optional[str] = None,
    category: Optional[QuestionCategory] = None,
    city: Optional[str] = None,
    area: Optional[str] = None,
    status_filter: Optional[QuestionStatus] = None,
    author_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 20,
) -> QuestionListResponse:
    query = db.query(CommunityQuestion)

    # Safety: exclude blocked users
    if current_user:
        blocked_ids = get_blocked_user_ids(db, current_user.id)
        if blocked_ids:
            query = query.filter(~CommunityQuestion.author_id.in_(list(blocked_ids)))

    if q and q.strip():
        search_term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                CommunityQuestion.title.ilike(search_term),
                CommunityQuestion.body.ilike(search_term),
            )
        )
    if category:
        query = query.filter(CommunityQuestion.category == category.value)
    if city:
        query = query.filter(CommunityQuestion.city.ilike(f"%{city.strip()}%"))
    if area:
        query = query.filter(CommunityQuestion.area.ilike(f"%{area.strip()}%"))
    if status_filter:
        query = query.filter(CommunityQuestion.status == status_filter.value)
    if author_id:
        query = query.filter(CommunityQuestion.author_id == author_id)

    total = query.count()
    questions = (
        query.order_by(desc(CommunityQuestion.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )

    return QuestionListResponse(
        total=total,
        questions=[_hydrate_question_response(db, q) for q in questions],
    )


def get_question_detail(
    db: Session, question_id: uuid.UUID, current_user: Optional[User] = None
) -> QuestionDetailResponse:
    question = (
        db.query(CommunityQuestion)
        .filter(CommunityQuestion.id == question_id)
        .first()
    )
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community question not found.",
        )

    # Safety: check if author is blocked
    if current_user:
        blocked_ids = get_blocked_user_ids(db, current_user.id)
        if question.author_id in blocked_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot view content from this user due to safety blocking.",
            )

    base_resp = _hydrate_question_response(db, question)

    # Fetch answers
    answers_query = db.query(CommunityAnswer).filter(
        CommunityAnswer.question_id == question.id
    )
    if current_user:
        blocked_ids = get_blocked_user_ids(db, current_user.id)
        if blocked_ids:
            answers_query = answers_query.filter(
                ~CommunityAnswer.author_id.in_(list(blocked_ids))
            )

    answers = (
        answers_query.order_by(
            desc(CommunityAnswer.is_accepted),
            desc(CommunityAnswer.created_at),
        ).all()
    )

    hydrated_answers = [
        _hydrate_answer_response(db, a, current_user) for a in answers
    ]

    # Sort answers: accepted first, then net helpful votes descending
    hydrated_answers.sort(
        key=lambda a: (
            1 if a.is_accepted else 0,
            a.helpful_votes - a.not_helpful_votes,
        ),
        reverse=True,
    )

    return QuestionDetailResponse(
        **base_resp.model_dump(),
        answers=hydrated_answers,
    )


def update_question(
    db: Session,
    question_id: uuid.UUID,
    current_user: User,
    payload: QuestionUpdate,
) -> QuestionResponse:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Suspended accounts cannot modify community content.",
        )

    question = (
        db.query(CommunityQuestion)
        .filter(CommunityQuestion.id == question_id)
        .first()
    )
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community question not found.",
        )

    if question.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit questions you authored.",
        )

    content_changed = False
    if payload.title is not None and payload.title.strip() != question.title:
        question.title = payload.title.strip()
        content_changed = True
    if payload.body is not None and payload.body.strip() != question.body:
        question.body = payload.body.strip()
        content_changed = True
    if payload.category is not None and payload.category.value != question.category:
        question.category = payload.category.value
        content_changed = True
    if payload.city is not None and payload.city.strip() != (question.city or ""):
        question.city = payload.city.strip() or None
        content_changed = True
    if payload.area is not None and payload.area.strip() != (question.area or ""):
        question.area = payload.area.strip() or None
        content_changed = True
    if payload.status is not None:
        question.status = payload.status.value

    now = datetime.now(timezone.utc)
    question.updated_at = now

    # Regenerate embedding if content changed
    if content_changed:
        canonical = _compute_canonical_text(
            question.title, question.body, question.category, question.city, question.area
        )
        src_hash = _compute_hash(canonical)
        emb = (
            db.query(Embedding)
            .filter(
                Embedding.owner_type == "community_question",
                Embedding.owner_id == question.id,
            )
            .first()
        )
        if emb:
            if emb.source_hash != src_hash:
                emb.canonical_text = canonical
                emb.source_hash = src_hash
                emb.embedding = EmbeddingService().embed_text(canonical)
                emb.updated_at = now
        else:
            embedding_service = EmbeddingService()
            new_emb = Embedding(
                id=uuid.uuid4(),
                owner_type="community_question",
                owner_id=question.id,
                embedding_type="semantic_dense",
                model_name=embedding_service.model_name,
                dimension=embedding_service.dimension,
                source_hash=src_hash,
                embedding=embedding_service.embed_text(canonical),
                canonical_text=canonical,
                created_at=now,
                updated_at=now,
            )
            db.add(new_emb)

    db.commit()
    db.refresh(question)
    return _hydrate_question_response(db, question)


def delete_question(
    db: Session, question_id: uuid.UUID, current_user: User
) -> None:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Suspended accounts cannot delete community content.",
        )

    question = (
        db.query(CommunityQuestion)
        .filter(CommunityQuestion.id == question_id)
        .first()
    )
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community question not found.",
        )

    if question.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete questions you authored.",
        )

    # Delete embeddings
    db.query(Embedding).filter(
        Embedding.owner_type == "community_question",
        Embedding.owner_id == question.id,
    ).delete(synchronize_session=False)

    db.delete(question)
    db.commit()


# ============================================================================
# Answer Services
# ============================================================================

def create_answer(
    db: Session, question_id: uuid.UUID, author: User, payload: AnswerCreate
) -> AnswerResponse:
    if not author.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Suspended accounts cannot post community answers.",
        )

    question = (
        db.query(CommunityQuestion)
        .filter(CommunityQuestion.id == question_id)
        .first()
    )
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community question not found.",
        )

    if question.status == QuestionStatus.CLOSED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot answer a closed community question.",
        )

    # Safety: check if author is blocked
    blocked_ids = get_blocked_user_ids(db, author.id)
    if question.author_id in blocked_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot interact with this question due to safety blocking.",
        )

    now = datetime.now(timezone.utc)
    answer = CommunityAnswer(
        id=uuid.uuid4(),
        question_id=question.id,
        author_id=author.id,
        body=payload.body.strip(),
        is_accepted=False,
        created_at=now,
        updated_at=now,
    )
    db.add(answer)
    db.commit()
    db.refresh(answer)

    return _hydrate_answer_response(db, answer, author)


def update_answer(
    db: Session, answer_id: uuid.UUID, current_user: User, payload: AnswerUpdate
) -> AnswerResponse:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Suspended accounts cannot modify answers.",
        )

    answer = (
        db.query(CommunityAnswer).filter(CommunityAnswer.id == answer_id).first()
    )
    if not answer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community answer not found.",
        )

    if answer.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit answers you authored.",
        )

    answer.body = payload.body.strip()
    answer.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(answer)

    return _hydrate_answer_response(db, answer, current_user)


def delete_answer(
    db: Session, answer_id: uuid.UUID, current_user: User
) -> None:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Suspended accounts cannot delete answers.",
        )

    answer = (
        db.query(CommunityAnswer).filter(CommunityAnswer.id == answer_id).first()
    )
    if not answer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community answer not found.",
        )

    if answer.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete answers you authored.",
        )

    db.delete(answer)
    db.commit()


def accept_answer(
    db: Session, question_id: uuid.UUID, answer_id: uuid.UUID, current_user: User
) -> AnswerResponse:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Suspended accounts cannot perform this action.",
        )

    question = (
        db.query(CommunityQuestion)
        .filter(CommunityQuestion.id == question_id)
        .first()
    )
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community question not found.",
        )

    if question.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the question author can accept an answer.",
        )

    answer = (
        db.query(CommunityAnswer)
        .filter(
            CommunityAnswer.id == answer_id,
            CommunityAnswer.question_id == question_id,
        )
        .first()
    )
    if not answer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Answer not found for this question.",
        )

    now = datetime.now(timezone.utc)

    # Toggle off if already accepted
    if answer.is_accepted:
        answer.is_accepted = False
        answer.accepted_at = None
        question.status = QuestionStatus.OPEN.value
    else:
        # Unaccept all other answers for this question
        db.query(CommunityAnswer).filter(
            CommunityAnswer.question_id == question_id,
            CommunityAnswer.is_accepted == True,  # noqa: E712
        ).update(
            {"is_accepted": False, "accepted_at": None},
            synchronize_session=False,
        )

        answer.is_accepted = True
        answer.accepted_at = now
        question.status = QuestionStatus.RESOLVED.value

    answer.updated_at = now
    question.updated_at = now
    db.commit()
    db.refresh(answer)
    db.refresh(question)

    return _hydrate_answer_response(db, answer, current_user)


# ============================================================================
# Voting Services
# ============================================================================

def vote_answer(
    db: Session, answer_id: uuid.UUID, voter: User, vote_type: VoteType
) -> VoteResponse:
    if not voter.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Suspended accounts cannot vote.",
        )

    answer = (
        db.query(CommunityAnswer).filter(CommunityAnswer.id == answer_id).first()
    )
    if not answer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community answer not found.",
        )

    if answer.author_id == voter.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authors cannot vote on their own answers.",
        )

    # Check bidirectional block
    blocked_ids = get_blocked_user_ids(db, voter.id)
    if answer.author_id in blocked_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot vote on content by this user due to safety blocking.",
        )

    # Check bidirectional block on question author as well
    question = (
        db.query(CommunityQuestion)
        .filter(CommunityQuestion.id == answer.question_id)
        .first()
    )
    if question and question.author_id in blocked_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot vote on content for this question due to safety blocking.",
        )

    now = datetime.now(timezone.utc)
    existing_vote = (
        db.query(CommunityAnswerVote)
        .filter(
            CommunityAnswerVote.answer_id == answer.id,
            CommunityAnswerVote.voter_id == voter.id,
        )
        .first()
    )

    if existing_vote:
        if existing_vote.vote != vote_type.value:
            existing_vote.vote = vote_type.value
            existing_vote.updated_at = now
    else:
        new_vote = CommunityAnswerVote(
            id=uuid.uuid4(),
            answer_id=answer.id,
            voter_id=voter.id,
            vote=vote_type.value,
            created_at=now,
            updated_at=now,
        )
        db.add(new_vote)

    db.commit()

    helpful_count = (
        db.query(func.count(CommunityAnswerVote.id))
        .filter(
            CommunityAnswerVote.answer_id == answer.id,
            CommunityAnswerVote.vote == VoteType.HELPFUL.value,
        )
        .scalar()
        or 0
    )
    not_helpful_count = (
        db.query(func.count(CommunityAnswerVote.id))
        .filter(
            CommunityAnswerVote.answer_id == answer.id,
            CommunityAnswerVote.vote == VoteType.NOT_HELPFUL.value,
        )
        .scalar()
        or 0
    )

    return VoteResponse(
        answer_id=answer.id,
        voter_id=voter.id,
        vote=vote_type,
        helpful_votes=helpful_count,
        not_helpful_votes=not_helpful_count,
    )


def remove_vote(
    db: Session, answer_id: uuid.UUID, voter: User
) -> VoteResponse:
    if not voter.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Suspended accounts cannot modify votes.",
        )

    answer = (
        db.query(CommunityAnswer).filter(CommunityAnswer.id == answer_id).first()
    )
    if not answer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community answer not found.",
        )

    # Check bidirectional block
    blocked_ids = get_blocked_user_ids(db, voter.id)
    if answer.author_id in blocked_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot interact with content by this user due to safety blocking.",
        )

    db.query(CommunityAnswerVote).filter(
        CommunityAnswerVote.answer_id == answer.id,
        CommunityAnswerVote.voter_id == voter.id,
    ).delete(synchronize_session=False)
    db.commit()

    helpful_count = (
        db.query(func.count(CommunityAnswerVote.id))
        .filter(
            CommunityAnswerVote.answer_id == answer.id,
            CommunityAnswerVote.vote == VoteType.HELPFUL.value,
        )
        .scalar()
        or 0
    )
    not_helpful_count = (
        db.query(func.count(CommunityAnswerVote.id))
        .filter(
            CommunityAnswerVote.answer_id == answer.id,
            CommunityAnswerVote.vote == VoteType.NOT_HELPFUL.value,
        )
        .scalar()
        or 0
    )

    return VoteResponse(
        answer_id=answer.id,
        voter_id=voter.id,
        vote=None,
        helpful_votes=helpful_count,
        not_helpful_votes=not_helpful_count,
    )


# ============================================================================
# Semantic Search & Request Intelligence
# ============================================================================

def search_community(
    db: Session,
    query_text: str,
    current_user: Optional[User] = None,
    category: Optional[QuestionCategory] = None,
    city: Optional[str] = None,
    area: Optional[str] = None,
    limit: int = 15,
    skip: int = 0,
) -> CommunitySearchResponse:
    clean_q = query_text.strip()
    if not clean_q:
        return CommunitySearchResponse(query=query_text, total=0, results=[])

    # 1. Embed query
    embedding_service = EmbeddingService()
    try:
        q_vector = embedding_service.embed_text(clean_q)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic embedding generation failed: {exc}",
        )

    # 2. Vector distance expression
    distance_expr = Embedding.embedding.cosine_distance(q_vector)

    query = (
        db.query(CommunityQuestion, distance_expr.label("distance"))
        .join(Embedding, Embedding.owner_id == CommunityQuestion.id)
        .filter(Embedding.owner_type == "community_question")
    )

    # 3. Safety: filter blocked users
    if current_user:
        blocked_ids = get_blocked_user_ids(db, current_user.id)
        if blocked_ids:
            query = query.filter(~CommunityQuestion.author_id.in_(list(blocked_ids)))

    # 4. Filters
    if category:
        query = query.filter(CommunityQuestion.category == category.value)
    if city:
        query = query.filter(CommunityQuestion.city.ilike(f"%{city.strip()}%"))
    if area:
        query = query.filter(CommunityQuestion.area.ilike(f"%{area.strip()}%"))

    # Order by similarity
    results_raw = query.order_by("distance").offset(skip).limit(limit).all()

    items: List[CommunitySearchItem] = []
    for q, dist in results_raw:
        # Distance range for cosine is [0, 2], where 0 is identical
        sim = max(0.0, round(1.0 - float(dist), 4))
        if sim < 0.25:
            continue
        q_resp = _hydrate_question_response(db, q)

        # Get top or accepted answer
        top_ans = (
            db.query(CommunityAnswer)
            .filter(CommunityAnswer.question_id == q.id)
            .order_by(
                desc(CommunityAnswer.is_accepted),
                desc(CommunityAnswer.created_at),
            )
            .first()
        )
        top_ans_resp = (
            _hydrate_answer_response(db, top_ans, current_user) if top_ans else None
        )

        items.append(
            CommunitySearchItem(
                question=q_resp,
                similarity_score=sim,
                top_answer=top_ans_resp,
            )
        )

    return CommunitySearchResponse(
        query=clean_q,
        total=len(items),
        results=items,
    )


def get_community_knowledge_for_request(
    db: Session,
    request_id: uuid.UUID,
    current_user: User,
    limit: int = 5,
) -> RequestCommunityKnowledgeResponse:
    # 1. Fetch request
    req = db.query(Request).filter(Request.id == request_id).first()
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found.",
        )

    # Ownership check: prevent IDOR access to private requests
    if req.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access community knowledge for this request.",
        )

    # 2. Extract text and location
    search_text = req.raw_text
    city = req.city
    area = req.area

    # Search community knowledge
    search_res = search_community(
        db=db,
        query_text=search_text,
        current_user=current_user,
        city=city,
        area=area,
        limit=limit,
    )

    items: List[RequestCommunityKnowledgeItem] = []
    for r in search_res.results:
        # Filter out very distant / irrelevant matches (threshold 0.25 similarity)
        if r.similarity_score >= 0.25:
            items.append(
                RequestCommunityKnowledgeItem(
                    question=r.question,
                    relevance_score=r.similarity_score,
                    accepted_or_top_answer=r.top_answer,
                )
            )

    return RequestCommunityKnowledgeResponse(
        request_id=req.id,
        total=len(items),
        items=items,
    )
