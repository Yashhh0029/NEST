"""add_display_name_to_locations

Revision ID: k1a2b3c4d5e6
Revises: j1a2b3c4d5e6
Create Date: 2026-10-02 20:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'k1a2b3c4d5e6'
down_revision = 'j1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('locations', sa.Column('display_name', sa.String(length=255), nullable=True))
    op.add_column('locations', sa.Column('place_types', sa.String(length=255), nullable=True))
    op.add_column('request_locations', sa.Column('display_name', sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column('request_locations', 'display_name')
    op.drop_column('locations', 'place_types')
    op.drop_column('locations', 'display_name')
