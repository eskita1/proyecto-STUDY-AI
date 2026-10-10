"""Add institutional foundation.

Revision ID: 20261010_03
Revises: 20261010_02
Create Date: 2026-10-10

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261010_03"
down_revision: str | Sequence[str] | None = "20261010_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def normalized_name_constraint(table: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(
        "name <> '' AND name = regexp_replace(btrim(name), '\\s+', ' ', 'g')",
        name=f"ck_{table}_name_normalized",
    )


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "careers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("faculty_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        normalized_name_constraint("careers"),
        sa.ForeignKeyConstraint(["faculty_id"], ["faculties.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_careers_faculty_id_lower_name",
        "careers",
        ["faculty_id", sa.text("lower(name)")],
        unique=True,
    )
    op.create_table(
        "study_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("career_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        normalized_name_constraint("study_plans"),
        sa.ForeignKeyConstraint(["career_id"], ["careers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_study_plans_career_id_lower_name",
        "study_plans",
        ["career_id", sa.text("lower(name)")],
        unique=True,
    )
    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("code", sa.String(), nullable=True),
        normalized_name_constraint("courses"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_courses_lower_name", "courses", [sa.text("lower(name)")], unique=True
    )
    op.create_table(
        "study_plan_courses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("study_plan_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["study_plan_id"], ["study_plans.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "study_plan_id",
            "course_id",
            name="uq_study_plan_courses_study_plan_id_course_id",
        ),
    )
    op.create_table(
        "user_careers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("career_id", sa.Integer(), nullable=False),
        sa.Column("study_plan_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["career_id"], ["careers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["study_plan_id"], ["study_plans.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "career_id", name="uq_user_careers_user_id_career_id"
        ),
    )


def downgrade() -> None:
    op.drop_table("user_careers")
    op.drop_table("study_plan_courses")
    op.drop_index("uq_courses_lower_name", table_name="courses")
    op.drop_table("courses")
    op.drop_index("uq_study_plans_career_id_lower_name", table_name="study_plans")
    op.drop_table("study_plans")
    op.drop_index("uq_careers_faculty_id_lower_name", table_name="careers")
    op.drop_table("careers")
    op.drop_table("users")
