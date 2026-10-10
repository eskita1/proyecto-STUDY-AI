from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


class StudySession(Base):
    __tablename__ = "study_sessions"
    __table_args__ = (
        CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at",
            name="ck_study_sessions_time_order",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    course_enrollment_id: Mapped[int] = mapped_column(
        ForeignKey("course_enrollments.id", ondelete="RESTRICT")
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    note: Mapped[str | None] = mapped_column(String, nullable=True)


class StudySessionTopic(Base):
    __tablename__ = "study_session_topics"
    __table_args__ = (
        UniqueConstraint(
            "study_session_id",
            "topic_id",
            name="uq_study_session_topics_session_topic",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    study_session_id: Mapped[int] = mapped_column(
        ForeignKey("study_sessions.id", ondelete="RESTRICT")
    )
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="RESTRICT"))
