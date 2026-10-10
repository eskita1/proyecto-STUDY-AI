"""Add enrollment topic tracking.

Revision ID: 20261010_06
Revises: 20261010_05
Create Date: 2026-10-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261010_06"
down_revision: str | Sequence[str] | None = "20261010_05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "enrollment_topics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_enrollment_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("course_progress_status", sa.String(), nullable=False),
        sa.Column("student_status", sa.String(), nullable=False),
        sa.Column("personal_note", sa.String(), nullable=True),
        sa.CheckConstraint(
            "course_progress_status IN ('NOT_SEEN', 'SEEN')",
            name="ck_enrollment_topics_course_progress_status",
        ),
        sa.CheckConstraint(
            "student_status IN ('NOT_STARTED', 'IN_PROGRESS', 'STUDIED')",
            name="ck_enrollment_topics_student_status",
        ),
        sa.ForeignKeyConstraint(
            ["course_enrollment_id"],
            ["course_enrollments.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "course_enrollment_id",
            "topic_id",
            name="uq_enrollment_topics_enrollment_topic",
        ),
    )


def downgrade() -> None:
    op.drop_table("enrollment_topics")
