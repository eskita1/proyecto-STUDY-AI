"""Create universities table.

Revision ID: 20261010_01
Revises:
Create Date: 2026-10-10

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261010_01"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "universities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.CheckConstraint(
            "name <> '' AND "
            "name = regexp_replace(btrim(name), '\\s+', ' ', 'g')",
            name="ck_universities_name_normalized",
        ),
        sa.CheckConstraint(
            "country_code ~ '^[A-Z]{2}$'",
            name="ck_universities_country_code_format",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_universities_country_code_lower_name",
        "universities",
        ["country_code", sa.text("lower(name)")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_universities_country_code_lower_name",
        table_name="universities",
    )
    op.drop_table("universities")
