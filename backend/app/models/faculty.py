from sqlalchemy import CheckConstraint, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


class Faculty(Base):
    __tablename__ = "faculties"
    __table_args__ = (
        CheckConstraint(
            "name <> '' AND "
            "name = regexp_replace(btrim(name), '\\s+', ' ', 'g')",
            name="ck_faculties_name_normalized",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    university_id: Mapped[int] = mapped_column(
        ForeignKey(
            "universities.id",
            name="fk_faculties_university_id_universities",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)


Index(
    "uq_faculties_university_id_lower_name",
    Faculty.university_id,
    func.lower(Faculty.name),
    unique=True,
)
