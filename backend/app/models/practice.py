from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


class PracticeMode(StrEnum):
    QUICK = "QUICK"
    DETAILED = "DETAILED"


class ExerciseResult(StrEnum):
    CORRECT = "CORRECT"
    PARTIALLY_CORRECT = "PARTIALLY_CORRECT"
    INCORRECT = "INCORRECT"
    NOT_EVALUATED = "NOT_EVALUATED"


class PracticeSession(Base):
    __tablename__ = "practice_sessions"
    __table_args__ = (
        CheckConstraint(
            "mode IN ('QUICK', 'DETAILED')", name="ck_practice_sessions_mode"
        ),
        CheckConstraint(
            "(mode = 'QUICK' AND total_exercises IS NOT NULL AND "
            "correct_exercises IS NOT NULL AND partial_exercises IS NOT NULL AND "
            "incorrect_exercises IS NOT NULL AND total_exercises >= 0 AND "
            "correct_exercises >= 0 AND partial_exercises >= 0 AND "
            "incorrect_exercises >= 0 AND total_exercises = correct_exercises + "
            "partial_exercises + incorrect_exercises) OR "
            "(mode = 'DETAILED' AND total_exercises IS NULL AND "
            "correct_exercises IS NULL AND partial_exercises IS NULL AND "
            "incorrect_exercises IS NULL)",
            name="ck_practice_sessions_mode_counts",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    course_enrollment_id: Mapped[int] = mapped_column(
        ForeignKey("course_enrollments.id", ondelete="RESTRICT")
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_type: Mapped[str] = mapped_column(String)
    source_name: Mapped[str] = mapped_column(String)
    note: Mapped[str | None] = mapped_column(String, nullable=True)
    mode: Mapped[str] = mapped_column(String)
    total_exercises: Mapped[int | None] = mapped_column(Integer, nullable=True)
    correct_exercises: Mapped[int | None] = mapped_column(Integer, nullable=True)
    partial_exercises: Mapped[int | None] = mapped_column(Integer, nullable=True)
    incorrect_exercises: Mapped[int | None] = mapped_column(Integer, nullable=True)


class PracticeSessionTopic(Base):
    __tablename__ = "practice_session_topics"
    __table_args__ = (
        UniqueConstraint(
            "practice_session_id",
            "topic_id",
            name="uq_practice_session_topics_session_topic",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    practice_session_id: Mapped[int] = mapped_column(
        ForeignKey("practice_sessions.id", ondelete="RESTRICT")
    )
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="RESTRICT"))


class PracticeExercise(Base):
    __tablename__ = "practice_exercises"
    __table_args__ = (
        CheckConstraint(
            "result IN ('CORRECT', 'PARTIALLY_CORRECT', 'INCORRECT', 'NOT_EVALUATED')",
            name="ck_practice_exercises_result",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    practice_session_id: Mapped[int] = mapped_column(
        ForeignKey("practice_sessions.id", ondelete="RESTRICT")
    )
    label: Mapped[str] = mapped_column(String)
    result: Mapped[str] = mapped_column(String)
