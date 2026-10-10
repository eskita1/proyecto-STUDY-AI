from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.repositories.academic import AcademicStructureRepository
from app.repositories.enrollment import (
    CourseEnrollmentRepository,
    CourseOfferingRepository,
)
from app.repositories.planning import (
    AssessmentRepository,
    AssessmentTopicRepository,
    CourseScheduleItemRepository,
)
from app.repositories.tracking import EnrollmentTopicRepository
from app.schemas.planning import (
    AssessmentCreate,
    AssessmentPreparationRead,
    AssessmentRead,
    AssessmentTopicCreate,
    AssessmentTopicRead,
    CourseScheduleItemCreate,
    CourseScheduleItemRead,
)
from app.services.planning import (
    AssessmentPreparationService,
    AssessmentService,
    AssessmentTopicService,
    PlanningConflictError,
    PlanningNotFoundError,
    PlanningValidationError,
    ScheduleService,
)

router = APIRouter()
SessionDependency = Annotated[Session, Depends(get_db)]
PlanningError = (PlanningNotFoundError, PlanningConflictError, PlanningValidationError)


def fail(error: Exception) -> None:
    if isinstance(error, PlanningNotFoundError):
        raise HTTPException(404, str(error)) from error
    if isinstance(error, PlanningConflictError):
        raise HTTPException(409, str(error)) from error
    if isinstance(error, PlanningValidationError):
        raise HTTPException(422, str(error)) from error
    raise error


@router.post(
    "/course-schedule-items", response_model=CourseScheduleItemRead, status_code=201
)
def create_schedule_item(payload: CourseScheduleItemCreate, session: SessionDependency):
    try:
        return ScheduleService(
            CourseScheduleItemRepository(session),
            CourseOfferingRepository(session),
            AcademicStructureRepository(session),
        ).create(**payload.model_dump())
    except PlanningError as error:
        fail(error)


@router.get("/course-schedule-items", response_model=list[CourseScheduleItemRead])
def list_schedule_items(session: SessionDependency):
    return ScheduleService(
        CourseScheduleItemRepository(session),
        CourseOfferingRepository(session),
        AcademicStructureRepository(session),
    ).list()


@router.post("/assessments", response_model=AssessmentRead, status_code=201)
def create_assessment(payload: AssessmentCreate, session: SessionDependency):
    try:
        return AssessmentService(
            AssessmentRepository(session), CourseOfferingRepository(session)
        ).create(**payload.model_dump())
    except PlanningError as error:
        fail(error)


@router.get("/assessments", response_model=list[AssessmentRead])
def list_assessments(session: SessionDependency):
    return AssessmentService(
        AssessmentRepository(session), CourseOfferingRepository(session)
    ).list()


@router.get("/assessments/{entity_id}", response_model=AssessmentRead)
def get_assessment(entity_id: int, session: SessionDependency):
    try:
        return AssessmentService(
            AssessmentRepository(session), CourseOfferingRepository(session)
        ).get(entity_id)
    except PlanningError as error:
        fail(error)


@router.post("/assessment-topics", response_model=AssessmentTopicRead, status_code=201)
def create_assessment_topic(payload: AssessmentTopicCreate, session: SessionDependency):
    try:
        return AssessmentTopicService(
            AssessmentTopicRepository(session),
            AssessmentRepository(session),
            AcademicStructureRepository(session),
        ).create(**payload.model_dump())
    except PlanningError as error:
        fail(error)


@router.get("/assessment-topics", response_model=list[AssessmentTopicRead])
def list_assessment_topics(
    session: SessionDependency, assessment_id: int | None = None
):
    return AssessmentTopicService(
        AssessmentTopicRepository(session),
        AssessmentRepository(session),
        AcademicStructureRepository(session),
    ).list(assessment_id)


@router.get(
    "/course-enrollments/{enrollment_id}/assessments/{assessment_id}/preparation",
    response_model=AssessmentPreparationRead,
)
def assessment_preparation(
    enrollment_id: int, assessment_id: int, session: SessionDependency
):
    try:
        return AssessmentPreparationService(
            AssessmentRepository(session),
            AssessmentTopicRepository(session),
            AcademicStructureRepository(session),
            CourseEnrollmentRepository(session),
            EnrollmentTopicRepository(session),
        ).calculate(enrollment_id, assessment_id)
    except PlanningError as error:
        fail(error)
