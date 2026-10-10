"""Add study activity.

Revision ID: 20261010_08
Revises: 20261010_07
Create Date: 2026-10-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261010_08"
down_revision: str | Sequence[str] | None = "20261010_07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "study_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_enrollment_id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.String(), nullable=True),
        sa.CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at",
            name="ck_study_sessions_time_order",
        ),
        sa.ForeignKeyConstraint(
            ["course_enrollment_id"], ["course_enrollments.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "study_session_topics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("study_session_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["study_session_id"], ["study_sessions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "study_session_id", "topic_id", name="uq_study_session_topics_session_topic"
        ),
    )


def downgrade() -> None:
    op.drop_table("study_session_topics")
    op.drop_table("study_sessions")
