from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.planning import AssessmentType


class CourseScheduleItemCreate(BaseModel):
    course_offering_id: int = Field(gt=0)
    scheduled_date: date
    unit_id: int | None = Field(default=None, gt=0)
    topic_id: int | None = Field(default=None, gt=0)
    position: int = Field(gt=0)

    @model_validator(mode="after")
    def exactly_one_target(self):
        if (self.unit_id is None) == (self.topic_id is None):
            raise ValueError("Exactly one of unit_id or topic_id is required")
        return self


class CourseScheduleItemRead(CourseScheduleItemCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class AssessmentCreate(BaseModel):
    course_offering_id: int = Field(gt=0)
    name: str = Field(min_length=1)
    type: AssessmentType
    date: date
    description: str | None = None


class AssessmentRead(AssessmentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class AssessmentTopicCreate(BaseModel):
    assessment_id: int = Field(gt=0)
    topic_id: int = Field(gt=0)


class AssessmentTopicRead(AssessmentTopicCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class AssessmentPreparationRead(BaseModel):
    assessment_id: int
    active_topic_count: int
    studied_topic_count: int
    preparation_coverage: float | None
