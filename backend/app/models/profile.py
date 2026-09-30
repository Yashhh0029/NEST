import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from app.db.database import Base


class Profile(Base):
    __tablename__ = "profiles"

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
        unique=True,
        index=True,
        nullable=False,
    )
    headline = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    occupation = Column(String(255), nullable=True)
    organization = Column(String(255), nullable=True)
    years_experience = Column(Float, nullable=True, default=0.0)
    languages = Column(JSONB, nullable=True, default=list)
    help_description = Column(Text, nullable=True)
    needs_description = Column(Text, nullable=True)
    availability = Column(Boolean, nullable=False, default=True)

    # Phase 14 Scheduling & Capacity extensions
    helper_timezone = Column(String(50), nullable=False, default="Asia/Kolkata")
    max_weekly_sessions = Column(Integer, nullable=False, default=3)
    accepting_sessions = Column(Boolean, nullable=False, default=True)

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

    user = relationship("User", back_populates="profile")

    def __repr__(self) -> str:
        return f"<Profile user_id={self.user_id} headline={self.headline}>"
