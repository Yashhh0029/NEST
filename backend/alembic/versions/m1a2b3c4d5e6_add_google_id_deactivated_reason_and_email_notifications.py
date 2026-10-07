"""add_google_id_deactivated_reason_and_email_notifications

Revision ID: m1a2b3c4d5e6
Revises: l1a2b3c4d5e6
Create Date: 2026-10-07 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision = 'm1a2b3c4d5e6'
down_revision = 'l1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Extend users table with Google OAuth sub identifier and deactivation state details
    op.add_column('users', sa.Column('google_id', sa.String(length=255), nullable=True))
    op.create_index('ix_users_google_id', 'users', ['google_id'], unique=True)
    op.add_column('users', sa.Column('deactivated_reason', sa.String(length=500), nullable=True))

    # 2. Create email_notifications table for resilient, deduplicated, asynchronous event notifications
    op.create_table(
        'email_notifications',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('idempotency_key', sa.String(length=255), nullable=False, unique=True),
        sa.Column('recipient_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('recipient_email', sa.String(length=255), nullable=False),
        sa.Column('notification_type', sa.String(length=50), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata_payload', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_email_notifications_id', 'email_notifications', ['id'])
    op.create_index('ix_email_notifications_idempotency_key', 'email_notifications', ['idempotency_key'])
    op.create_index('ix_email_notifications_recipient_id', 'email_notifications', ['recipient_id'])
    op.create_index('ix_email_notifications_status', 'email_notifications', ['status'])
    op.create_index('ix_email_notifications_created_at', 'email_notifications', ['created_at'])


def downgrade():
    op.drop_index('ix_email_notifications_created_at', table_name='email_notifications')
    op.drop_index('ix_email_notifications_status', table_name='email_notifications')
    op.drop_index('ix_email_notifications_recipient_id', table_name='email_notifications')
    op.drop_index('ix_email_notifications_idempotency_key', table_name='email_notifications')
    op.drop_index('ix_email_notifications_id', table_name='email_notifications')
    op.drop_table('email_notifications')

    op.drop_index('ix_users_google_id', table_name='users')
    op.drop_column('users', 'deactivated_reason')
    op.drop_column('users', 'google_id')
