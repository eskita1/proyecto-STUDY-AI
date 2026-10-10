import re

from app.models.university import University
from app.repositories.university import (
    UniversityRepository,
    UniversityRepositoryConflictError,
)

COUNTRY_CODE_PATTERN = re.compile(r"^[A-Z]{2}$")


class UniversityNotFoundError(Exception):
    pass


class UniversityAlreadyExistsError(Exception):
    pass


class UniversityConflictError(Exception):
    pass


class UniversityValidationError(Exception):
    pass


class UniversityService:
    def __init__(self, repository: UniversityRepository) -> None:
        self.repository = repository

    def create(self, *, name: str, country_code: str) -> University:
        normalized_name = self._normalize_name(name)
        normalized_country_code = self._normalize_country_code(country_code)
        self._ensure_unique(
            name=normalized_name,
            country_code=normalized_country_code,
        )
        try:
            return self.repository.create(
                name=normalized_name,
                country_code=normalized_country_code,
            )
        except UniversityRepositoryConflictError as error:
            raise UniversityAlreadyExistsError from error

    def get(self, university_id: int) -> University:
        university = self.repository.get(university_id)
        if university is None:
            raise UniversityNotFoundError
        return university

    def list(self) -> list[University]:
        return self.repository.list()

    def update(
        self,
        university_id: int,
        *,
        name: str | None = None,
        country_code: str | None = None,
    ) -> University:
        university = self.get(university_id)
        normalized_name = (
            university.name if name is None else self._normalize_name(name)
        )
        normalized_country_code = (
            university.country_code
            if country_code is None
            else self._normalize_country_code(country_code)
        )
        self._ensure_unique(
            name=normalized_name,
            country_code=normalized_country_code,
            exclude_id=university.id,
        )
        try:
            return self.repository.update(
                university,
                name=normalized_name,
                country_code=normalized_country_code,
            )
        except UniversityRepositoryConflictError as error:
            raise UniversityAlreadyExistsError from error

    def delete(self, university_id: int) -> None:
        university = self.get(university_id)
        try:
            self.repository.delete(university)
        except UniversityRepositoryConflictError as error:
            raise UniversityConflictError from error

    def _ensure_unique(
        self,
        *,
        name: str,
        country_code: str,
        exclude_id: int | None = None,
    ) -> None:
        existing = self.repository.find_by_name_and_country(
            name=name,
            country_code=country_code,
            exclude_id=exclude_id,
        )
        if existing is not None:
            raise UniversityAlreadyExistsError

    @staticmethod
    def _normalize_name(name: str) -> str:
        normalized_name = " ".join(name.split())
        if not normalized_name:
            raise UniversityValidationError("University name cannot be empty")
        return normalized_name

    @staticmethod
    def _normalize_country_code(country_code: str) -> str:
        normalized_country_code = country_code.upper()
        if COUNTRY_CODE_PATTERN.fullmatch(normalized_country_code) is None:
            raise UniversityValidationError(
                "country_code must be a two-letter ISO 3166-1 alpha-2 code"
            )
        return normalized_country_code
