from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.repositories.academic import AcademicStructureRepository
from app.repositories.enrollment import CourseEnrollmentRepository
from app.repositories.tracking import EnrollmentTopicRepository
from app.schemas.tracking import (
    EnrollmentTopicCreate,
    EnrollmentTopicRead,
    EnrollmentTopicUpdate,
    ProgressRead,
)
from app.services.tracking import (
    EnrollmentTopicService,
    ProgressService,
    TrackingConflictError,
    TrackingNotFoundError,
    TrackingValidationError,
)

router = APIRouter()
SessionDependency = Annotated[Session, Depends(get_db)]
TrackingError = (TrackingNotFoundError, TrackingConflictError, TrackingValidationError)


def tracking_service(session: Session) -> EnrollmentTopicService:
    structure = AcademicStructureRepository(session)
    return EnrollmentTopicService(
        EnrollmentTopicRepository(session),
        CourseEnrollmentRepository(session),
        structure,
        structure,
    )


def fail(error: Exception) -> None:
    if isinstance(error, TrackingNotFoundError):
        raise HTTPException(404, str(error)) from error
    if isinstance(error, TrackingConflictError):
        raise HTTPException(409, str(error)) from error
    if isinstance(error, TrackingValidationError):
        raise HTTPException(422, str(error)) from error
    raise error


@router.post("/enrollment-topics", response_model=EnrollmentTopicRead, status_code=201)
def create_enrollment_topic(payload: EnrollmentTopicCreate, session: SessionDependency):
    try:
        return tracking_service(session).create(**payload.model_dump())
    except TrackingError as error:
        fail(error)


@router.get("/enrollment-topics", response_model=list[EnrollmentTopicRead])
def list_enrollment_topics(
    session: SessionDependency, course_enrollment_id: int | None = None
):
    try:
        return tracking_service(session).list(course_enrollment_id)
    except TrackingError as error:
        fail(error)


@router.get("/enrollment-topics/{entity_id}", response_model=EnrollmentTopicRead)
def get_enrollment_topic(entity_id: int, session: SessionDependency):
    try:
        return tracking_service(session).get(entity_id)
    except TrackingError as error:
        fail(error)


@router.patch("/enrollment-topics/{entity_id}", response_model=EnrollmentTopicRead)
def update_enrollment_topic(
    entity_id: int, payload: EnrollmentTopicUpdate, session: SessionDependency
):
    try:
        return tracking_service(session).update(
            entity_id, **payload.model_dump(exclude_unset=True)
        )
    except TrackingError as error:
        fail(error)


@router.get(
    "/course-enrollments/{course_enrollment_id}/progress", response_model=ProgressRead
)
def get_progress(course_enrollment_id: int, session: SessionDependency):
    try:
        return ProgressService(
            EnrollmentTopicRepository(session), CourseEnrollmentRepository(session)
        ).calculate(course_enrollment_id)
    except TrackingError as error:
        fail(error)
