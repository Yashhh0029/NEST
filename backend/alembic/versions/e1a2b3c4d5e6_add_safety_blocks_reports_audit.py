"""add_safety_blocks_reports_audit

Revision ID: e1a2b3c4d5e6
Revises: c9d5e2f34a12
Create Date: 2026-09-30 03:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'c9d5e2f34a12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create blocks table
    op.create_table(
        'blocks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('blocker_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('blocked_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('blocker_id != blocked_id', name='ck_blocks_not_self'),
        sa.ForeignKeyConstraint(['blocker_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['blocked_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('blocker_id', 'blocked_id', name='uq_blocker_blocked')
    )
    op.create_index(op.f('ix_blocks_id'), 'blocks', ['id'], unique=False)
    op.create_index(op.f('ix_blocks_blocker_id'), 'blocks', ['blocker_id'], unique=False)
    op.create_index(op.f('ix_blocks_blocked_id'), 'blocks', ['blocked_id'], unique=False)
    op.create_index(op.f('ix_blocks_created_at'), 'blocks', ['created_at'], unique=False)

    # 2. Create reports table
    op.create_table(
        'reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reporter_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reported_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('connection_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reason', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='OPEN'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('resolution_note', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['connection_id'], ['connections.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reported_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reporter_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reports_id'), 'reports', ['id'], unique=False)
    op.create_index(op.f('ix_reports_reporter_id'), 'reports', ['reporter_id'], unique=False)
    op.create_index(op.f('ix_reports_reported_user_id'), 'reports', ['reported_user_id'], unique=False)
    op.create_index(op.f('ix_reports_connection_id'), 'reports', ['connection_id'], unique=False)
    op.create_index(op.f('ix_reports_message_id'), 'reports', ['message_id'], unique=False)
    op.create_index(op.f('ix_reports_status'), 'reports', ['status'], unique=False)
    op.create_index(op.f('ix_reports_reason'), 'reports', ['reason'], unique=False)
    op.create_index(op.f('ix_reports_created_at'), 'reports', ['created_at'], unique=False)

    # 3. Create moderation_actions table
    op.create_table(
        'moderation_actions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('admin_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('report_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['admin_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_moderation_actions_id'), 'moderation_actions', ['id'], unique=False)
    op.create_index(op.f('ix_moderation_actions_admin_id'), 'moderation_actions', ['admin_id'], unique=False)
    op.create_index(op.f('ix_moderation_actions_target_user_id'), 'moderation_actions', ['target_user_id'], unique=False)
    op.create_index(op.f('ix_moderation_actions_report_id'), 'moderation_actions', ['report_id'], unique=False)
    op.create_index(op.f('ix_moderation_actions_action'), 'moderation_actions', ['action'], unique=False)
    op.create_index(op.f('ix_moderation_actions_created_at'), 'moderation_actions', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_moderation_actions_created_at'), table_name='moderation_actions')
    op.drop_index(op.f('ix_moderation_actions_action'), table_name='moderation_actions')
    op.drop_index(op.f('ix_moderation_actions_report_id'), table_name='moderation_actions')
    op.drop_index(op.f('ix_moderation_actions_target_user_id'), table_name='moderation_actions')
    op.drop_index(op.f('ix_moderation_actions_admin_id'), table_name='moderation_actions')
    op.drop_index(op.f('ix_moderation_actions_id'), table_name='moderation_actions')
    op.drop_table('moderation_actions')

    op.drop_index(op.f('ix_reports_created_at'), table_name='reports')
    op.drop_index(op.f('ix_reports_reason'), table_name='reports')
    op.drop_index(op.f('ix_reports_status'), table_name='reports')
    op.drop_index(op.f('ix_reports_message_id'), table_name='reports')
    op.drop_index(op.f('ix_reports_connection_id'), table_name='reports')
    op.drop_index(op.f('ix_reports_reported_user_id'), table_name='reports')
    op.drop_index(op.f('ix_reports_reporter_id'), table_name='reports')
    op.drop_index(op.f('ix_reports_id'), table_name='reports')
    op.drop_table('reports')

    op.drop_index(op.f('ix_blocks_created_at'), table_name='blocks')
    op.drop_index(op.f('ix_blocks_blocked_id'), table_name='blocks')
    op.drop_index(op.f('ix_blocks_blocker_id'), table_name='blocks')
    op.drop_index(op.f('ix_blocks_id'), table_name='blocks')
    op.drop_table('blocks')
