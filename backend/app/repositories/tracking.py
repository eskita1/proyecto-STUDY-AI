from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.academic import Topic, Unit
from app.models.tracking import EnrollmentTopic


class TrackingRepositoryConflictError(Exception):
    pass


class EnrollmentTopicRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, entity_id: int) -> EnrollmentTopic | None:
        return self.session.get(EnrollmentTopic, entity_id)

    def list(self, course_enrollment_id: int | None = None) -> list[EnrollmentTopic]:
        statement = select(EnrollmentTopic).order_by(EnrollmentTopic.id)
        if course_enrollment_id is not None:
            statement = statement.where(
                EnrollmentTopic.course_enrollment_id == course_enrollment_id
            )
        return list(self.session.scalars(statement))

    def find(self, course_enrollment_id: int, topic_id: int) -> EnrollmentTopic | None:
        return self.session.scalar(
            select(EnrollmentTopic).where(
                EnrollmentTopic.course_enrollment_id == course_enrollment_id,
                EnrollmentTopic.topic_id == topic_id,
            )
        )

    def save(self, entity: EnrollmentTopic) -> EnrollmentTopic:
        try:
            self.session.add(entity)
            self.session.commit()
            self.session.refresh(entity)
            return entity
        except IntegrityError as error:
            self.session.rollback()
            raise TrackingRepositoryConflictError from error

    def active_topics(self, course_offering_id: int) -> list[Topic]:
        statement = (
            select(Topic)
            .join(Unit)
            .where(
                Unit.course_offering_id == course_offering_id,
                Unit.status == "ACTIVE",
                Topic.status == "ACTIVE",
            )
            .order_by(Unit.position, Topic.position)
        )
        return list(self.session.scalars(statement))
