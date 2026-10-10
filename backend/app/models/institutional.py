from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)


class Career(Base):
    __tablename__ = "careers"
    __table_args__ = (
        CheckConstraint(
            "name <> '' AND name = regexp_replace(btrim(name), '\\s+', ' ', 'g')",
            name="ck_careers_name_normalized",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    faculty_id: Mapped[int] = mapped_column(
        ForeignKey("faculties.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)


Index(
    "uq_careers_faculty_id_lower_name",
    Career.faculty_id,
    func.lower(Career.name),
    unique=True,
)


class StudyPlan(Base):
    __tablename__ = "study_plans"
    __table_args__ = (
        CheckConstraint(
            "name <> '' AND name = regexp_replace(btrim(name), '\\s+', ' ', 'g')",
            name="ck_study_plans_name_normalized",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    career_id: Mapped[int] = mapped_column(
        ForeignKey("careers.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)


Index(
    "uq_study_plans_career_id_lower_name",
    StudyPlan.career_id,
    func.lower(StudyPlan.name),
    unique=True,
)


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (
        CheckConstraint(
            "name <> '' AND name = regexp_replace(btrim(name), '\\s+', ' ', 'g')",
            name="ck_courses_name_normalized",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str | None] = mapped_column(String, nullable=True)


Index("uq_courses_lower_name", func.lower(Course.name), unique=True)


class StudyPlanCourse(Base):
    __tablename__ = "study_plan_courses"
    __table_args__ = (
        UniqueConstraint(
            "study_plan_id",
            "course_id",
            name="uq_study_plan_courses_study_plan_id_course_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    study_plan_id: Mapped[int] = mapped_column(
        ForeignKey("study_plans.id", ondelete="RESTRICT"), nullable=False
    )
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False
    )


class UserCareer(Base):
    __tablename__ = "user_careers"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "career_id", name="uq_user_careers_user_id_career_id"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    career_id: Mapped[int] = mapped_column(
        ForeignKey("careers.id", ondelete="RESTRICT"), nullable=False
    )
    study_plan_id: Mapped[int] = mapped_column(
        ForeignKey("study_plans.id", ondelete="RESTRICT"), nullable=False
    )
