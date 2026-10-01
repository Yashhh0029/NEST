"""add_email_verification

Revision ID: j1a2b3c4d5e6
Revises: i1a2b3c4d5e6
Create Date: 2026-10-01 01:25:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'j1a2b3c4d5e6'
down_revision = 'i1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add email verification fields to users table
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('users', sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('email_verification_token_hash', sa.String(length=128), nullable=True))
    op.create_index(op.f('ix_users_email_verification_token_hash'), 'users', ['email_verification_token_hash'], unique=False)
    op.add_column('users', sa.Column('email_verification_expires_at', sa.DateTime(timezone=True), nullable=True))

    # 2. Existing accounts migration:
    # Preserve verified state for accounts verified through trusted means (Google auth / is_verified=true)
    # Unverified accounts remain email_verified = false
    op.execute(
        "UPDATE users SET email_verified = true, email_verified_at = updated_at WHERE is_verified = true"
    )


def downgrade():
    op.drop_index(op.f('ix_users_email_verification_token_hash'), table_name='users')
    op.drop_column('users', 'email_verification_expires_at')
    op.drop_column('users', 'email_verification_token_hash')
    op.drop_column('users', 'email_verified_at')
    op.drop_column('users', 'email_verified')
