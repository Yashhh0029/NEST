import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.database import Base


class Location(Base):
    __tablename__ = "locations"

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
    city = Column(String(100), nullable=False)
    area = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=False, default="India")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location_label = Column(String(100), nullable=False, default="Primary")
    display_name = Column(String(255), nullable=True)
    place_types = Column(String(255), nullable=True)
    google_place_id = Column(String(255), nullable=True, index=True)
    formatted_address = Column(String(500), nullable=True)
    postal_code = Column(String(20), nullable=True)
    location_source = Column(String(50), nullable=False, default="manual")
    location_precision = Column(String(50), nullable=False, default="locality")

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
        UniqueConstraint("user_id", "location_label", name="uq_user_location_label"),
    )

    user = relationship("User", back_populates="locations")

    def __repr__(self) -> str:
        return f"<Location user_id={self.user_id} city={self.city} area={self.area}>"
