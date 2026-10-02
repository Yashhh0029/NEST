import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.database import Base


class RequestLocation(Base):
    __tablename__ = "request_locations"

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
        unique=True,
        index=True,
        nullable=False,
    )
    google_place_id = Column(String(255), nullable=True, index=True)
    display_name = Column(String(255), nullable=True)
    formatted_address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True, index=True)
    area = Column(String(100), nullable=True, index=True)
    state = Column(String(100), nullable=True, index=True)
    country = Column(String(100), nullable=False, default="India")
    postal_code = Column(String(20), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location_source = Column(String(50), nullable=False, default="nlp_resolved")
    location_precision = Column(String(50), nullable=False, default="approximate")

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

    request = relationship("Request", back_populates="target_location")

    def __repr__(self) -> str:
        return f"<RequestLocation request_id={self.request_id} city={self.city} area={self.area}>"
