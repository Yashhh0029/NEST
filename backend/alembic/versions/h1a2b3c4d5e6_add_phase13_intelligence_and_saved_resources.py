"""add_phase13_intelligence_and_saved_resources

Revision ID: h1a2b3c4d5e6
Revises: g1a2b3c4d5e6
Create Date: 2026-09-30 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'h1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'g1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add need_progress, resolution_summary, and resolved_at to requests table
    op.add_column(
        'requests',
        sa.Column('need_progress', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb"))
    )
    op.add_column(
        'requests',
        sa.Column('resolution_summary', sa.Text(), nullable=True)
    )
    op.add_column(
        'requests',
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True)
    )

    # 2. Create request_saved_resources table
    op.create_table(
        'request_saved_resources',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('request_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('place_id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('formatted_address', sa.Text(), nullable=True),
        sa.Column('rating', sa.Float(), nullable=True),
        sa.Column('user_ratings_total', sa.Integer(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['request_id'], ['requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('request_id', 'place_id', name='uq_request_saved_place')
    )
    op.create_index(op.f('ix_request_saved_resources_id'), 'request_saved_resources', ['id'], unique=False)
    op.create_index(op.f('ix_request_saved_resources_request_id'), 'request_saved_resources', ['request_id'], unique=False)
    op.create_index(op.f('ix_request_saved_resources_user_id'), 'request_saved_resources', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_request_saved_resources_user_id'), table_name='request_saved_resources')
    op.drop_index(op.f('ix_request_saved_resources_request_id'), table_name='request_saved_resources')
    op.drop_index(op.f('ix_request_saved_resources_id'), table_name='request_saved_resources')
    op.drop_table('request_saved_resources')

    op.drop_column('requests', 'resolved_at')
    op.drop_column('requests', 'resolution_summary')
    op.drop_column('requests', 'need_progress')
