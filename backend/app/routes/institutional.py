from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.repositories.faculty import FacultyRepository
from app.repositories.institutional import (
    CareerRepository,
    CourseRepository,
    StudyPlanCourseRepository,
    StudyPlanRepository,
    UserCareerRepository,
    UserRepository,
)
from app.schemas.institutional import (
    CareerCreate,
    CareerRead,
    CareerUpdate,
    CourseCreate,
    CourseRead,
    CourseUpdate,
    StudyPlanCourseCreate,
    StudyPlanCourseRead,
    StudyPlanCourseUpdate,
    StudyPlanCreate,
    StudyPlanRead,
    StudyPlanUpdate,
    UserCareerCreate,
    UserCareerRead,
    UserCareerUpdate,
    UserCreate,
    UserRead,
)
from app.services.institutional import (
    CareerService,
    CourseService,
    InstitutionalConflictError,
    InstitutionalNotFoundError,
    InstitutionalValidationError,
    StudyPlanCourseService,
    StudyPlanService,
    UserCareerService,
    UserService,
)

router = APIRouter()
SessionDependency = Annotated[Session, Depends(get_db)]


def translate_error(error: Exception) -> None:
    if isinstance(error, InstitutionalNotFoundError):
        raise HTTPException(status_code=404, detail=str(error)) from error
    if isinstance(error, InstitutionalConflictError):
        raise HTTPException(status_code=409, detail=str(error)) from error
    if isinstance(error, InstitutionalValidationError):
        raise HTTPException(status_code=422, detail=str(error)) from error
    raise error


def career_service(session: Session) -> CareerService:
    return CareerService(CareerRepository(session), FacultyRepository(session))


def study_plan_service(session: Session) -> StudyPlanService:
    return StudyPlanService(StudyPlanRepository(session), CareerRepository(session))


def study_plan_course_service(session: Session) -> StudyPlanCourseService:
    return StudyPlanCourseService(
        StudyPlanCourseRepository(session),
        StudyPlanRepository(session),
        CourseRepository(session),
    )


def user_career_service(session: Session) -> UserCareerService:
    return UserCareerService(
        UserCareerRepository(session),
        UserRepository(session),
        CareerRepository(session),
        StudyPlanRepository(session),
    )


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, session: SessionDependency) -> UserRead:
    return UserRead.model_validate(UserService(UserRepository(session)).create())


@router.get("/users", response_model=list[UserRead])
def list_users(session: SessionDependency) -> list[UserRead]:
    return [
        UserRead.model_validate(item)
        for item in UserService(UserRepository(session)).list()
    ]


@router.get("/users/{entity_id}", response_model=UserRead)
def get_user(entity_id: int, session: SessionDependency) -> UserRead:
    try:
        return UserRead.model_validate(
            UserService(UserRepository(session)).get(entity_id)
        )
    except InstitutionalNotFoundError as error:
        translate_error(error)


