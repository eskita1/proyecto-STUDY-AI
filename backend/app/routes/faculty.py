from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.repositories.faculty import FacultyRepository
from app.repositories.university import UniversityRepository
from app.schemas.faculty import FacultyCreate, FacultyRead, FacultyUpdate
from app.services.faculty import (
    FacultyAlreadyExistsError,
    FacultyConflictError,
    FacultyNotFoundError,
    FacultyService,
    FacultyUniversityNotFoundError,
    FacultyValidationError,
)

router = APIRouter(prefix="/faculties", tags=["faculties"])


def get_faculty_service(
    session: Annotated[Session, Depends(get_db)],
) -> FacultyService:
    return FacultyService(
        FacultyRepository(session),
        UniversityRepository(session),
    )


FacultyServiceDependency = Annotated[
    FacultyService,
    Depends(get_faculty_service),
]


def _translate_service_error(error: Exception) -> None:
    if isinstance(error, FacultyNotFoundError):
        raise HTTPException(status_code=404, detail="Faculty not found") from error
    if isinstance(error, FacultyUniversityNotFoundError):
        raise HTTPException(status_code=404, detail="University not found") from error
    if isinstance(error, FacultyAlreadyExistsError):
        raise HTTPException(
            status_code=409,
            detail="Faculty already exists in this University",
        ) from error
    if isinstance(error, FacultyConflictError):
        raise HTTPException(
            status_code=409,
            detail="Faculty is referenced by other records",
        ) from error
    if isinstance(error, FacultyValidationError):
        raise HTTPException(status_code=422, detail=str(error)) from error
    raise error


@router.post("", response_model=FacultyRead, status_code=status.HTTP_201_CREATED)
def create_faculty(
    payload: FacultyCreate,
    service: FacultyServiceDependency,
) -> FacultyRead:
    try:
        return FacultyRead.model_validate(service.create(**payload.model_dump()))
    except (
        FacultyAlreadyExistsError,
        FacultyUniversityNotFoundError,
        FacultyValidationError,
    ) as error:
        _translate_service_error(error)


@router.get("", response_model=list[FacultyRead])
def list_faculties(service: FacultyServiceDependency) -> list[FacultyRead]:
    return [FacultyRead.model_validate(item) for item in service.list()]


@router.get("/{faculty_id}", response_model=FacultyRead)
def get_faculty(
    faculty_id: int,
    service: FacultyServiceDependency,
) -> FacultyRead:
    try:
        return FacultyRead.model_validate(service.get(faculty_id))
    except FacultyNotFoundError as error:
        _translate_service_error(error)


@router.patch("/{faculty_id}", response_model=FacultyRead)
def update_faculty(
    faculty_id: int,
    payload: FacultyUpdate,
    service: FacultyServiceDependency,
) -> FacultyRead:
    try:
        faculty = service.update(
            faculty_id,
            **payload.model_dump(exclude_unset=True),
        )
        return FacultyRead.model_validate(faculty)
    except (
        FacultyAlreadyExistsError,
        FacultyNotFoundError,
        FacultyUniversityNotFoundError,
        FacultyValidationError,
    ) as error:
        _translate_service_error(error)


@router.delete("/{faculty_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_faculty(
    faculty_id: int,
    service: FacultyServiceDependency,
) -> Response:
    try:
        service.delete(faculty_id)
    except (FacultyConflictError, FacultyNotFoundError) as error:
        _translate_service_error(error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
