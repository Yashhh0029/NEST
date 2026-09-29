import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from app.db.database import Base


class ReportReason(str, enum.Enum):
    HARASSMENT = "HARASSMENT"
    SPAM = "SPAM"
    SCAM = "SCAM"
    THREAT = "THREAT"
    INAPPROPRIATE_CONTENT = "INAPPROPRIATE_CONTENT"
    FAKE_PROFILE = "FAKE_PROFILE"
    SAFETY_CONCERN = "SAFETY_CONCERN"
    OTHER = "OTHER"


class ReportStatus(str, enum.Enum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class ModerationActionType(str, enum.Enum):
    REPORT_REVIEWED = "REPORT_REVIEWED"
    REPORT_RESOLVED = "REPORT_RESOLVED"
    REPORT_DISMISSED = "REPORT_DISMISSED"
    USER_SUSPENDED = "USER_SUSPENDED"
    USER_REACTIVATED = "USER_REACTIVATED"


class Block(Base):
    __tablename__ = "blocks"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        nullable=False,
    )
    blocker_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    blocked_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        CheckConstraint("blocker_id != blocked_id", name="ck_blocks_not_self"),
        UniqueConstraint("blocker_id", "blocked_id", name="uq_blocker_blocked"),
    )

    blocker = relationship("User", foreign_keys=[blocker_id])
    blocked = relationship("User", foreign_keys=[blocked_id])


class Report(Base):
    __tablename__ = "reports"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        nullable=False,
    )
    reporter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reported_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    connection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("connections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("community_questions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    answer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("community_answers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reason = Column(
        Enum(
            ReportReason,
            name="report_reason",
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        index=True,
    )
    description = Column(Text, nullable=True)
    status = Column(
        Enum(
            ReportStatus,
            name="report_status",
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=ReportStatus.OPEN,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolution_note = Column(Text, nullable=True)

    reporter = relationship("User", foreign_keys=[reporter_id])
    reported_user = relationship("User", foreign_keys=[reported_user_id])
    resolved_by_user = relationship("User", foreign_keys=[resolved_by])
    connection = relationship("Connection", foreign_keys=[connection_id])
    message = relationship("Message", foreign_keys=[message_id])


class ModerationAction(Base):
    __tablename__ = "moderation_actions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        nullable=False,
    )
    admin_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    report_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action = Column(
        Enum(
            ModerationActionType,
            name="moderation_action_type",
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        index=True,
    )
    reason = Column(Text, nullable=False)
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    admin = relationship("User", foreign_keys=[admin_id])
    target_user = relationship("User", foreign_keys=[target_user_id])
    report = relationship("Report", foreign_keys=[report_id])
