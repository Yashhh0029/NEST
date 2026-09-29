import uuid
from datetime import datetime, timezone
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base


class Embedding(Base):
    __tablename__ = "embeddings"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        nullable=False,
    )
    owner_type = Column(String(50), nullable=False, index=True)  # "profile", "request", "resource"
    owner_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    embedding_type = Column(String(50), nullable=False, default="semantic_dense")
    model_name = Column(String(100), nullable=False, default="all-MiniLM-L6-v2")
    dimension = Column(Integer, nullable=False, default=384)
    source_hash = Column(String(64), nullable=False, index=True)  # SHA-256 of canonical text
    embedding = Column(Vector(384), nullable=False)
    canonical_text = Column(Text, nullable=False)

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
        UniqueConstraint("owner_type", "owner_id", name="uq_owner_embedding"),
    )

    def __repr__(self) -> str:
        return f"<Embedding owner_type={self.owner_type} owner_id={self.owner_id} model={self.model_name}>"
