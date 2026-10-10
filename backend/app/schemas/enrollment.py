from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enrollment import AcademicTerm, EnrollmentStatus


class NonEmptyUpdate(BaseModel):
    @model_validator(mode="after")
    def require_field(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class UserCourseCreate(BaseModel):
    user_id: int = Field(gt=0)
    study_plan_course_id: int = Field(gt=0)


class UserCourseUpdate(NonEmptyUpdate):
    user_id: int | None = Field(default=None, gt=0)
    study_plan_course_id: int | None = Field(default=None, gt=0)


class UserCourseRead(UserCourseCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class CourseOfferingCreate(BaseModel):
    study_plan_course_id: int = Field(gt=0)
    name: str = Field(min_length=1)
    academic_year: int = Field(gt=0)
    term: AcademicTerm
    start_date: date | None = None
    end_date: date | None = None


class CourseOfferingUpdate(NonEmptyUpdate):
    study_plan_course_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=1)
    academic_year: int | None = Field(default=None, gt=0)
    term: AcademicTerm | None = None
    start_date: date | None = None
    end_date: date | None = None


class CourseOfferingRead(CourseOfferingCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class CourseEnrollmentCreate(BaseModel):
    user_course_id: int = Field(gt=0)
    course_offering_id: int = Field(gt=0)
    status: EnrollmentStatus = EnrollmentStatus.IN_PROGRESS
    final_grade: str | None = None


class CourseEnrollmentUpdate(NonEmptyUpdate):
    user_course_id: int | None = Field(default=None, gt=0)
    course_offering_id: int | None = Field(default=None, gt=0)
    status: EnrollmentStatus | None = None
    final_grade: str | None = None


class CourseEnrollmentRead(CourseEnrollmentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
