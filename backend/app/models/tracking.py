from enum import StrEnum

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


class CourseProgressStatus(StrEnum):
    NOT_SEEN = "NOT_SEEN"
    SEEN = "SEEN"


class StudentStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    STUDIED = "STUDIED"


class EnrollmentTopic(Base):
    __tablename__ = "enrollment_topics"
    __table_args__ = (
        UniqueConstraint(
            "course_enrollment_id",
            "topic_id",
            name="uq_enrollment_topics_enrollment_topic",
        ),
        CheckConstraint(
            "course_progress_status IN ('NOT_SEEN', 'SEEN')",
            name="ck_enrollment_topics_course_progress_status",
        ),
        CheckConstraint(
            "student_status IN ('NOT_STARTED', 'IN_PROGRESS', 'STUDIED')",
            name="ck_enrollment_topics_student_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    course_enrollment_id: Mapped[int] = mapped_column(
        ForeignKey("course_enrollments.id", ondelete="RESTRICT")
    )
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="RESTRICT"))
    course_progress_status: Mapped[str] = mapped_column(
        String, default=CourseProgressStatus.NOT_SEEN
    )
    student_status: Mapped[str] = mapped_column(
        String, default=StudentStatus.NOT_STARTED
    )
    personal_note: Mapped[str | None] = mapped_column(String, nullable=True)
