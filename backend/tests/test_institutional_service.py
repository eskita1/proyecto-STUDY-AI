from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services.institutional import (
    CareerService,
    CourseService,
    InstitutionalConflictError,
    InstitutionalNotFoundError,
    InstitutionalValidationError,
    StudyPlanCourseService,
    UserCareerService,
)


def test_career_normalizes_name_and_validates_faculty():
    repository = Mock()
    repository.find_equivalent.return_value = None
    repository.create.return_value = SimpleNamespace(id=1)
    faculty_repository = Mock()
    faculty_repository.get.return_value = SimpleNamespace(id=2)

    CareerService(repository, faculty_repository).create(
        faculty_id=2, name="  Computer   Engineering "
    )

    repository.create.assert_called_once_with(
        faculty_id=2, name="Computer Engineering"
    )


def test_career_rejects_missing_faculty_and_duplicate():
    repository = Mock()
    faculty_repository = Mock()
    faculty_repository.get.return_value = None
    service = CareerService(repository, faculty_repository)

    with pytest.raises(InstitutionalNotFoundError):
        service.create(faculty_id=99, name="Engineering")

    faculty_repository.get.return_value = SimpleNamespace(id=1)
    repository.find_equivalent.return_value = SimpleNamespace(id=1)
    with pytest.raises(InstitutionalConflictError):
        service.create(faculty_id=1, name="Engineering")


def test_course_rejects_blank_and_duplicate_name():
    repository = Mock()
    repository.find_equivalent.return_value = None
    service = CourseService(repository)

    with pytest.raises(InstitutionalValidationError):
        service.create(name="   ")

    repository.find_equivalent.return_value = SimpleNamespace(id=1)
    with pytest.raises(InstitutionalConflictError):
        service.create(name="Algorithms")


def test_study_plan_course_validates_both_parents():
    repository = Mock()
    study_plan_repository = Mock()
    course_repository = Mock()
    service = StudyPlanCourseService(
        repository, study_plan_repository, course_repository
    )
    study_plan_repository.get.return_value = None

    with pytest.raises(InstitutionalNotFoundError):
        service.create(study_plan_id=1, course_id=1)

    study_plan_repository.get.return_value = SimpleNamespace(id=1)
    course_repository.get.return_value = None
    with pytest.raises(InstitutionalNotFoundError):
        service.create(study_plan_id=1, course_id=1)


def test_user_career_requires_study_plan_from_selected_career():
    repository = Mock()
    user_repository = Mock()
    career_repository = Mock()
    study_plan_repository = Mock()
    user_repository.get.return_value = SimpleNamespace(id=1)
    career_repository.get.return_value = SimpleNamespace(id=2)
    study_plan_repository.get.return_value = SimpleNamespace(id=3, career_id=99)
    service = UserCareerService(
        repository,
        user_repository,
        career_repository,
        study_plan_repository,
    )

    with pytest.raises(InstitutionalValidationError):
        service.create(user_id=1, career_id=2, study_plan_id=3)


def test_user_career_rejects_equivalent_relationship():
    repository = Mock()
    repository.find_equivalent.return_value = SimpleNamespace(id=5)
    user_repository = Mock()
    career_repository = Mock()
    study_plan_repository = Mock()
    user_repository.get.return_value = SimpleNamespace(id=1)
    career_repository.get.return_value = SimpleNamespace(id=2)
    study_plan_repository.get.return_value = SimpleNamespace(id=3, career_id=2)
    service = UserCareerService(
        repository,
        user_repository,
        career_repository,
        study_plan_repository,
    )

    with pytest.raises(InstitutionalConflictError):
        service.create(user_id=1, career_id=2, study_plan_id=3)
