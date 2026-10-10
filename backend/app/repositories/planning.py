from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.planning import Assessment, AssessmentTopic, CourseScheduleItem


class PlanningRepositoryConflictError(Exception):
    pass


class CourseScheduleItemRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, entity_id: int):
        return self.session.get(CourseScheduleItem, entity_id)

    def list(self):
        return list(
            self.session.scalars(
                select(CourseScheduleItem).order_by(
                    CourseScheduleItem.scheduled_date, CourseScheduleItem.position
                )
            )
        )

    def save(self, entity):
        return save(self.session, entity)


class AssessmentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, entity_id: int):
        return self.session.get(Assessment, entity_id)

    def list(self):
        return list(
            self.session.scalars(
                select(Assessment).order_by(Assessment.date, Assessment.id)
            )
        )

    def save(self, entity):
        return save(self.session, entity)


class AssessmentTopicRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, entity_id: int):
        return self.session.get(AssessmentTopic, entity_id)

    def list(self, assessment_id: int | None = None):
        statement = select(AssessmentTopic).order_by(AssessmentTopic.id)
        if assessment_id is not None:
            statement = statement.where(AssessmentTopic.assessment_id == assessment_id)
        return list(self.session.scalars(statement))

    def find(self, assessment_id: int, topic_id: int):
        return self.session.scalar(
            select(AssessmentTopic).where(
                AssessmentTopic.assessment_id == assessment_id,
                AssessmentTopic.topic_id == topic_id,
            )
        )

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
        raise PlanningRepositoryConflictError from error
