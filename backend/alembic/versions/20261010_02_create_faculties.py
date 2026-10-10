"""Create faculties table.

Revision ID: 20261010_02
Revises: 20261010_01
Create Date: 2026-10-10

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261010_02"
down_revision: str | Sequence[str] | None = "20261010_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "faculties",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("university_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.CheckConstraint(
            "name <> '' AND "
            "name = regexp_replace(btrim(name), '\\s+', ' ', 'g')",
            name="ck_faculties_name_normalized",
        ),
        sa.ForeignKeyConstraint(
            ["university_id"],
            ["universities.id"],
            name="fk_faculties_university_id_universities",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_faculties_university_id_lower_name",
        "faculties",
        ["university_id", sa.text("lower(name)")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_faculties_university_id_lower_name",
        table_name="faculties",
    )
    op.drop_table("faculties")
