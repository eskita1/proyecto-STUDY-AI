from pydantic import BaseModel, ConfigDict, Field, model_validator


class UserCreate(BaseModel):
    pass


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int


class CareerCreate(BaseModel):
    faculty_id: int = Field(gt=0)
    name: str = Field(min_length=1)


class CareerUpdate(BaseModel):
    faculty_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_fields(self) -> "CareerUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Career fields cannot be null")
        return self


class CareerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    faculty_id: int
    name: str


class StudyPlanCreate(BaseModel):
    career_id: int = Field(gt=0)
    name: str = Field(min_length=1)


class StudyPlanUpdate(BaseModel):
    career_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_fields(self) -> "StudyPlanUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("StudyPlan fields cannot be null")
        return self


class StudyPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    career_id: int
    name: str


class CourseCreate(BaseModel):
    name: str = Field(min_length=1)
    code: str | None = None


class CourseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    code: str | None = None

    @model_validator(mode="after")
    def validate_fields(self) -> "CourseUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Course name cannot be null")
        return self


class CourseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: str | None


class StudyPlanCourseCreate(BaseModel):
    study_plan_id: int = Field(gt=0)
    course_id: int = Field(gt=0)


class StudyPlanCourseUpdate(BaseModel):
    study_plan_id: int | None = Field(default=None, gt=0)
    course_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_fields(self) -> "StudyPlanCourseUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("StudyPlanCourse fields cannot be null")
        return self


class StudyPlanCourseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    study_plan_id: int
    course_id: int


class UserCareerCreate(BaseModel):
    user_id: int = Field(gt=0)
    career_id: int = Field(gt=0)
    study_plan_id: int = Field(gt=0)


class UserCareerUpdate(BaseModel):
    user_id: int | None = Field(default=None, gt=0)
    career_id: int | None = Field(default=None, gt=0)
    study_plan_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_fields(self) -> "UserCareerUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("UserCareer fields cannot be null")
        return self


class UserCareerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    career_id: int
    study_plan_id: int
