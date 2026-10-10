from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.repositories.academic import AcademicStructureRepository
from app.repositories.enrollment import CourseEnrollmentRepository
from app.repositories.practice import (
    PracticeExerciseRepository,
    PracticeSessionRepository,
    PracticeSessionTopicRepository,
)
from app.schemas.practice import (
    PracticeExerciseCreate,
    PracticeExerciseRead,
    PracticeSessionCreate,
    PracticeSessionRead,
    PracticeSessionTopicCreate,
    PracticeSessionTopicRead,
)
from app.services.practice import (
    PracticeConflictError,
    PracticeExerciseService,
    PracticeNotFoundError,
    PracticeSessionService,
    PracticeTopicService,
    PracticeValidationError,
)

router = APIRouter()
SessionDependency = Annotated[Session, Depends(get_db)]
PracticeError = (PracticeNotFoundError, PracticeConflictError, PracticeValidationError)


def fail(error: Exception) -> None:
    if isinstance(error, PracticeNotFoundError):
        raise HTTPException(404, str(error)) from error
    if isinstance(error, PracticeConflictError):
        raise HTTPException(409, str(error)) from error
    if isinstance(error, PracticeValidationError):
        raise HTTPException(422, str(error)) from error
    raise error


@router.post("/practice-sessions", response_model=PracticeSessionRead, status_code=201)
def create_practice_session(payload: PracticeSessionCreate, session: SessionDependency):
    try:
        return PracticeSessionService(
            PracticeSessionRepository(session), CourseEnrollmentRepository(session)
        ).create(**payload.model_dump())
    except PracticeError as error:
        fail(error)


@router.get("/practice-sessions", response_model=list[PracticeSessionRead])
def list_practice_sessions(
    session: SessionDependency, course_enrollment_id: int | None = None
):
    return PracticeSessionService(
        PracticeSessionRepository(session), CourseEnrollmentRepository(session)
    ).list(course_enrollment_id)


@router.get("/practice-sessions/{entity_id}", response_model=PracticeSessionRead)
def get_practice_session(entity_id: int, session: SessionDependency):
    try:
        return PracticeSessionService(
            PracticeSessionRepository(session), CourseEnrollmentRepository(session)
        ).get(entity_id)
    except PracticeError as error:
        fail(error)


@router.post(
    "/practice-session-topics", response_model=PracticeSessionTopicRead, status_code=201
)
def create_practice_topic(
    payload: PracticeSessionTopicCreate, session: SessionDependency
):
    try:
        return PracticeTopicService(
            PracticeSessionTopicRepository(session),
            PracticeSessionRepository(session),
            CourseEnrollmentRepository(session),
            AcademicStructureRepository(session),
        ).create(**payload.model_dump())
    except PracticeError as error:
        fail(error)


@router.get("/practice-session-topics", response_model=list[PracticeSessionTopicRead])
def list_practice_topics(
    session: SessionDependency, practice_session_id: int | None = None
):
    return PracticeTopicService(
        PracticeSessionTopicRepository(session),
        PracticeSessionRepository(session),
        CourseEnrollmentRepository(session),
        AcademicStructureRepository(session),
    ).list(practice_session_id)


@router.post(
    "/practice-exercises", response_model=PracticeExerciseRead, status_code=201
)
def create_practice_exercise(
    payload: PracticeExerciseCreate, session: SessionDependency
):
    try:
        return PracticeExerciseService(
            PracticeExerciseRepository(session), PracticeSessionRepository(session)
        ).create(**payload.model_dump())
    except PracticeError as error:
        fail(error)


@router.get("/practice-exercises", response_model=list[PracticeExerciseRead])
def list_practice_exercises(
    session: SessionDependency, practice_session_id: int | None = None
):
    return PracticeExerciseService(
        PracticeExerciseRepository(session), PracticeSessionRepository(session)
    ).list(practice_session_id)
