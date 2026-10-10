from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.repositories.university import UniversityRepository
from app.schemas.university import UniversityCreate, UniversityRead, UniversityUpdate
from app.services.university import (
    UniversityAlreadyExistsError,
    UniversityNotFoundError,
    UniversityService,
    UniversityValidationError,
)

router = APIRouter(prefix="/universities", tags=["universities"])


def get_university_service(
    session: Annotated[Session, Depends(get_db)],
) -> UniversityService:
    return UniversityService(UniversityRepository(session))


UniversityServiceDependency = Annotated[
    UniversityService,
    Depends(get_university_service),
]


def _translate_service_error(error: Exception) -> None:
    if isinstance(error, UniversityNotFoundError):
        raise HTTPException(status_code=404, detail="University not found") from error
    if isinstance(error, UniversityAlreadyExistsError):
        raise HTTPException(
            status_code=409,
            detail="University already exists in this country",
        ) from error
    if isinstance(error, UniversityValidationError):
        raise HTTPException(status_code=422, detail=str(error)) from error
    raise error


@router.post("", response_model=UniversityRead, status_code=status.HTTP_201_CREATED)
def create_university(
    payload: UniversityCreate,
    service: UniversityServiceDependency,
) -> UniversityRead:
    try:
        return UniversityRead.model_validate(service.create(**payload.model_dump()))
    except (
        UniversityAlreadyExistsError,
        UniversityValidationError,
    ) as error:
        _translate_service_error(error)


@router.get("", response_model=list[UniversityRead])
def list_universities(service: UniversityServiceDependency) -> list[UniversityRead]:
    return [UniversityRead.model_validate(item) for item in service.list()]


@router.get("/{university_id}", response_model=UniversityRead)
def get_university(
    university_id: int,
    service: UniversityServiceDependency,
) -> UniversityRead:
    try:
        return UniversityRead.model_validate(service.get(university_id))
    except UniversityNotFoundError as error:
        _translate_service_error(error)


@router.patch("/{university_id}", response_model=UniversityRead)
def update_university(
    university_id: int,
    payload: UniversityUpdate,
    service: UniversityServiceDependency,
) -> UniversityRead:
    try:
        university = service.update(
            university_id,
            **payload.model_dump(exclude_unset=True),
        )
        return UniversityRead.model_validate(university)
    except (
        UniversityAlreadyExistsError,
        UniversityNotFoundError,
        UniversityValidationError,
    ) as error:
        _translate_service_error(error)


@router.delete("/{university_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_university(
    university_id: int,
    service: UniversityServiceDependency,
) -> Response:
    try:
        service.delete(university_id)
    except UniversityNotFoundError as error:
        _translate_service_error(error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
