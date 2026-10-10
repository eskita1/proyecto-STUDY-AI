from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.repositories.academic import AcademicStructureRepository
from app.repositories.enrollment import CourseEnrollmentRepository
from app.repositories.study import StudySessionRepository, StudySessionTopicRepository
from app.schemas.study import (
    LastStudiedRead,
    StudySessionCreate,
    StudySessionRead,
    StudySessionTopicCreate,
    StudySessionTopicRead,
)
from app.services.study import (
    StudyConflictError,
    StudyNotFoundError,
    StudySessionService,
    StudySessionTopicService,
    StudyValidationError,
)

router = APIRouter()
SessionDependency = Annotated[Session, Depends(get_db)]
StudyError = (StudyNotFoundError, StudyConflictError, StudyValidationError)


def topic_service(session: Session) -> StudySessionTopicService:
    return StudySessionTopicService(
        StudySessionTopicRepository(session),
        StudySessionRepository(session),
        CourseEnrollmentRepository(session),
        AcademicStructureRepository(session),
    )


def fail(error: Exception) -> None:
    if isinstance(error, StudyNotFoundError):
        raise HTTPException(404, str(error)) from error
    if isinstance(error, StudyConflictError):
        raise HTTPException(409, str(error)) from error
    if isinstance(error, StudyValidationError):
        raise HTTPException(422, str(error)) from error
    raise error


@router.post("/study-sessions", response_model=StudySessionRead, status_code=201)
def create_study_session(payload: StudySessionCreate, session: SessionDependency):
    try:
        return StudySessionService(
            StudySessionRepository(session), CourseEnrollmentRepository(session)
        ).create(**payload.model_dump())
    except StudyError as error:
        fail(error)


@router.get("/study-sessions", response_model=list[StudySessionRead])
def list_study_sessions(
    session: SessionDependency, course_enrollment_id: int | None = None
):
    return StudySessionService(
        StudySessionRepository(session), CourseEnrollmentRepository(session)
    ).list(course_enrollment_id)


@router.get("/study-sessions/{entity_id}", response_model=StudySessionRead)
def get_study_session(entity_id: int, session: SessionDependency):
    try:
        return StudySessionService(
            StudySessionRepository(session), CourseEnrollmentRepository(session)
        ).get(entity_id)
    except StudyError as error:
        fail(error)


@router.post(
    "/study-session-topics", response_model=StudySessionTopicRead, status_code=201
)
def create_study_session_topic(
    payload: StudySessionTopicCreate, session: SessionDependency
):
    try:
        return topic_service(session).create(**payload.model_dump())
    except StudyError as error:
        fail(error)


@router.get("/study-session-topics", response_model=list[StudySessionTopicRead])
def list_study_session_topics(
    session: SessionDependency, study_session_id: int | None = None
):
    return topic_service(session).list(study_session_id)


@router.get(
    "/course-enrollments/{enrollment_id}/topics/{topic_id}/last-studied",
    response_model=LastStudiedRead,
)
def last_studied(enrollment_id: int, topic_id: int, session: SessionDependency):
    try:
        return topic_service(session).last_studied(enrollment_id, topic_id)
    except StudyError as error:
        fail(error)
