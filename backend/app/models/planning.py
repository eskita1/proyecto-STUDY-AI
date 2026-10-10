from datetime import date
from enum import StrEnum

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


class AssessmentType(StrEnum):
    MIDTERM = "MIDTERM"
    FINAL = "FINAL"
    RECOVERY = "RECOVERY"
    ASSIGNMENT = "ASSIGNMENT"
    QUIZ = "QUIZ"
    OTHER = "OTHER"


class CourseScheduleItem(Base):
    __tablename__ = "course_schedule_items"
    __table_args__ = (
        CheckConstraint(
            "(unit_id IS NOT NULL)::integer + (topic_id IS NOT NULL)::integer = 1",
            name="ck_schedule_items_exactly_one_target",
        ),
        CheckConstraint("position > 0", name="ck_schedule_items_position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    course_offering_id: Mapped[int] = mapped_column(
        ForeignKey("course_offerings.id", ondelete="RESTRICT")
    )
    scheduled_date: Mapped[date] = mapped_column(Date)
    unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("units.id", ondelete="RESTRICT"), nullable=True
    )
    topic_id: Mapped[int | None] = mapped_column(
        ForeignKey("topics.id", ondelete="RESTRICT"), nullable=True
    )
    position: Mapped[int]


class Assessment(Base):
    __tablename__ = "assessments"
    __table_args__ = (
        CheckConstraint(
            "type IN ('MIDTERM', 'FINAL', 'RECOVERY', 'ASSIGNMENT', 'QUIZ', 'OTHER')",
            name="ck_assessments_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    course_offering_id: Mapped[int] = mapped_column(
        ForeignKey("course_offerings.id", ondelete="RESTRICT")
    )
    name: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)
    date: Mapped[date] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(String, nullable=True)


class AssessmentTopic(Base):
    __tablename__ = "assessment_topics"
    __table_args__ = (
        UniqueConstraint(
            "assessment_id", "topic_id", name="uq_assessment_topics_assessment_topic"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("assessments.id", ondelete="RESTRICT")
    )
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="RESTRICT"))
