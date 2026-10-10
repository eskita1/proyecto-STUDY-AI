from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.repositories.enrollment import (
    CourseEnrollmentRepository,
    CourseOfferingRepository,
    UserCourseRepository,
)
from app.repositories.institutional import StudyPlanCourseRepository, UserRepository
from app.schemas.enrollment import (
    CourseEnrollmentCreate,
    CourseEnrollmentRead,
    CourseEnrollmentUpdate,
    CourseOfferingCreate,
    CourseOfferingRead,
    CourseOfferingUpdate,
    UserCourseCreate,
    UserCourseRead,
    UserCourseUpdate,
)
from app.services.enrollment import (
    CourseEnrollmentService,
    CourseOfferingService,
    EnrollmentConflictError,
    EnrollmentNotFoundError,
    EnrollmentValidationError,
    UserCourseService,
)

router = APIRouter()
SessionDependency = Annotated[Session, Depends(get_db)]
EnrollmentError = (
    EnrollmentNotFoundError,
    EnrollmentConflictError,
    EnrollmentValidationError,
)


def user_course_service(session: Session) -> UserCourseService:
    return UserCourseService(
        UserCourseRepository(session),
        UserRepository(session),
        StudyPlanCourseRepository(session),
    )


def offering_service(session: Session) -> CourseOfferingService:
    return CourseOfferingService(
        CourseOfferingRepository(session), StudyPlanCourseRepository(session)
    )


def enrollment_service(session: Session) -> CourseEnrollmentService:
    return CourseEnrollmentService(
        CourseEnrollmentRepository(session),
        UserCourseRepository(session),
        CourseOfferingRepository(session),
    )


def fail(error: Exception) -> None:
    if isinstance(error, EnrollmentNotFoundError):
        raise HTTPException(404, str(error)) from error
    if isinstance(error, EnrollmentConflictError):
        raise HTTPException(409, str(error)) from error
    if isinstance(error, EnrollmentValidationError):
        raise HTTPException(422, str(error)) from error
    raise error


@router.post("/user-courses", response_model=UserCourseRead, status_code=201)
def create_user_course(payload: UserCourseCreate, session: SessionDependency):
    try:
        return user_course_service(session).create(**payload.model_dump())
    except EnrollmentError as error:
        fail(error)


@router.get("/user-courses", response_model=list[UserCourseRead])
def list_user_courses(session: SessionDependency):
    return user_course_service(session).list()


@router.get("/user-courses/{entity_id}", response_model=UserCourseRead)
def get_user_course(entity_id: int, session: SessionDependency):
    try:
        return user_course_service(session).get(entity_id)
    except EnrollmentError as error:
        fail(error)


@router.patch("/user-courses/{entity_id}", response_model=UserCourseRead)
def update_user_course(
    entity_id: int, payload: UserCourseUpdate, session: SessionDependency
):
    try:
        return user_course_service(session).update(
            entity_id, **payload.model_dump(exclude_unset=True)
        )
    except EnrollmentError as error:
        fail(error)


@router.delete("/user-courses/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_course(entity_id: int, session: SessionDependency):
    try:
        user_course_service(session).delete(entity_id)
    except EnrollmentError as error:
        fail(error)
    return Response(status_code=204)


@router.post("/course-offerings", response_model=CourseOfferingRead, status_code=201)
def create_offering(payload: CourseOfferingCreate, session: SessionDependency):
    try:
        return offering_service(session).create(**payload.model_dump())
    except EnrollmentError as error:
        fail(error)


@router.get("/course-offerings", response_model=list[CourseOfferingRead])
def list_offerings(session: SessionDependency):
    return offering_service(session).list()


@router.get("/course-offerings/{entity_id}", response_model=CourseOfferingRead)
def get_offering(entity_id: int, session: SessionDependency):
    try:
        return offering_service(session).get(entity_id)
    except EnrollmentError as error:
        fail(error)


@router.patch("/course-offerings/{entity_id}", response_model=CourseOfferingRead)
def update_offering(
    entity_id: int, payload: CourseOfferingUpdate, session: SessionDependency
):
    try:
        return offering_service(session).update(
            entity_id, **payload.model_dump(exclude_unset=True)
        )
    except EnrollmentError as error:
        fail(error)


@router.delete("/course-offerings/{entity_id}", status_code=204)
def delete_offering(entity_id: int, session: SessionDependency):
    try:
        offering_service(session).delete(entity_id)
    except EnrollmentError as error:
        fail(error)
    return Response(status_code=204)


@router.post(
    "/course-enrollments", response_model=CourseEnrollmentRead, status_code=201
)
def create_enrollment(payload: CourseEnrollmentCreate, session: SessionDependency):
    try:
        return enrollment_service(session).create(**payload.model_dump())
    except EnrollmentError as error:
        fail(error)


@router.get("/course-enrollments", response_model=list[CourseEnrollmentRead])
def list_enrollments(session: SessionDependency):
    return enrollment_service(session).list()


@router.get("/course-enrollments/{entity_id}", response_model=CourseEnrollmentRead)
def get_enrollment(entity_id: int, session: SessionDependency):
    try:
        return enrollment_service(session).get(entity_id)
    except EnrollmentError as error:
        fail(error)


@router.patch("/course-enrollments/{entity_id}", response_model=CourseEnrollmentRead)
def update_enrollment(
    entity_id: int, payload: CourseEnrollmentUpdate, session: SessionDependency
):
    try:
        return enrollment_service(session).update(
            entity_id, **payload.model_dump(exclude_unset=True)
        )
    except EnrollmentError as error:
        fail(error)


@router.delete("/course-enrollments/{entity_id}", status_code=204)
def delete_enrollment(entity_id: int, session: SessionDependency):
    try:
        enrollment_service(session).delete(entity_id)
    except EnrollmentError as error:
        fail(error)
    return Response(status_code=204)
