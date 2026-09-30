"""add_phase14_sessions_and_availability

Revision ID: i1a2b3c4d5e6
Revises: h1a2b3c4d5e6
Create Date: 2026-09-30 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'i1a2b3c4d5e6'
down_revision = 'h1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Extend requests table with structured timing preferences
    op.add_column('requests', sa.Column('preferred_date', sa.Date(), nullable=True))
    op.add_column('requests', sa.Column('preferred_start_time', sa.Time(), nullable=True))
    op.add_column('requests', sa.Column('preferred_end_time', sa.Time(), nullable=True))
    op.add_column('requests', sa.Column('requester_timezone', sa.String(length=50), server_default='Asia/Kolkata', nullable=False))
    op.add_column('requests', sa.Column('is_time_flexible', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('requests', sa.Column('flexibility_window_days', sa.Integer(), server_default='3', nullable=True))
    op.add_column('requests', sa.Column('preferred_days_of_week', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=True))

    # 2. Extend profiles with timezone and capacity controls
    op.add_column('profiles', sa.Column('helper_timezone', sa.String(length=50), server_default='Asia/Kolkata', nullable=False))
    op.add_column('profiles', sa.Column('max_weekly_sessions', sa.Integer(), server_default='3', nullable=False))
    op.add_column('profiles', sa.Column('accepting_sessions', sa.Boolean(), server_default='true', nullable=False))

    # 3. Create helper_availability_slots
    op.create_table(
        'helper_availability_slots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('day_of_week', sa.SmallInteger(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.CheckConstraint('day_of_week BETWEEN 0 AND 6', name='chk_slot_day_of_week'),
        sa.CheckConstraint('end_time > start_time', name='chk_slot_time_order'),
        sa.UniqueConstraint('user_id', 'day_of_week', 'start_time', 'end_time', name='uq_helper_day_slot')
    )
    op.create_index('ix_avail_slots_user_day', 'helper_availability_slots', ['user_id', 'day_of_week'])

    # 4. Create helper_availability_exceptions
    op.create_table(
        'helper_availability_exceptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('exception_date', sa.Date(), nullable=False),
        sa.Column('is_available', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.UniqueConstraint('user_id', 'exception_date', name='uq_helper_date_exception')
    )
    op.create_index('ix_avail_exceptions_user_date', 'helper_availability_exceptions', ['user_id', 'exception_date'])

    # 5. Create assistance_sessions
    op.create_table(
        'assistance_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('connection_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('connections.id', ondelete='CASCADE'), nullable=False),
        sa.Column('request_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('requests.id', ondelete='CASCADE'), nullable=False),
        sa.Column('proposer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('recipient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('need_category', sa.String(length=100), nullable=True),
        sa.Column('modality', sa.String(length=50), nullable=False),
        sa.Column('meeting_place_id', sa.String(length=255), nullable=True),
        sa.Column('meeting_place_name', sa.String(length=255), nullable=True),
        sa.Column('meeting_formatted_address', sa.Text(), nullable=True),
        sa.Column('meeting_latitude', sa.Float(), nullable=True),
        sa.Column('meeting_longitude', sa.Float(), nullable=True),
        sa.Column('meeting_url', sa.String(length=500), nullable=True),
        sa.Column('scheduled_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('scheduled_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('session_timezone', sa.String(length=50), server_default='Asia/Kolkata', nullable=False),
        sa.Column('status', sa.String(length=50), server_default='PROPOSED', nullable=False),
        sa.Column('status_reason', sa.Text(), nullable=True),
        sa.Column('previous_scheduled_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('previous_scheduled_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reschedule_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('requester_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('helper_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.CheckConstraint('scheduled_end > scheduled_start', name='chk_session_times'),
        sa.CheckConstraint('duration_minutes BETWEEN 15 AND 480', name='chk_duration_range')
    )
    op.create_index('ix_sessions_conn_status', 'assistance_sessions', ['connection_id', 'status'])
    op.create_index('ix_sessions_participants', 'assistance_sessions', ['proposer_id', 'recipient_id'])
    op.create_index('ix_sessions_schedule', 'assistance_sessions', ['scheduled_start', 'scheduled_end'])


def downgrade():
    op.drop_table('assistance_sessions')
    op.drop_table('helper_availability_exceptions')
    op.drop_table('helper_availability_slots')
    op.drop_column('profiles', 'accepting_sessions')
    op.drop_column('profiles', 'max_weekly_sessions')
    op.drop_column('profiles', 'helper_timezone')
    op.drop_column('requests', 'preferred_days_of_week')
    op.drop_column('requests', 'flexibility_window_days')
    op.drop_column('requests', 'is_time_flexible')
    op.drop_column('requests', 'requester_timezone')
    op.drop_column('requests', 'preferred_end_time')
    op.drop_column('requests', 'preferred_start_time')
    op.drop_column('requests', 'preferred_date')
