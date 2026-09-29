import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text
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

    # Structured payloads and explanations
    extracted_requirements = Column(JSONB, nullable=True, default=dict)
    preferences = Column(JSONB, nullable=True, default=list)
    user_context = Column(JSONB, nullable=True, default=list)
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

    def __repr__(self) -> str:
        return f"<Request id={self.id} user_id={self.user_id} city={self.city} area={self.area}>"
