from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.tracking import CourseProgressStatus, StudentStatus


class EnrollmentTopicCreate(BaseModel):
    course_enrollment_id: int = Field(gt=0)
    topic_id: int = Field(gt=0)
    course_progress_status: CourseProgressStatus = CourseProgressStatus.NOT_SEEN
    student_status: StudentStatus = StudentStatus.NOT_STARTED
    personal_note: str | None = None


class EnrollmentTopicUpdate(BaseModel):
    course_progress_status: CourseProgressStatus | None = None
    student_status: StudentStatus | None = None
    personal_note: str | None = None

    @model_validator(mode="after")
    def require_field(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if (
            "course_progress_status" in self.model_fields_set
            and self.course_progress_status is None
        ):
            raise ValueError("course_progress_status cannot be null")
        if "student_status" in self.model_fields_set and self.student_status is None:
            raise ValueError("student_status cannot be null")
        return self


class EnrollmentTopicRead(EnrollmentTopicCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ProgressRead(BaseModel):
    active_topic_count: int
    seen_topic_count: int
    studied_topic_count: int
    seen_and_studied_topic_count: int
    course_progress: float | None
    student_progress: float | None
    catch_up_progress: float | None
    academic_gap_topic_ids: list[int]
