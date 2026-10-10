from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


class AcademicSourceType(StrEnum):
    STUDY_PLAN = "STUDY_PLAN"
    SYLLABUS = "SYLLABUS"
    SCHEDULE = "SCHEDULE"
    THEORETICAL_MATERIAL = "THEORETICAL_MATERIAL"
    PRACTICE_MATERIAL = "PRACTICE_MATERIAL"
    OTHER = "OTHER"


class AcademicSourceStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    SUPERSEDED = "SUPERSEDED"


class ProposalStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class StructureStatus(StrEnum):
    ACTIVE = "ACTIVE"
    REMOVED = "REMOVED"


class AcademicSource(Base):
    __tablename__ = "academic_sources"
    __table_args__ = (
        CheckConstraint(
            "(study_plan_id IS NOT NULL)::integer + "
            "(course_offering_id IS NOT NULL)::integer = 1",
            name="ck_academic_sources_exactly_one_owner",
        ),
        CheckConstraint(
            "type IN ('STUDY_PLAN', 'SYLLABUS', 'SCHEDULE', "
            "'THEORETICAL_MATERIAL', 'PRACTICE_MATERIAL', 'OTHER')",
            name="ck_academic_sources_type",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'CONFIRMED', 'SUPERSEDED')",
            name="ck_academic_sources_status",
        ),
        CheckConstraint(
            "(type = 'STUDY_PLAN' AND study_plan_id IS NOT NULL) OR "
            "(type IN ('SYLLABUS', 'SCHEDULE', 'THEORETICAL_MATERIAL', "
            "'PRACTICE_MATERIAL') AND course_offering_id IS NOT NULL) OR "
            "type = 'OTHER'",
            name="ck_academic_sources_type_owner",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default=AcademicSourceStatus.PENDING)
    study_plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("study_plans.id", ondelete="RESTRICT"), nullable=True
    )
    course_offering_id: Mapped[int | None] = mapped_column(
        ForeignKey("course_offerings.id", ondelete="RESTRICT"), nullable=True
    )


class ExtractionProposal(Base):
    __tablename__ = "extraction_proposals"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'CONFIRMED', 'REJECTED')",
            name="ck_extraction_proposals_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    academic_source_id: Mapped[int] = mapped_column(
        ForeignKey("academic_sources.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(String, default=ProposalStatus.PENDING)
    extracted_data: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Unit(Base):
    __tablename__ = "units"
    __table_args__ = (
        CheckConstraint("position > 0", name="ck_units_position"),
        CheckConstraint("status IN ('ACTIVE', 'REMOVED')", name="ck_units_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    course_offering_id: Mapped[int] = mapped_column(
        ForeignKey("course_offerings.id", ondelete="RESTRICT")
    )
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    position: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String, default=StructureStatus.ACTIVE)
    confirmed_from_proposal_id: Mapped[int | None] = mapped_column(
        ForeignKey("extraction_proposals.id", ondelete="RESTRICT"), nullable=True
    )


class Topic(Base):
    __tablename__ = "topics"
    __table_args__ = (
        CheckConstraint("position > 0", name="ck_topics_position"),
        CheckConstraint("status IN ('ACTIVE', 'REMOVED')", name="ck_topics_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id", ondelete="RESTRICT"))
    name: Mapped[str] = mapped_column(String)
    position: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String, default=StructureStatus.ACTIVE)
    confirmed_from_proposal_id: Mapped[int | None] = mapped_column(
        ForeignKey("extraction_proposals.id", ondelete="RESTRICT"), nullable=True
    )


class Subtopic(Base):
    __tablename__ = "subtopics"
    __table_args__ = (CheckConstraint("position > 0", name="ck_subtopics_position"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="RESTRICT"))
    name: Mapped[str] = mapped_column(String)
    position: Mapped[int] = mapped_column(Integer)
    confirmed_from_proposal_id: Mapped[int | None] = mapped_column(
        ForeignKey("extraction_proposals.id", ondelete="RESTRICT"), nullable=True
    )
