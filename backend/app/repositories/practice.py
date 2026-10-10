from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.practice import PracticeExercise, PracticeSession, PracticeSessionTopic


class PracticeRepositoryConflictError(Exception):
    pass


class PracticeSessionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, entity_id: int):
        return self.session.get(PracticeSession, entity_id)

    def list(self, enrollment_id: int | None = None):
        statement = select(PracticeSession).order_by(PracticeSession.occurred_at)
        if enrollment_id is not None:
            statement = statement.where(
                PracticeSession.course_enrollment_id == enrollment_id
            )
        return list(self.session.scalars(statement))

    def save(self, entity):
        return save(self.session, entity)


class PracticeSessionTopicRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def find(self, session_id: int, topic_id: int):
        return self.session.scalar(
            select(PracticeSessionTopic).where(
                PracticeSessionTopic.practice_session_id == session_id,
                PracticeSessionTopic.topic_id == topic_id,
            )
        )

    def list(self, session_id: int | None = None):
        statement = select(PracticeSessionTopic).order_by(PracticeSessionTopic.id)
        if session_id is not None:
            statement = statement.where(
                PracticeSessionTopic.practice_session_id == session_id
            )
        return list(self.session.scalars(statement))

    def save(self, entity):
        return save(self.session, entity)


class PracticeExerciseRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, session_id: int | None = None):
        statement = select(PracticeExercise).order_by(PracticeExercise.id)
        if session_id is not None:
            statement = statement.where(
                PracticeExercise.practice_session_id == session_id
            )
        return list(self.session.scalars(statement))

    def save(self, entity):
        return save(self.session, entity)


def save(session: Session, entity):
    try:
        session.add(entity)
        session.commit()
        session.refresh(entity)
        return entity
    except IntegrityError as error:
        session.rollback()
        raise PracticeRepositoryConflictError from error
