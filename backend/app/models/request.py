import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text, Time, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from app.db.database import Base


class Request(Base):
    __tablename__ = "requests"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        nullable=False,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    raw_text = Column(Text, nullable=False)
    intent = Column(String(100), nullable=True, default="newcomer_assistance")
    status = Column(String(50), nullable=False, default="OPEN", index=True)

    # Structured geography
    city = Column(String(100), nullable=True, index=True)
    area = Column(String(100), nullable=True, index=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True, default="India")

    # Structured budget
    budget_amount = Column(Float, nullable=True)
    budget_currency = Column(String(20), nullable=True, default="INR")
    budget_period = Column(String(50), nullable=True)  # "monthly", "weekly", "daily", "yearly", or None
    budget_operator = Column(String(20), nullable=True)  # "<=", ">=", "==", "~="

    # Structured timing preferences (Phase 14)
    preferred_date = Column(Date, nullable=True)
    preferred_start_time = Column(Time, nullable=True)
    preferred_end_time = Column(Time, nullable=True)
    requester_timezone = Column(String(50), nullable=False, default="Asia/Kolkata")
    is_time_flexible = Column(Boolean, nullable=False, default=True)
    flexibility_window_days = Column(Integer, nullable=True, default=3)
    preferred_days_of_week = Column(JSONB, nullable=True, default=list)

    # Structured payloads and explanations
    extracted_requirements = Column(JSONB, nullable=True, default=dict)
    preferences = Column(JSONB, nullable=True, default=list)
    user_context = Column(JSONB, nullable=True, default=list)
    need_progress = Column(JSONB, nullable=False, default=dict)
    resolution_summary = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    extraction_method = Column(
        String(100),
        nullable=False,
        default="deterministic_nlp_rule_based_v1",
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

    user = relationship("User", back_populates="requests")
    target_location = relationship(
        "RequestLocation",
        back_populates="request",
        uselist=False,
        cascade="all, delete-orphan",
    )
    saved_resources = relationship(
        "RequestSavedResource",
        back_populates="request",
        cascade="all, delete-orphan",
        order_by="desc(RequestSavedResource.created_at)",
    )

    def __repr__(self) -> str:
        return f"<Request id={self.id} user_id={self.user_id} city={self.city} area={self.area} status={self.status}>"


class RequestSavedResource(Base):
    __tablename__ = "request_saved_resources"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        nullable=False,
    )
    request_id = Column(
        UUID(as_uuid=True),
        ForeignKey("requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    place_id = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    formatted_address = Column(Text, nullable=True)
    rating = Column(Float, nullable=True)
    user_ratings_total = Column(Integer, nullable=True)
    # Public place coordinates only from Google Places (NEVER private home GPS)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("request_id", "place_id", name="uq_request_saved_place"),
    )

    request = relationship("Request", back_populates="saved_resources")
    user = relationship("User", foreign_keys=[user_id])

