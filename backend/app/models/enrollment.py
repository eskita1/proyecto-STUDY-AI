from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


class AcademicTerm(StrEnum):
    FIRST_TERM = "FIRST_TERM"
    SECOND_TERM = "SECOND_TERM"
    ANNUAL = "ANNUAL"
    SUMMER = "SUMMER"
    OTHER = "OTHER"


class EnrollmentStatus(StrEnum):
    IN_PROGRESS = "IN_PROGRESS"
    PASSED = "PASSED"
    FAILED = "FAILED"


class UserCourse(Base):
    __tablename__ = "user_courses"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "study_plan_course_id", name="uq_user_courses_user_spc"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    study_plan_course_id: Mapped[int] = mapped_column(
        ForeignKey("study_plan_courses.id", ondelete="RESTRICT")
    )


class CourseOffering(Base):
    __tablename__ = "course_offerings"
    __table_args__ = (
        CheckConstraint(
            "name <> '' AND name = regexp_replace(btrim(name), '\\s+', ' ', 'g')",
            name="ck_course_offerings_name_normalized",
        ),
        CheckConstraint("academic_year > 0", name="ck_course_offerings_academic_year"),
        CheckConstraint(
            "term IN ('FIRST_TERM', 'SECOND_TERM', 'ANNUAL', 'SUMMER', 'OTHER')",
            name="ck_course_offerings_term",
        ),
        CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
            name="ck_course_offerings_date_order",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    study_plan_course_id: Mapped[int] = mapped_column(
        ForeignKey("study_plan_courses.id", ondelete="RESTRICT")
    )
    name: Mapped[str] = mapped_column(String)
    academic_year: Mapped[int]
    term: Mapped[str] = mapped_column(String)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)


Index(
    "uq_course_offerings_logical",
    CourseOffering.study_plan_course_id,
    func.lower(CourseOffering.name),
    CourseOffering.academic_year,
    CourseOffering.term,
    unique=True,
)


class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('IN_PROGRESS', 'PASSED', 'FAILED')",
            name="ck_course_enrollments_status",
        ),
        CheckConstraint(
            "status <> 'IN_PROGRESS' OR final_grade IS NULL",
            name="ck_course_enrollments_in_progress_grade",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_course_id: Mapped[int] = mapped_column(
        ForeignKey("user_courses.id", ondelete="RESTRICT")
    )
    course_offering_id: Mapped[int] = mapped_column(
        ForeignKey("course_offerings.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(String)
    final_grade: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


Index(
    "uq_course_enrollments_one_active_attempt",
    CourseEnrollment.user_course_id,
    unique=True,
    postgresql_where=text("status = 'IN_PROGRESS'"),
)
