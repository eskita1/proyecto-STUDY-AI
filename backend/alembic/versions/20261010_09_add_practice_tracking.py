"""Add practice tracking.

Revision ID: 20261010_09
Revises: 20261010_08
Create Date: 2026-10-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261010_09"
down_revision: str | Sequence[str] | None = "20261010_08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "practice_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_enrollment_id", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_name", sa.String(), nullable=False),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("mode", sa.String(), nullable=False),
        sa.Column("total_exercises", sa.Integer(), nullable=True),
        sa.Column("correct_exercises", sa.Integer(), nullable=True),
        sa.Column("partial_exercises", sa.Integer(), nullable=True),
        sa.Column("incorrect_exercises", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "mode IN ('QUICK', 'DETAILED')", name="ck_practice_sessions_mode"
        ),
        sa.CheckConstraint(
            "(mode = 'QUICK' AND total_exercises IS NOT NULL AND "
            "correct_exercises IS NOT NULL AND partial_exercises IS NOT NULL AND "
            "incorrect_exercises IS NOT NULL AND total_exercises >= 0 AND "
            "correct_exercises >= 0 AND partial_exercises >= 0 AND "
            "incorrect_exercises >= 0 AND total_exercises = correct_exercises + "
            "partial_exercises + incorrect_exercises) OR "
            "(mode = 'DETAILED' AND total_exercises IS NULL AND "
            "correct_exercises IS NULL AND partial_exercises IS NULL AND "
            "incorrect_exercises IS NULL)",
            name="ck_practice_sessions_mode_counts",
        ),
        sa.ForeignKeyConstraint(
            ["course_enrollment_id"], ["course_enrollments.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "practice_exercises",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("practice_session_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("result", sa.String(), nullable=False),
        sa.CheckConstraint(
            "result IN ('CORRECT', 'PARTIALLY_CORRECT', 'INCORRECT', 'NOT_EVALUATED')",
            name="ck_practice_exercises_result",
        ),
        sa.ForeignKeyConstraint(
            ["practice_session_id"], ["practice_sessions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "practice_session_topics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("practice_session_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["practice_session_id"], ["practice_sessions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "practice_session_id",
            "topic_id",
            name="uq_practice_session_topics_session_topic",
        ),
    )


def downgrade() -> None:
    op.drop_table("practice_session_topics")
    op.drop_table("practice_exercises")
    op.drop_table("practice_sessions")
