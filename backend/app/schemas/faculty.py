from pydantic import BaseModel, ConfigDict, Field, model_validator


class FacultyCreate(BaseModel):
    university_id: int = Field(gt=0)
    name: str = Field(min_length=1)


class FacultyUpdate(BaseModel):
    university_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_update_fields(self) -> "FacultyUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Faculty fields cannot be null")
        return self


class FacultyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    university_id: int
    name: str
