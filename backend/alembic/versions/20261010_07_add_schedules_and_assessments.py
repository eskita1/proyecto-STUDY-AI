"""Add schedules and assessments.

Revision ID: 20261010_07
Revises: 20261010_06
Create Date: 2026-10-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261010_07"
down_revision: str | Sequence[str] | None = "20261010_06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "course_schedule_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_offering_id", sa.Integer(), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("unit_id", sa.Integer(), nullable=True),
        sa.Column("topic_id", sa.Integer(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "(unit_id IS NOT NULL)::integer + (topic_id IS NOT NULL)::integer = 1",
            name="ck_schedule_items_exactly_one_target",
        ),
        sa.CheckConstraint("position > 0", name="ck_schedule_items_position"),
        sa.ForeignKeyConstraint(
            ["course_offering_id"], ["course_offerings.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "assessments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_offering_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.CheckConstraint(
            "type IN ('MIDTERM', 'FINAL', 'RECOVERY', 'ASSIGNMENT', 'QUIZ', 'OTHER')",
            name="ck_assessments_type",
        ),
        sa.ForeignKeyConstraint(
            ["course_offering_id"], ["course_offerings.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "assessment_topics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("assessment_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["assessment_id"], ["assessments.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assessment_id", "topic_id", name="uq_assessment_topics_assessment_topic"
        ),
    )


def downgrade() -> None:
    op.drop_table("assessment_topics")
    op.drop_table("assessments")
    op.drop_table("course_schedule_items")
