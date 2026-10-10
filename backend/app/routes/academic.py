from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.repositories.academic import (
    AcademicSourceRepository,
    AcademicStructureRepository,
    ExtractionProposalRepository,
)
from app.repositories.enrollment import CourseOfferingRepository
from app.repositories.institutional import StudyPlanRepository
from app.schemas.academic import (
    AcademicSourceCreate,
    AcademicSourceRead,
    ExtractionProposalCreate,
    ExtractionProposalRead,
    SubtopicRead,
    TopicRead,
    UnitRead,
)
from app.services.academic import (
    AcademicConflictError,
    AcademicNotFoundError,
    AcademicSourceService,
    AcademicStructureService,
    AcademicValidationError,
    ProposalService,
)

router = APIRouter()
SessionDependency = Annotated[Session, Depends(get_db)]
AcademicError = (AcademicNotFoundError, AcademicConflictError, AcademicValidationError)


def source_service(session: Session) -> AcademicSourceService:
    return AcademicSourceService(
        AcademicSourceRepository(session),
        StudyPlanRepository(session),
        CourseOfferingRepository(session),
    )


def proposal_service(session: Session) -> ProposalService:
    return ProposalService(
        ExtractionProposalRepository(session),
        AcademicSourceRepository(session),
        AcademicStructureRepository(session),
    )


def structure_service(session: Session) -> AcademicStructureService:
    return AcademicStructureService(
        AcademicStructureRepository(session), CourseOfferingRepository(session)
    )


def fail(error: Exception) -> None:
    if isinstance(error, AcademicNotFoundError):
        raise HTTPException(404, str(error)) from error
    if isinstance(error, AcademicConflictError):
        raise HTTPException(409, str(error)) from error
    if isinstance(error, AcademicValidationError):
        raise HTTPException(422, str(error)) from error
    raise error


@router.post("/academic-sources", response_model=AcademicSourceRead, status_code=201)
def create_source(payload: AcademicSourceCreate, session: SessionDependency):
    try:
        return source_service(session).create(**payload.model_dump())
    except AcademicError as error:
        fail(error)


@router.get("/academic-sources", response_model=list[AcademicSourceRead])
def list_sources(session: SessionDependency):
    return source_service(session).list()


@router.get("/academic-sources/{entity_id}", response_model=AcademicSourceRead)
def get_source(entity_id: int, session: SessionDependency):
    try:
        return source_service(session).get(entity_id)
    except AcademicError as error:
        fail(error)


@router.post(
    "/academic-sources/{entity_id}/supersede", response_model=AcademicSourceRead
)
def supersede_source(entity_id: int, session: SessionDependency):
    try:
        return source_service(session).supersede(entity_id)
    except AcademicError as error:
        fail(error)


@router.post(
    "/extraction-proposals", response_model=ExtractionProposalRead, status_code=201
)
def create_proposal(payload: ExtractionProposalCreate, session: SessionDependency):
    try:
        return proposal_service(session).create(**payload.model_dump())
    except AcademicError as error:
        fail(error)


@router.get("/extraction-proposals", response_model=list[ExtractionProposalRead])
def list_proposals(session: SessionDependency):
    return proposal_service(session).list()


@router.get("/extraction-proposals/{entity_id}", response_model=ExtractionProposalRead)
def get_proposal(entity_id: int, session: SessionDependency):
    try:
        return proposal_service(session).get(entity_id)
    except AcademicError as error:
        fail(error)


@router.post(
    "/extraction-proposals/{entity_id}/confirm", response_model=ExtractionProposalRead
)
def confirm_proposal(entity_id: int, session: SessionDependency):
    try:
        return proposal_service(session).confirm(entity_id)
    except AcademicError as error:
        fail(error)


@router.post(
    "/extraction-proposals/{entity_id}/reject", response_model=ExtractionProposalRead
)
def reject_proposal(entity_id: int, session: SessionDependency):
    try:
        return proposal_service(session).reject(entity_id)
    except AcademicError as error:
        fail(error)


@router.get("/course-offerings/{offering_id}/units", response_model=list[UnitRead])
def list_units(offering_id: int, session: SessionDependency):
    try:
        return structure_service(session).list_units(offering_id)
    except AcademicError as error:
        fail(error)


@router.get("/course-offerings/{offering_id}/topics", response_model=list[TopicRead])
def list_topics(offering_id: int, session: SessionDependency):
    try:
        return structure_service(session).list_topics(offering_id)
    except AcademicError as error:
        fail(error)


@router.get(
    "/course-offerings/{offering_id}/subtopics", response_model=list[SubtopicRead]
)
def list_subtopics(offering_id: int, session: SessionDependency):
    try:
        return structure_service(session).list_subtopics(offering_id)
    except AcademicError as error:
        fail(error)
