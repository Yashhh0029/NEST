from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.models.community import QuestionCategory, QuestionStatus, VoteType


# Trust Signals for Answer Authors
class AuthorTrustSignals(BaseModel):
    user_id: uuid.UUID
    name: str
    average_rating: Optional[float] = None
    review_count: int = 0
    completed_interactions_count: int = 0
    reputation_status: str = "UNAVAILABLE"  # "ACTIVE" or "UNAVAILABLE"

    model_config = ConfigDict(from_attributes=True)


class QuestionAuthorSummary(BaseModel):
    id: uuid.UUID
    name: str

    model_config = ConfigDict(from_attributes=True)


# Question Schemas
class QuestionCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=255)
    body: str = Field(..., min_length=10, max_length=10000)
    category: QuestionCategory
    city: Optional[str] = Field(None, max_length=100)
    area: Optional[str] = Field(None, max_length=100)


class QuestionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=5, max_length=255)
    body: Optional[str] = Field(None, min_length=10, max_length=10000)
    category: Optional[QuestionCategory] = None
    city: Optional[str] = Field(None, max_length=100)
    area: Optional[str] = Field(None, max_length=100)
    status: Optional[QuestionStatus] = None


class QuestionResponse(BaseModel):
    id: uuid.UUID
    author_id: uuid.UUID
    author: Optional[QuestionAuthorSummary] = None
    title: str
    body: str
    category: QuestionCategory
    status: QuestionStatus
    city: Optional[str] = None
    area: Optional[str] = None
    answers_count: int = 0
    has_accepted_answer: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Answer Schemas
class AnswerCreate(BaseModel):
    body: str = Field(..., min_length=5, max_length=10000)


class AnswerUpdate(BaseModel):
    body: str = Field(..., min_length=5, max_length=10000)


class AnswerResponse(BaseModel):
    id: uuid.UUID
    question_id: uuid.UUID
    author_id: uuid.UUID
    author: Optional[QuestionAuthorSummary] = None
    author_trust_signals: Optional[AuthorTrustSignals] = None
    body: str
    is_accepted: bool = False
    accepted_at: Optional[datetime] = None
    helpful_votes: int = 0
    not_helpful_votes: int = 0
    user_vote: Optional[VoteType] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuestionDetailResponse(QuestionResponse):
    answers: List[AnswerResponse] = []


class QuestionListResponse(BaseModel):
    total: int
    questions: List[QuestionResponse]


class AnswerListResponse(BaseModel):
    total: int
    answers: List[AnswerResponse]


# Voting Schemas
class VotePayload(BaseModel):
    vote: Optional[VoteType] = None
    vote_type: Optional[VoteType] = None

    def get_vote(self) -> VoteType:
        v = self.vote or self.vote_type
        if not v:
            raise ValueError("vote or vote_type is required")
        return v


class VoteResponse(BaseModel):
    answer_id: uuid.UUID
    voter_id: uuid.UUID
    vote: Optional[VoteType] = None
    helpful_votes: int
    not_helpful_votes: int


# Search Schemas
class CommunitySearchItem(BaseModel):
    question: QuestionResponse
    similarity_score: float
    top_answer: Optional[AnswerResponse] = None


class CommunitySearchResponse(BaseModel):
    query: str
    total: int
    results: List[CommunitySearchItem]


# Request Integration Schemas
class RequestCommunityKnowledgeItem(BaseModel):
    question: QuestionResponse
    relevance_score: float
    accepted_or_top_answer: Optional[AnswerResponse] = None


class RequestCommunityKnowledgeResponse(BaseModel):
    request_id: uuid.UUID
    total: int
    items: List[RequestCommunityKnowledgeItem]
