"""Add enrollment model.

Revision ID: 20261010_04
Revises: 20261010_03
Create Date: 2026-10-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261010_04"
down_revision: str | Sequence[str] | None = "20261010_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_courses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("study_plan_course_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["study_plan_course_id"], ["study_plan_courses.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "study_plan_course_id", name="uq_user_courses_user_spc"
        ),
    )
    op.create_table(
        "course_offerings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("study_plan_course_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("academic_year", sa.Integer(), nullable=False),
        sa.Column("term", sa.String(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.CheckConstraint(
            "academic_year > 0", name="ck_course_offerings_academic_year"
        ),
        sa.CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
            name="ck_course_offerings_date_order",
        ),
        sa.CheckConstraint(
            "name <> '' AND name = regexp_replace(btrim(name), '\\s+', ' ', 'g')",
            name="ck_course_offerings_name_normalized",
        ),
        sa.CheckConstraint(
            "term IN ('FIRST_TERM', 'SECOND_TERM', 'ANNUAL', 'SUMMER', 'OTHER')",
            name="ck_course_offerings_term",
        ),
        sa.ForeignKeyConstraint(
            ["study_plan_course_id"], ["study_plan_courses.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_course_offerings_logical",
        "course_offerings",
        ["study_plan_course_id", sa.text("lower(name)"), "academic_year", "term"],
        unique=True,
    )
    op.create_table(
        "course_enrollments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_course_id", sa.Integer(), nullable=False),
        sa.Column("course_offering_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("final_grade", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status <> 'IN_PROGRESS' OR final_grade IS NULL",
            name="ck_course_enrollments_in_progress_grade",
        ),
        sa.CheckConstraint(
            "status IN ('IN_PROGRESS', 'PASSED', 'FAILED')",
            name="ck_course_enrollments_status",
        ),
        sa.ForeignKeyConstraint(
            ["course_offering_id"], ["course_offerings.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["user_course_id"], ["user_courses.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_course_enrollments_one_active_attempt",
        "course_enrollments",
        ["user_course_id"],
        unique=True,
        postgresql_where=sa.text("status = 'IN_PROGRESS'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_course_enrollments_one_active_attempt", table_name="course_enrollments"
    )
    op.drop_table("course_enrollments")
    op.drop_index("uq_course_offerings_logical", table_name="course_offerings")
    op.drop_table("course_offerings")
    op.drop_table("user_courses")
