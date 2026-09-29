import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.database import Base


class QuestionCategory(str, enum.Enum):
    ACCOMMODATION = "ACCOMMODATION"
    TRANSPORT = "TRANSPORT"
    FOOD = "FOOD"
    SAFETY = "SAFETY"
    JOBS = "JOBS"
    EDUCATION = "EDUCATION"
    HEALTHCARE = "HEALTHCARE"
    LOCAL_SERVICES = "LOCAL_SERVICES"
    COST_OF_LIVING = "COST_OF_LIVING"
    DAILY_LIFE = "DAILY_LIFE"
    OTHER = "OTHER"


class QuestionStatus(str, enum.Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class VoteType(str, enum.Enum):
    HELPFUL = "HELPFUL"
    NOT_HELPFUL = "NOT_HELPFUL"


class CommunityQuestion(Base):
    __tablename__ = "community_questions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        nullable=False,
    )
    author_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False, index=True)
    body = Column(Text, nullable=False)
    city = Column(String(100), nullable=True, index=True)
    area = Column(String(100), nullable=True, index=True)
    category = Column(
        Enum(
            QuestionCategory,
            name="question_category",
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        index=True,
    )
    status = Column(
        Enum(
            QuestionStatus,
            name="question_status",
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=QuestionStatus.OPEN,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    author = relationship("User", foreign_keys=[author_id])
    answers = relationship(
        "CommunityAnswer",
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="desc(CommunityAnswer.created_at)",
    )


class CommunityAnswer(Base):
    __tablename__ = "community_answers"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        nullable=False,
    )
    question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("community_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    body = Column(Text, nullable=False)
    is_accepted = Column(Boolean, nullable=False, default=False, index=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    question = relationship("CommunityQuestion", back_populates="answers")
    author = relationship("User", foreign_keys=[author_id])
    votes = relationship(
        "CommunityAnswerVote",
        back_populates="answer",
        cascade="all, delete-orphan",
    )


class CommunityAnswerVote(Base):
    __tablename__ = "community_answer_votes"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        nullable=False,
    )
    answer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("community_answers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    voter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vote = Column(
        Enum(
            VoteType,
            name="vote_type",
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("answer_id", "voter_id", name="uq_answer_voter"),
    )

    answer = relationship("CommunityAnswer", back_populates="votes")
    voter = relationship("User", foreign_keys=[voter_id])
