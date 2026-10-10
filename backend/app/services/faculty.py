from app.models.faculty import Faculty
from app.repositories.faculty import (
    FacultyRepository,
    FacultyRepositoryConflictError,
)
from app.repositories.university import UniversityRepository


class FacultyNotFoundError(Exception):
    pass


class FacultyUniversityNotFoundError(Exception):
    pass


class FacultyAlreadyExistsError(Exception):
    pass


class FacultyConflictError(Exception):
    pass


class FacultyValidationError(Exception):
    pass


class FacultyService:
    def __init__(
        self,
        repository: FacultyRepository,
        university_repository: UniversityRepository,
    ) -> None:
        self.repository = repository
        self.university_repository = university_repository

    def create(self, *, university_id: int, name: str) -> Faculty:
        normalized_name = self._normalize_name(name)
        self._ensure_university_exists(university_id)
        self._ensure_unique(
            name=normalized_name,
            university_id=university_id,
        )
        try:
            return self.repository.create(
                university_id=university_id,
                name=normalized_name,
            )
        except FacultyRepositoryConflictError as error:
            raise FacultyAlreadyExistsError from error

    def get(self, faculty_id: int) -> Faculty:
        faculty = self.repository.get(faculty_id)
        if faculty is None:
            raise FacultyNotFoundError
        return faculty

    def list(self) -> list[Faculty]:
        return self.repository.list()

    def update(
        self,
        faculty_id: int,
        *,
        university_id: int | None = None,
        name: str | None = None,
    ) -> Faculty:
        faculty = self.get(faculty_id)
        target_university_id = (
            faculty.university_id if university_id is None else university_id
        )
        normalized_name = (
            faculty.name if name is None else self._normalize_name(name)
        )
        self._ensure_university_exists(target_university_id)
        self._ensure_unique(
            name=normalized_name,
            university_id=target_university_id,
            exclude_id=faculty.id,
        )
        try:
            return self.repository.update(
                faculty,
                university_id=target_university_id,
                name=normalized_name,
            )
        except FacultyRepositoryConflictError as error:
            raise FacultyAlreadyExistsError from error

    def delete(self, faculty_id: int) -> None:
        faculty = self.get(faculty_id)
        try:
            self.repository.delete(faculty)
        except FacultyRepositoryConflictError as error:
            raise FacultyConflictError from error

    def _ensure_university_exists(self, university_id: int) -> None:
        if self.university_repository.get(university_id) is None:
            raise FacultyUniversityNotFoundError

    def _ensure_unique(
        self,
        *,
        name: str,
        university_id: int,
        exclude_id: int | None = None,
    ) -> None:
        existing = self.repository.find_by_name_and_university(
            name=name,
            university_id=university_id,
            exclude_id=exclude_id,
        )
        if existing is not None:
            raise FacultyAlreadyExistsError

    @staticmethod
    def _normalize_name(name: str) -> str:
        normalized_name = " ".join(name.split())
        if not normalized_name:
            raise FacultyValidationError("Faculty name cannot be empty")
        return normalized_name
