from datetime import datetime, timezone
from enum import Enum
import uuid
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.database import Base


class SessionStatus(str, Enum):
    PROPOSED = "PROPOSED"
    CONFIRMED = "CONFIRMED"
    RESCHEDULE_PROPOSED = "RESCHEDULE_PROPOSED"
    DECLINED = "DECLINED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class SessionModality(str, Enum):
    IN_PERSON = "IN_PERSON"
    REMOTE = "REMOTE"


class AssistanceSession(Base):
    __tablename__ = "assistance_sessions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        nullable=False,
    )
    connection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    request_id = Column(
        UUID(as_uuid=True),
        ForeignKey("requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    proposer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    need_category = Column(String(100), nullable=True)
    modality = Column(String(50), nullable=False, default=SessionModality.IN_PERSON.value)

    # In-person public venue fields (strictly server-validated via Google Places)
    meeting_place_id = Column(String(255), nullable=True)
    meeting_place_name = Column(String(255), nullable=True)
    meeting_formatted_address = Column(Text, nullable=True)
    meeting_latitude = Column(Float, nullable=True)
    meeting_longitude = Column(Float, nullable=True)

    # Remote fields (strictly HTTPS)
    meeting_url = Column(String(500), nullable=True)

    # Timing fields
    scheduled_start = Column(DateTime(timezone=True), nullable=False, index=True)
    scheduled_end = Column(DateTime(timezone=True), nullable=False, index=True)
    duration_minutes = Column(Integer, nullable=False)
    session_timezone = Column(String(50), nullable=False, default="Asia/Kolkata")

    # State machine
    status = Column(String(50), nullable=False, default=SessionStatus.PROPOSED.value, index=True)
    status_reason = Column(Text, nullable=True)

    # Reschedule tracking
    previous_scheduled_start = Column(DateTime(timezone=True), nullable=True)
    previous_scheduled_end = Column(DateTime(timezone=True), nullable=True)
    reschedule_count = Column(Integer, nullable=False, default=0)

    # Dual-confirmation completion
    requester_completed_at = Column(DateTime(timezone=True), nullable=True)
    helper_completed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
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
        CheckConstraint("scheduled_end > scheduled_start", name="chk_session_times"),
        CheckConstraint("duration_minutes BETWEEN 15 AND 480", name="chk_duration_range"),
    )

    connection = relationship("Connection", backref="sessions")
    request = relationship("Request", backref="sessions")
    proposer = relationship("User", foreign_keys=[proposer_id])
    recipient = relationship("User", foreign_keys=[recipient_id])
    cancelled_by = relationship("User", foreign_keys=[cancelled_by_id])

    def __repr__(self) -> str:
        return f"<AssistanceSession id={self.id} title='{self.title}' status={self.status} {self.scheduled_start}>"
