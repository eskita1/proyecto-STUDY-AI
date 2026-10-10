from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.practice import ExerciseResult, PracticeMode


class PracticeSessionCreate(BaseModel):
    course_enrollment_id: int = Field(gt=0)
    occurred_at: datetime
    source_type: str = Field(min_length=1)
    source_name: str = Field(min_length=1)
    note: str | None = None
    mode: PracticeMode
    total_exercises: int | None = Field(default=None, ge=0)
    correct_exercises: int | None = Field(default=None, ge=0)
    partial_exercises: int | None = Field(default=None, ge=0)
    incorrect_exercises: int | None = Field(default=None, ge=0)

    @field_validator("occurred_at")
    @classmethod
    def timezone_aware(cls, value: datetime):
        if value.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_mode(self):
        counts = (
            self.total_exercises,
            self.correct_exercises,
            self.partial_exercises,
            self.incorrect_exercises,
        )
        if self.mode == PracticeMode.QUICK:
            if any(value is None for value in counts):
                raise ValueError("QUICK mode requires all aggregate counts")
            if self.total_exercises != sum(counts[1:]):
                raise ValueError("Practice counts must sum to total_exercises")
        elif any(value is not None for value in counts):
            raise ValueError("DETAILED mode cannot contain aggregate counts")
        return self


class PracticeSessionRead(PracticeSessionCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class PracticeSessionTopicCreate(BaseModel):
    practice_session_id: int = Field(gt=0)
    topic_id: int = Field(gt=0)


class PracticeSessionTopicRead(PracticeSessionTopicCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class PracticeExerciseCreate(BaseModel):
    practice_session_id: int = Field(gt=0)
    label: str = Field(min_length=1)
    result: ExerciseResult


class PracticeExerciseRead(PracticeExerciseCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
