"""add_vector_embeddings

Revision ID: 7411d6f5e980
Revises: f5ef218f72a9
Create Date: 2026-09-29 14:44:23.589352

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import pgvector


# revision identifiers, used by Alembic.
revision: str = '7411d6f5e980'
down_revision: Union[str, Sequence[str], None] = 'f5ef218f72a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Ensure vector extension is present
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Create embeddings table
    op.create_table('embeddings',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('owner_type', sa.String(length=50), nullable=False),
    sa.Column('owner_id', sa.UUID(), nullable=False),
    sa.Column('embedding_type', sa.String(length=50), nullable=False),
    sa.Column('model_name', sa.String(length=100), nullable=False),
    sa.Column('dimension', sa.Integer(), nullable=False),
    sa.Column('source_hash', sa.String(length=64), nullable=False),
    sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=384), nullable=False),
    sa.Column('canonical_text', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('owner_type', 'owner_id', name='uq_owner_embedding')
    )
    op.create_index(op.f('ix_embeddings_id'), 'embeddings', ['id'], unique=False)
    op.create_index(op.f('ix_embeddings_owner_id'), 'embeddings', ['owner_id'], unique=False)
    op.create_index(op.f('ix_embeddings_owner_type'), 'embeddings', ['owner_type'], unique=False)
    op.create_index(op.f('ix_embeddings_source_hash'), 'embeddings', ['source_hash'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_embeddings_source_hash'), table_name='embeddings')
    op.drop_index(op.f('ix_embeddings_owner_type'), table_name='embeddings')
    op.drop_index(op.f('ix_embeddings_owner_id'), table_name='embeddings')
    op.drop_index(op.f('ix_embeddings_id'), table_name='embeddings')
    op.drop_table('embeddings')
