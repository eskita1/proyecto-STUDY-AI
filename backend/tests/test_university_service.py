from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.repositories.university import UniversityRepositoryConflictError
from app.services.university import (
    UniversityAlreadyExistsError,
    UniversityConflictError,
    UniversityNotFoundError,
    UniversityService,
    UniversityValidationError,
)


def make_service() -> tuple[UniversityService, Mock]:
    repository = Mock()
    repository.find_by_name_and_country.return_value = None
    return UniversityService(repository), repository


def test_create_normalizes_name_and_country_code():
    service, repository = make_service()
    university = SimpleNamespace(
        id=1,
        name="Universidad de Buenos Aires",
        country_code="AR",
    )
    repository.create.return_value = university

    result = service.create(
        name="  Universidad   de Buenos Aires  ",
        country_code="ar",
    )

    repository.create.assert_called_once_with(
        name="Universidad de Buenos Aires",
        country_code="AR",
    )
    assert result is university


def test_create_rejects_empty_name():
    service, _ = make_service()

    with pytest.raises(UniversityValidationError):
        service.create(name="  \t ", country_code="AR")


@pytest.mark.parametrize("country_code", ["A", "ARG", "A1", "áR"])
def test_create_rejects_invalid_country_code(country_code):
    service, _ = make_service()

    with pytest.raises(UniversityValidationError):
        service.create(name="University", country_code=country_code)


def test_create_rejects_existing_name_in_same_country():
    service, repository = make_service()
    repository.find_by_name_and_country.return_value = SimpleNamespace(id=1)

    with pytest.raises(UniversityAlreadyExistsError):
        service.create(name="University", country_code="AR")


def test_create_translates_database_conflict():
    service, repository = make_service()
    repository.create.side_effect = UniversityRepositoryConflictError

    with pytest.raises(UniversityAlreadyExistsError):
        service.create(name="University", country_code="AR")


def test_get_rejects_missing_university():
    service, repository = make_service()
    repository.get.return_value = None

    with pytest.raises(UniversityNotFoundError):
        service.get(99)


def test_update_preserves_unspecified_fields_and_checks_uniqueness():
    service, repository = make_service()
    university = SimpleNamespace(id=1, name="Original Name", country_code="AR")
    repository.get.return_value = university
    repository.update.return_value = university

    service.update(1, name="  Updated   Name ")

    repository.find_by_name_and_country.assert_called_once_with(
        name="Updated Name",
        country_code="AR",
        exclude_id=1,
    )
    repository.update.assert_called_once_with(
        university,
        name="Updated Name",
        country_code="AR",
    )


def test_delete_rejects_missing_university():
    service, repository = make_service()
    repository.get.return_value = None

    with pytest.raises(UniversityNotFoundError):
        service.delete(99)

    repository.delete.assert_not_called()


def test_delete_translates_persistence_conflict():
    service, repository = make_service()
    university = SimpleNamespace(id=1, name="University", country_code="AR")
    repository.get.return_value = university
    repository.delete.side_effect = UniversityRepositoryConflictError

    with pytest.raises(UniversityConflictError):
        service.delete(1)
