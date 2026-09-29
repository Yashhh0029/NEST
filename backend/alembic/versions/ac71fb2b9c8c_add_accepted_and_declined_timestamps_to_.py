"""add_accepted_and_declined_timestamps_to_connections

Revision ID: ac71fb2b9c8c
Revises: 354032dd729c
Create Date: 2026-09-30 01:09:52.426777

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ac71fb2b9c8c'
down_revision: Union[str, Sequence[str], None] = '354032dd729c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('connections', sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('connections', sa.Column('declined_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('connections', 'declined_at')
    op.drop_column('connections', 'accepted_at')
