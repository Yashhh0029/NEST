"""add_community_intelligence_tables

Revision ID: f2b3c4d5e6f7
Revises: e1a2b3c4d5e6
Create Date: 2026-09-30 04:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f2b3c4d5e6f7'
down_revision: Union[str, Sequence[str], None] = 'e1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create community_questions table
    op.create_table(
        'community_questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('area', sa.String(length=100), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='OPEN'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_community_questions_id'), 'community_questions', ['id'], unique=False)
    op.create_index(op.f('ix_community_questions_author_id'), 'community_questions', ['author_id'], unique=False)
    op.create_index(op.f('ix_community_questions_title'), 'community_questions', ['title'], unique=False)
    op.create_index(op.f('ix_community_questions_city'), 'community_questions', ['city'], unique=False)
    op.create_index(op.f('ix_community_questions_area'), 'community_questions', ['area'], unique=False)
    op.create_index(op.f('ix_community_questions_category'), 'community_questions', ['category'], unique=False)
    op.create_index(op.f('ix_community_questions_status'), 'community_questions', ['status'], unique=False)
    op.create_index(op.f('ix_community_questions_created_at'), 'community_questions', ['created_at'], unique=False)

    # 2. Create community_answers table
    op.create_table(
        'community_answers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('is_accepted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['community_questions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_community_answers_id'), 'community_answers', ['id'], unique=False)
    op.create_index(op.f('ix_community_answers_question_id'), 'community_answers', ['question_id'], unique=False)
    op.create_index(op.f('ix_community_answers_author_id'), 'community_answers', ['author_id'], unique=False)
    op.create_index(op.f('ix_community_answers_is_accepted'), 'community_answers', ['is_accepted'], unique=False)
    op.create_index(op.f('ix_community_answers_created_at'), 'community_answers', ['created_at'], unique=False)

    # 3. Create community_answer_votes table
    op.create_table(
        'community_answer_votes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('answer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('voter_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('vote', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['answer_id'], ['community_answers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['voter_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('answer_id', 'voter_id', name='uq_answer_voter')
    )
    op.create_index(op.f('ix_community_answer_votes_id'), 'community_answer_votes', ['id'], unique=False)
    op.create_index(op.f('ix_community_answer_votes_answer_id'), 'community_answer_votes', ['answer_id'], unique=False)
    op.create_index(op.f('ix_community_answer_votes_voter_id'), 'community_answer_votes', ['voter_id'], unique=False)
    op.create_index(op.f('ix_community_answer_votes_vote'), 'community_answer_votes', ['vote'], unique=False)

    # 4. Add question_id and answer_id to reports table
    op.add_column('reports', sa.Column('question_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('reports', sa.Column('answer_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_reports_question_id', 'reports', 'community_questions', ['question_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_reports_answer_id', 'reports', 'community_answers', ['answer_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_reports_question_id'), 'reports', ['question_id'], unique=False)
    op.create_index(op.f('ix_reports_answer_id'), 'reports', ['answer_id'], unique=False)


def downgrade() -> None:
    # 4. Remove question_id and answer_id from reports
    op.drop_index(op.f('ix_reports_answer_id'), table_name='reports')
    op.drop_index(op.f('ix_reports_question_id'), table_name='reports')
    op.drop_constraint('fk_reports_answer_id', 'reports', type_='foreignkey')
    op.drop_constraint('fk_reports_question_id', 'reports', type_='foreignkey')
    op.drop_column('reports', 'answer_id')
    op.drop_column('reports', 'question_id')

    # 3. Drop community_answer_votes
    op.drop_index(op.f('ix_community_answer_votes_vote'), table_name='community_answer_votes')
    op.drop_index(op.f('ix_community_answer_votes_voter_id'), table_name='community_answer_votes')
    op.drop_index(op.f('ix_community_answer_votes_answer_id'), table_name='community_answer_votes')
    op.drop_index(op.f('ix_community_answer_votes_id'), table_name='community_answer_votes')
    op.drop_table('community_answer_votes')

    # 2. Drop community_answers
    op.drop_index(op.f('ix_community_answers_created_at'), table_name='community_answers')
    op.drop_index(op.f('ix_community_answers_is_accepted'), table_name='community_answers')
    op.drop_index(op.f('ix_community_answers_author_id'), table_name='community_answers')
    op.drop_index(op.f('ix_community_answers_question_id'), table_name='community_answers')
    op.drop_index(op.f('ix_community_answers_id'), table_name='community_answers')
    op.drop_table('community_answers')

    # 1. Drop community_questions
    op.drop_index(op.f('ix_community_questions_created_at'), table_name='community_questions')
    op.drop_index(op.f('ix_community_questions_status'), table_name='community_questions')
    op.drop_index(op.f('ix_community_questions_category'), table_name='community_questions')
    op.drop_index(op.f('ix_community_questions_area'), table_name='community_questions')
    op.drop_index(op.f('ix_community_questions_city'), table_name='community_questions')
    op.drop_index(op.f('ix_community_questions_title'), table_name='community_questions')
    op.drop_index(op.f('ix_community_questions_author_id'), table_name='community_questions')
    op.drop_index(op.f('ix_community_questions_id'), table_name='community_questions')
    op.drop_table('community_questions')