@router.delete("/users/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(entity_id: int, session: SessionDependency) -> Response:
    try:
        UserService(UserRepository(session)).delete(entity_id)
    except (InstitutionalConflictError, InstitutionalNotFoundError) as error:
        translate_error(error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/careers", response_model=CareerRead, status_code=status.HTTP_201_CREATED)
def create_career(payload: CareerCreate, session: SessionDependency) -> CareerRead:
    try:
        return CareerRead.model_validate(
            career_service(session).create(**payload.model_dump())
        )
    except (
        InstitutionalConflictError,
        InstitutionalNotFoundError,
        InstitutionalValidationError,
    ) as error:
        translate_error(error)


@router.get("/careers", response_model=list[CareerRead])
def list_careers(session: SessionDependency) -> list[CareerRead]:
    return [CareerRead.model_validate(item) for item in career_service(session).list()]


@router.get("/careers/{entity_id}", response_model=CareerRead)
def get_career(entity_id: int, session: SessionDependency) -> CareerRead:
    try:
        return CareerRead.model_validate(career_service(session).get(entity_id))
    except InstitutionalNotFoundError as error:
        translate_error(error)


@router.patch("/careers/{entity_id}", response_model=CareerRead)
def update_career(
    entity_id: int, payload: CareerUpdate, session: SessionDependency
) -> CareerRead:
    try:
        return CareerRead.model_validate(
            career_service(session).update(
                entity_id, **payload.model_dump(exclude_unset=True)
            )
        )
    except (
        InstitutionalConflictError,
        InstitutionalNotFoundError,
        InstitutionalValidationError,
    ) as error:
        translate_error(error)


@router.delete("/careers/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_career(entity_id: int, session: SessionDependency) -> Response:
    try:
        career_service(session).delete(entity_id)
    except (InstitutionalConflictError, InstitutionalNotFoundError) as error:
        translate_error(error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/study-plans", response_model=StudyPlanRead, status_code=status.HTTP_201_CREATED
)
def create_study_plan(
    payload: StudyPlanCreate, session: SessionDependency
) -> StudyPlanRead:
    try:
        return StudyPlanRead.model_validate(
            study_plan_service(session).create(**payload.model_dump())
        )
    except (
        InstitutionalConflictError,
        InstitutionalNotFoundError,
        InstitutionalValidationError,
    ) as error:
        translate_error(error)


@router.get("/study-plans", response_model=list[StudyPlanRead])
def list_study_plans(session: SessionDependency) -> list[StudyPlanRead]:
    return [
        StudyPlanRead.model_validate(item)
        for item in study_plan_service(session).list()
    ]


@router.get("/study-plans/{entity_id}", response_model=StudyPlanRead)
def get_study_plan(entity_id: int, session: SessionDependency) -> StudyPlanRead:
    try:
        return StudyPlanRead.model_validate(study_plan_service(session).get(entity_id))
    except InstitutionalNotFoundError as error:
        translate_error(error)


@router.patch("/study-plans/{entity_id}", response_model=StudyPlanRead)
def update_study_plan(
    entity_id: int, payload: StudyPlanUpdate, session: SessionDependency
) -> StudyPlanRead:
    try:
        return StudyPlanRead.model_validate(
            study_plan_service(session).update(
                entity_id, **payload.model_dump(exclude_unset=True)
            )
        )
    except (
        InstitutionalConflictError,
        InstitutionalNotFoundError,
        InstitutionalValidationError,
    ) as error:
        translate_error(error)


@router.delete("/study-plans/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_study_plan(entity_id: int, session: SessionDependency) -> Response:
    try:
        study_plan_service(session).delete(entity_id)
    except (InstitutionalConflictError, InstitutionalNotFoundError) as error:
        translate_error(error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/courses", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
def create_course(payload: CourseCreate, session: SessionDependency) -> CourseRead:
    try:
        return CourseRead.model_validate(
            CourseService(CourseRepository(session)).create(**payload.model_dump())
        )
    except (InstitutionalConflictError, InstitutionalValidationError) as error:
        translate_error(error)


@router.get("/courses", response_model=list[CourseRead])
def list_courses(session: SessionDependency) -> list[CourseRead]:
    service = CourseService(CourseRepository(session))
    return [CourseRead.model_validate(item) for item in service.list()]


@router.get("/courses/{entity_id}", response_model=CourseRead)
def get_course(entity_id: int, session: SessionDependency) -> CourseRead:
    try:
        return CourseRead.model_validate(
            CourseService(CourseRepository(session)).get(entity_id)
        )
    except InstitutionalNotFoundError as error:
        translate_error(error)


@router.patch("/courses/{entity_id}", response_model=CourseRead)
def update_course(
    entity_id: int, payload: CourseUpdate, session: SessionDependency
) -> CourseRead:
    values = payload.model_dump(exclude_unset=True)
    try:
        return CourseRead.model_validate(
            CourseService(CourseRepository(session)).update(
                entity_id,
                name=values.get("name"),
                code=values.get("code"),
                code_provided="code" in values,
            )
        )
    except (
        InstitutionalConflictError,
        InstitutionalNotFoundError,
        InstitutionalValidationError,
    ) as error:
        translate_error(error)


@router.delete("/courses/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(entity_id: int, session: SessionDependency) -> Response:
    try:
        CourseService(CourseRepository(session)).delete(entity_id)
    except (InstitutionalConflictError, InstitutionalNotFoundError) as error:
        translate_error(error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/study-plan-courses",
    response_model=StudyPlanCourseRead,
    status_code=status.HTTP_201_CREATED,
)
def create_study_plan_course(
    payload: StudyPlanCourseCreate, session: SessionDependency
) -> StudyPlanCourseRead:
    try:
        return StudyPlanCourseRead.model_validate(
            study_plan_course_service(session).create(**payload.model_dump())
        )
    except (InstitutionalConflictError, InstitutionalNotFoundError) as error:
        translate_error(error)


@router.get("/study-plan-courses", response_model=list[StudyPlanCourseRead])
def list_study_plan_courses(
    session: SessionDependency,
) -> list[StudyPlanCourseRead]:
    return [
        StudyPlanCourseRead.model_validate(item)
        for item in study_plan_course_service(session).list()
    ]


@router.get("/study-plan-courses/{entity_id}", response_model=StudyPlanCourseRead)
def get_study_plan_course(
    entity_id: int, session: SessionDependency
) -> StudyPlanCourseRead:
    try:
        return StudyPlanCourseRead.model_validate(
            study_plan_course_service(session).get(entity_id)
        )
    except InstitutionalNotFoundError as error:
        translate_error(error)


@router.patch("/study-plan-courses/{entity_id}", response_model=StudyPlanCourseRead)
def update_study_plan_course(
    entity_id: int,
    payload: StudyPlanCourseUpdate,
    session: SessionDependency,
) -> StudyPlanCourseRead:
    try:
        return StudyPlanCourseRead.model_validate(
            study_plan_course_service(session).update(
                entity_id, **payload.model_dump(exclude_unset=True)
            )
        )
    except (InstitutionalConflictError, InstitutionalNotFoundError) as error:
        translate_error(error)


@router.delete(
    "/study-plan-courses/{entity_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_study_plan_course(entity_id: int, session: SessionDependency) -> Response:
    try:
        study_plan_course_service(session).delete(entity_id)
    except (InstitutionalConflictError, InstitutionalNotFoundError) as error:
        translate_error(error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/user-careers", response_model=UserCareerRead, status_code=status.HTTP_201_CREATED
)
def create_user_career(
    payload: UserCareerCreate, session: SessionDependency
) -> UserCareerRead:
    try:
        return UserCareerRead.model_validate(
            user_career_service(session).create(**payload.model_dump())
        )
    except (
        InstitutionalConflictError,
        InstitutionalNotFoundError,
        InstitutionalValidationError,
    ) as error:
        translate_error(error)


@router.get("/user-careers", response_model=list[UserCareerRead])
def list_user_careers(session: SessionDependency) -> list[UserCareerRead]:
    return [
        UserCareerRead.model_validate(item)
        for item in user_career_service(session).list()
    ]


@router.get("/user-careers/{entity_id}", response_model=UserCareerRead)
def get_user_career(entity_id: int, session: SessionDependency) -> UserCareerRead:
    try:
        return UserCareerRead.model_validate(
            user_career_service(session).get(entity_id)
        )
    except InstitutionalNotFoundError as error:
        translate_error(error)


@router.patch("/user-careers/{entity_id}", response_model=UserCareerRead)
def update_user_career(
    entity_id: int, payload: UserCareerUpdate, session: SessionDependency
) -> UserCareerRead:
    try:
        return UserCareerRead.model_validate(
            user_career_service(session).update(
                entity_id, **payload.model_dump(exclude_unset=True)
            )
        )
    except (
        InstitutionalConflictError,
        InstitutionalNotFoundError,
        InstitutionalValidationError,
    ) as error:
        translate_error(error)


@router.delete("/user-careers/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_career(entity_id: int, session: SessionDependency) -> Response:
    try:
        user_career_service(session).delete(entity_id)
    except (InstitutionalConflictError, InstitutionalNotFoundError) as error:
        translate_error(error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
