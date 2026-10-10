from sqlalchemy import CheckConstraint, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


class University(Base):
    __tablename__ = "universities"
    __table_args__ = (
        CheckConstraint(
            "name <> '' AND "
            "name = regexp_replace(btrim(name), '\\s+', ' ', 'g')",
            name="ck_universities_name_normalized",
        ),
        CheckConstraint(
            "country_code ~ '^[A-Z]{2}$'",
            name="ck_universities_country_code_format",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)


Index(
    "uq_universities_country_code_lower_name",
    University.country_code,
    func.lower(University.name),
    unique=True,
)
