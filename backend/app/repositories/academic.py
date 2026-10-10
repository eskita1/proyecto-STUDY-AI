from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.academic import (
    AcademicSource,
    ExtractionProposal,
    Subtopic,
    Topic,
    Unit,
)


class AcademicRepositoryConflictError(Exception):
    pass


class AcademicSourceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, entity_id: int) -> AcademicSource | None:
        return self.session.get(AcademicSource, entity_id)

    def list(self) -> list[AcademicSource]:
        return list(
            self.session.scalars(select(AcademicSource).order_by(AcademicSource.id))
        )

    def save(self, entity: AcademicSource) -> AcademicSource:
        return save(self.session, entity)


class ExtractionProposalRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, entity_id: int) -> ExtractionProposal | None:
        return self.session.get(ExtractionProposal, entity_id)

    def list(self) -> list[ExtractionProposal]:
        return list(
            self.session.scalars(
                select(ExtractionProposal).order_by(ExtractionProposal.id)
            )
        )

    def save(self, entity: ExtractionProposal) -> ExtractionProposal:
        return save(self.session, entity)


class AcademicStructureRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_unit(self, entity_id: int) -> Unit | None:
        return self.session.get(Unit, entity_id)

    def get_topic(self, entity_id: int) -> Topic | None:
        return self.session.get(Topic, entity_id)

    def get_subtopic(self, entity_id: int) -> Subtopic | None:
        return self.session.get(Subtopic, entity_id)

    def list_units(self, course_offering_id: int) -> list[Unit]:
        statement = (
            select(Unit)
            .where(Unit.course_offering_id == course_offering_id)
            .order_by(Unit.position)
        )
        return list(self.session.scalars(statement))

    def list_topics(self, course_offering_id: int) -> list[Topic]:
        statement = (
            select(Topic)
            .join(Unit)
            .where(Unit.course_offering_id == course_offering_id)
            .order_by(Unit.position, Topic.position)
        )
        return list(self.session.scalars(statement))

    def list_subtopics(self, course_offering_id: int) -> list[Subtopic]:
        statement = (
            select(Subtopic)
            .join(Topic)
            .join(Unit)
            .where(Unit.course_offering_id == course_offering_id)
            .order_by(Unit.position, Topic.position, Subtopic.position)
        )
        return list(self.session.scalars(statement))

    def add(self, entity) -> None:
        try:
            self.session.add(entity)
            self.session.flush()
        except IntegrityError as error:
            self.session.rollback()
            raise AcademicRepositoryConflictError from error

    def delete_subtopic(self, entity: Subtopic) -> None:
        try:
            self.session.delete(entity)
            self.session.flush()
        except IntegrityError as error:
            self.session.rollback()
            raise AcademicRepositoryConflictError from error

    def commit(self) -> None:
        try:
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            raise AcademicRepositoryConflictError from error

    def rollback(self) -> None:
        self.session.rollback()


def save(session: Session, entity):
    try:
        session.add(entity)
        session.commit()
        session.refresh(entity)
        return entity
    except IntegrityError as error:
        session.rollback()
        raise AcademicRepositoryConflictError from error
