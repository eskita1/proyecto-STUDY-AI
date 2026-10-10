from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.models.enrollment import CourseEnrollment, UserCourse
from app.services.enrollment import (
    CourseEnrollmentService,
    CourseOfferingService,
    EnrollmentConflictError,
    EnrollmentValidationError,
    UserCourseService,
)


def saved(entity):
    entity.id = 1
    return entity


def test_user_course_is_only_historical_relationship():
    repository = Mock()
    repository.find_equivalent.return_value = None
    repository.save.side_effect = saved
    service = UserCourseService(
        repository,
        Mock(get=Mock(return_value=object())),
        Mock(get=Mock(return_value=object())),
    )

    entity = service.create(user_id=1, study_plan_course_id=2)

    assert isinstance(entity, UserCourse)
    assert set(entity.__table__.columns.keys()) == {
        "id",
        "user_id",
        "study_plan_course_id",
    }


def test_offering_rejects_reversed_dates():
    repository = Mock()
    service = CourseOfferingService(repository, Mock(get=Mock(return_value=object())))

    with pytest.raises(EnrollmentValidationError):
        service.create(
            study_plan_course_id=1,
            name="A",
            academic_year=2026,
            term="ANNUAL",
            start_date=date(2026, 12, 1),
            end_date=date(2026, 3, 1),
        )


def test_enrollment_rejects_cross_course_attempt():
    service = CourseEnrollmentService(
        Mock(),
        Mock(get=Mock(return_value=SimpleNamespace(study_plan_course_id=1))),
        Mock(get=Mock(return_value=SimpleNamespace(study_plan_course_id=2))),
    )

    with pytest.raises(EnrollmentValidationError):
        service.create(
            user_course_id=1,
            course_offering_id=1,
            status="FAILED",
            final_grade=None,
        )


def test_enrollment_rejects_grade_and_parallel_active_attempt():
    repository = Mock()
    user_course_repository = Mock(
        get=Mock(return_value=SimpleNamespace(study_plan_course_id=1))
    )
    offering_repository = Mock(
        get=Mock(return_value=SimpleNamespace(study_plan_course_id=1))
    )
    service = CourseEnrollmentService(
        repository, user_course_repository, offering_repository
    )
    with pytest.raises(EnrollmentValidationError):
        service.create(
            user_course_id=1,
            course_offering_id=1,
            status="IN_PROGRESS",
            final_grade="10",
        )

    repository.find_active.return_value = CourseEnrollment()
    with pytest.raises(EnrollmentConflictError):
        service.create(
            user_course_id=1,
            course_offering_id=1,
            status="IN_PROGRESS",
            final_grade=None,
        )
