"""add_accepted_answer_partial_unique_index

Revision ID: g1a2b3c4d5e6
Revises: f2b3c4d5e6f7
Create Date: 2026-09-30 04:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'g1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'f2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_question_accepted_answer "
        "ON community_answers (question_id) WHERE is_accepted = true"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_question_accepted_answer")
