"""add_completion_and_reviews

Revision ID: c9d5e2f34a12
Revises: b8e4f1a23c56
Create Date: 2026-09-30 01:56:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c9d5e2f34a12'
down_revision: Union[str, Sequence[str], None] = 'b8e4f1a23c56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add completed_at to connections
    op.add_column('connections', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))

    # 2. Create reviews table
    op.create_table(
        'reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('connection_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reviewer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reviewee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['connection_id'], ['connections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewee_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('connection_id', 'reviewer_id', name='uq_connection_reviewer')
    )
    op.create_index(op.f('ix_reviews_id'), 'reviews', ['id'], unique=False)
    op.create_index(op.f('ix_reviews_connection_id'), 'reviews', ['connection_id'], unique=False)
    op.create_index(op.f('ix_reviews_reviewer_id'), 'reviews', ['reviewer_id'], unique=False)
    op.create_index(op.f('ix_reviews_reviewee_id'), 'reviews', ['reviewee_id'], unique=False)
    op.create_index(op.f('ix_reviews_created_at'), 'reviews', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_reviews_created_at'), table_name='reviews')
    op.drop_index(op.f('ix_reviews_reviewee_id'), table_name='reviews')
    op.drop_index(op.f('ix_reviews_reviewer_id'), table_name='reviews')
    op.drop_index(op.f('ix_reviews_connection_id'), table_name='reviews')
    op.drop_index(op.f('ix_reviews_id'), table_name='reviews')
    op.drop_table('reviews')

    op.drop_column('connections', 'completed_at')
