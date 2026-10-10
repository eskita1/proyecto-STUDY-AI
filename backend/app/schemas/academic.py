from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.academic import AcademicSourceStatus, AcademicSourceType, ProposalStatus


class ChangeAction(StrEnum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    REMOVE = "REMOVE"


class SubtopicChange(BaseModel):
    id: int | None = Field(default=None, gt=0)
    action: ChangeAction
    name: str | None = None
    position: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_action(self):
        validate_change(self.action, self.id, self.name, self.position)
        return self


class TopicChange(BaseModel):
    id: int | None = Field(default=None, gt=0)
    action: ChangeAction
    name: str | None = None
    position: int | None = Field(default=None, gt=0)
    subtopics: list[SubtopicChange] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_action(self):
        validate_change(self.action, self.id, self.name, self.position)
        if self.action == ChangeAction.REMOVE and self.subtopics:
            raise ValueError("REMOVE Topic cannot contain nested changes")
        return self


class UnitChange(BaseModel):
    id: int | None = Field(default=None, gt=0)
    action: ChangeAction
    name: str | None = None
    description: str | None = None
    position: int | None = Field(default=None, gt=0)
    topics: list[TopicChange] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_action(self):
        validate_change(self.action, self.id, self.name, self.position)
        if self.action == ChangeAction.REMOVE and self.topics:
            raise ValueError("REMOVE Unit cannot contain nested changes")
        return self


def validate_change(
    action: ChangeAction, entity_id: int | None, name: str | None, position: int | None
) -> None:
    if action == ChangeAction.CREATE and entity_id is not None:
        raise ValueError("CREATE requires a null id")
    if action != ChangeAction.CREATE and entity_id is None:
        raise ValueError(f"{action} requires an existing id")
    if action != ChangeAction.REMOVE and (name is None or position is None):
        raise ValueError(f"{action} requires name and position")


class CourseStructurePayload(BaseModel):
    units: list[UnitChange]


class AcademicSourceCreate(BaseModel):
    type: AcademicSourceType
    study_plan_id: int | None = Field(default=None, gt=0)
    course_offering_id: int | None = Field(default=None, gt=0)


class AcademicSourceRead(AcademicSourceCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: AcademicSourceStatus


class ExtractionProposalCreate(BaseModel):
    academic_source_id: int = Field(gt=0)
    extracted_data: dict


class ExtractionProposalRead(ExtractionProposalCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: ProposalStatus
    created_at: datetime
    reviewed_at: datetime | None


class UnitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    course_offering_id: int
    name: str
    description: str | None
    position: int
    status: str
    confirmed_from_proposal_id: int | None


class TopicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    unit_id: int
    name: str
    position: int
    status: str
    confirmed_from_proposal_id: int | None


class SubtopicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    topic_id: int
    name: str
    position: int
    confirmed_from_proposal_id: int | None
