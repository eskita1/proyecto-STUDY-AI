from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StudySessionCreate(BaseModel):
    course_enrollment_id: int = Field(gt=0)
    started_at: datetime
    ended_at: datetime | None = None
    note: str | None = None

    @field_validator("started_at", "ended_at")
    @classmethod
    def timezone_aware(cls, value: datetime | None):
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def time_order(self):
        if self.ended_at is not None and self.ended_at < self.started_at:
            raise ValueError("ended_at must be on or after started_at")
        return self


class StudySessionRead(StudySessionCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class StudySessionTopicCreate(BaseModel):
    study_session_id: int = Field(gt=0)
    topic_id: int = Field(gt=0)


class StudySessionTopicRead(StudySessionTopicCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class LastStudiedRead(BaseModel):
    course_enrollment_id: int
    topic_id: int
    last_studied_at: datetime | None
