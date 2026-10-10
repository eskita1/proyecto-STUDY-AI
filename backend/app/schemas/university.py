from pydantic import BaseModel, ConfigDict, Field, model_validator


class UniversityCreate(BaseModel):
    name: str = Field(min_length=1)
    country_code: str = Field(
        min_length=2,
        max_length=2,
        pattern=r"^[A-Za-z]{2}$",
    )


class UniversityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    country_code: str | None = Field(
        default=None,
        min_length=2,
        max_length=2,
        pattern=r"^[A-Za-z]{2}$",
    )

    @model_validator(mode="after")
    def validate_update_fields(self) -> "UniversityUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("University fields cannot be null")
        return self


class UniversityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    country_code: str
