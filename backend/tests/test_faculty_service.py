from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.repositories.faculty import FacultyRepositoryConflictError
from app.services.faculty import (
    FacultyAlreadyExistsError,
    FacultyConflictError,
    FacultyNotFoundError,
    FacultyService,
    FacultyUniversityNotFoundError,
    FacultyValidationError,
)


def make_service() -> tuple[FacultyService, Mock, Mock]:
    repository = Mock()
    repository.find_by_name_and_university.return_value = None
    university_repository = Mock()
    university_repository.get.return_value = SimpleNamespace(id=1)
    return (
        FacultyService(repository, university_repository),
        repository,
        university_repository,
    )


def test_create_normalizes_name_and_validates_university():
    service, repository, university_repository = make_service()
    faculty = SimpleNamespace(id=1, university_id=1, name="Facultad de Ingeniería")
    repository.create.return_value = faculty

    result = service.create(
        university_id=1,
        name="  Facultad   de Ingeniería ",
    )

    university_repository.get.assert_called_once_with(1)
    repository.find_by_name_and_university.assert_called_once_with(
        name="Facultad de Ingeniería",
        university_id=1,
        exclude_id=None,
    )
    repository.create.assert_called_once_with(
        university_id=1,
        name="Facultad de Ingeniería",
    )
    assert result is faculty


def test_create_rejects_empty_name():
    service, repository, university_repository = make_service()

    with pytest.raises(FacultyValidationError):
        service.create(university_id=1, name="  \t ")

    university_repository.get.assert_not_called()
    repository.create.assert_not_called()


def test_create_rejects_missing_university():
    service, repository, university_repository = make_service()
    university_repository.get.return_value = None

    with pytest.raises(FacultyUniversityNotFoundError):
        service.create(university_id=99, name="Engineering")

    repository.find_by_name_and_university.assert_not_called()
    repository.create.assert_not_called()


def test_create_rejects_duplicate_in_same_university():
    service, repository, _ = make_service()
    repository.find_by_name_and_university.return_value = SimpleNamespace(id=1)

    with pytest.raises(FacultyAlreadyExistsError):
        service.create(university_id=1, name="Engineering")

    repository.create.assert_not_called()


def test_create_translates_database_conflict():
    service, repository, _ = make_service()
    repository.create.side_effect = FacultyRepositoryConflictError

    with pytest.raises(FacultyAlreadyExistsError):
        service.create(university_id=1, name="Engineering")


def test_get_returns_existing_faculty():
    service, repository, _ = make_service()
    faculty = SimpleNamespace(id=1, university_id=1, name="Engineering")
    repository.get.return_value = faculty

    assert service.get(1) is faculty


def test_get_rejects_missing_faculty():
    service, repository, _ = make_service()
    repository.get.return_value = None

    with pytest.raises(FacultyNotFoundError):
        service.get(99)


def test_update_name_preserves_university_and_excludes_self():
    service, repository, university_repository = make_service()
    faculty = SimpleNamespace(id=1, university_id=1, name="Original Name")
    repository.get.return_value = faculty
    repository.update.return_value = faculty

    service.update(1, name="  Updated   Name ")

    university_repository.get.assert_called_once_with(1)
    repository.find_by_name_and_university.assert_called_once_with(
        name="Updated Name",
        university_id=1,
        exclude_id=1,
    )
    repository.update.assert_called_once_with(
        faculty,
        university_id=1,
        name="Updated Name",
    )


def test_update_moves_faculty_to_existing_university():
    service, repository, university_repository = make_service()
    faculty = SimpleNamespace(id=1, university_id=1, name="Engineering")
    repository.get.return_value = faculty
    repository.update.return_value = faculty

    service.update(1, university_id=2)

    university_repository.get.assert_called_once_with(2)
    repository.find_by_name_and_university.assert_called_once_with(
        name="Engineering",
        university_id=2,
        exclude_id=1,
    )
    repository.update.assert_called_once_with(
        faculty,
        university_id=2,
        name="Engineering",
    )


def test_update_rejects_missing_destination_university():
    service, repository, university_repository = make_service()
    repository.get.return_value = SimpleNamespace(
        id=1,
        university_id=1,
        name="Engineering",
    )
    university_repository.get.return_value = None

    with pytest.raises(FacultyUniversityNotFoundError):
        service.update(1, university_id=99)

    repository.update.assert_not_called()


def test_update_rejects_duplicate_in_destination_university():
    service, repository, _ = make_service()
    repository.get.return_value = SimpleNamespace(
        id=1,
        university_id=1,
        name="Engineering",
    )
    repository.find_by_name_and_university.return_value = SimpleNamespace(id=2)

    with pytest.raises(FacultyAlreadyExistsError):
        service.update(1, university_id=2)

    repository.update.assert_not_called()


def test_update_rejects_missing_faculty():
    service, repository, university_repository = make_service()
    repository.get.return_value = None

    with pytest.raises(FacultyNotFoundError):
        service.update(99, name="Engineering")

    university_repository.get.assert_not_called()
    repository.update.assert_not_called()


def test_update_translates_database_conflict():
    service, repository, _ = make_service()
    faculty = SimpleNamespace(id=1, university_id=1, name="Engineering")
    repository.get.return_value = faculty
    repository.update.side_effect = FacultyRepositoryConflictError

    with pytest.raises(FacultyAlreadyExistsError):
        service.update(1, name="Science")


def test_delete_existing_faculty():
    service, repository, _ = make_service()
    faculty = SimpleNamespace(id=1, university_id=1, name="Engineering")
    repository.get.return_value = faculty

    service.delete(1)

    repository.delete.assert_called_once_with(faculty)


def test_delete_rejects_missing_faculty():
    service, repository, _ = make_service()
    repository.get.return_value = None

    with pytest.raises(FacultyNotFoundError):
        service.delete(99)

    repository.delete.assert_not_called()


def test_delete_translates_persistence_conflict():
    service, repository, _ = make_service()
    repository.get.return_value = SimpleNamespace(
        id=1,
        university_id=1,
        name="Engineering",
    )
    repository.delete.side_effect = FacultyRepositoryConflictError

    with pytest.raises(FacultyConflictError):
        service.delete(1)
