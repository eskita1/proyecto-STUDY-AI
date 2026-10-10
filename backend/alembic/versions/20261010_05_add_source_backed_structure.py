"""Add source-backed academic structure.

Revision ID: 20261010_05
Revises: 20261010_04
Create Date: 2026-10-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261010_05"
down_revision: str | Sequence[str] | None = "20261010_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "academic_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("study_plan_id", sa.Integer(), nullable=True),
        sa.Column("course_offering_id", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "(study_plan_id IS NOT NULL)::integer + "
            "(course_offering_id IS NOT NULL)::integer = 1",
            name="ck_academic_sources_exactly_one_owner",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'CONFIRMED', 'SUPERSEDED')",
            name="ck_academic_sources_status",
        ),
        sa.CheckConstraint(
            "type IN ('STUDY_PLAN', 'SYLLABUS', 'SCHEDULE', "
            "'THEORETICAL_MATERIAL', 'PRACTICE_MATERIAL', 'OTHER')",
            name="ck_academic_sources_type",
        ),
        sa.CheckConstraint(
            "(type = 'STUDY_PLAN' AND study_plan_id IS NOT NULL) OR "
            "(type IN ('SYLLABUS', 'SCHEDULE', 'THEORETICAL_MATERIAL', "
            "'PRACTICE_MATERIAL') AND course_offering_id IS NOT NULL) OR "
            "type = 'OTHER'",
            name="ck_academic_sources_type_owner",
        ),
        sa.ForeignKeyConstraint(
            ["course_offering_id"], ["course_offerings.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["study_plan_id"], ["study_plans.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "extraction_proposals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("academic_source_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column(
            "extracted_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('PENDING', 'CONFIRMED', 'REJECTED')",
            name="ck_extraction_proposals_status",
        ),
        sa.ForeignKeyConstraint(
            ["academic_source_id"], ["academic_sources.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "units",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_offering_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("confirmed_from_proposal_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("position > 0", name="ck_units_position"),
        sa.CheckConstraint("status IN ('ACTIVE', 'REMOVED')", name="ck_units_status"),
        sa.ForeignKeyConstraint(
            ["confirmed_from_proposal_id"],
            ["extraction_proposals.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["course_offering_id"], ["course_offerings.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("unit_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("confirmed_from_proposal_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("position > 0", name="ck_topics_position"),
        sa.CheckConstraint("status IN ('ACTIVE', 'REMOVED')", name="ck_topics_status"),
        sa.ForeignKeyConstraint(
            ["confirmed_from_proposal_id"],
            ["extraction_proposals.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "subtopics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("confirmed_from_proposal_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("position > 0", name="ck_subtopics_position"),
        sa.ForeignKeyConstraint(
            ["confirmed_from_proposal_id"],
            ["extraction_proposals.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("subtopics")
    op.drop_table("topics")
    op.drop_table("units")
    op.drop_table("extraction_proposals")
    op.drop_table("academic_sources")
