import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from app.db.database import Base


class EmailDeliveryStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    BOUNCED = "BOUNCED"
    SKIPPED_ONLINE = "SKIPPED_ONLINE"


class EmailNotification(Base):
    __tablename__ = "email_notifications"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        nullable=False,
    )
    idempotency_key = Column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    recipient_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    recipient_email = Column(String(255), nullable=False)
    notification_type = Column(String(50), nullable=False, index=True)
    subject = Column(String(255), nullable=False)
    status = Column(
        String(50),
        nullable=False,
        default=EmailDeliveryStatus.PENDING.value,
        index=True,
    )
    error_message = Column(Text, nullable=True)
    metadata_payload = Column(JSONB, nullable=True, default=dict)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    sent_at = Column(DateTime(timezone=True), nullable=True)

    recipient = relationship("User", backref="email_notifications")

    def __repr__(self) -> str:
        return f"<EmailNotification id={self.id} key={self.idempotency_key} recipient={self.recipient_email} status={self.status}>"
