from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.study import StudySession, StudySessionTopic


class StudyRepositoryConflictError(Exception):
    pass


class StudySessionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, entity_id: int):
        return self.session.get(StudySession, entity_id)

    def list(self, enrollment_id: int | None = None):
        statement = select(StudySession).order_by(StudySession.started_at)
        if enrollment_id is not None:
            statement = statement.where(
                StudySession.course_enrollment_id == enrollment_id
            )
        return list(self.session.scalars(statement))

    def save(self, entity):
        return save(self.session, entity)


class StudySessionTopicRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def find(self, session_id: int, topic_id: int):
        return self.session.scalar(
            select(StudySessionTopic).where(
                StudySessionTopic.study_session_id == session_id,
                StudySessionTopic.topic_id == topic_id,
            )
        )

    def list(self, session_id: int | None = None):
        statement = select(StudySessionTopic).order_by(StudySessionTopic.id)
        if session_id is not None:
            statement = statement.where(
                StudySessionTopic.study_session_id == session_id
            )
        return list(self.session.scalars(statement))

    def latest(self, enrollment_id: int, topic_id: int):
        statement = (
            select(func.max(StudySession.started_at))
            .join(
                StudySessionTopic, StudySessionTopic.study_session_id == StudySession.id
            )
            .where(
                StudySession.course_enrollment_id == enrollment_id,
                StudySessionTopic.topic_id == topic_id,
            )
        )
        return self.session.scalar(statement)

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
        raise StudyRepositoryConflictError from error
