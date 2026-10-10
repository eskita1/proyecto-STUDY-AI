from datetime import UTC

from app.models.study import StudySession, StudySessionTopic
from app.repositories.study import StudyRepositoryConflictError


class StudyNotFoundError(Exception):
    def __init__(self, resource: str) -> None:
        super().__init__(f"{resource} not found")


class StudyConflictError(Exception):
    pass


class StudyValidationError(Exception):
    pass


class StudySessionService:
    def __init__(self, repository, enrollment_repository):
        self.repository = repository
        self.enrollment_repository = enrollment_repository

    def get(self, entity_id: int):
        entity = self.repository.get(entity_id)
        if entity is None:
            raise StudyNotFoundError("StudySession")
        return entity

    def list(self, enrollment_id: int | None = None):
        return self.repository.list(enrollment_id)

    def create(self, **values):
        if self.enrollment_repository.get(values["course_enrollment_id"]) is None:
            raise StudyNotFoundError("CourseEnrollment")
        values["started_at"] = values["started_at"].astimezone(UTC)
        if values.get("ended_at") is not None:
            values["ended_at"] = values["ended_at"].astimezone(UTC)
            if values["ended_at"] < values["started_at"]:
                raise StudyValidationError("ended_at must be on or after started_at")
        return persisted(self.repository, StudySession(**values), "StudySession")


class StudySessionTopicService:
    def __init__(
        self,
        repository,
        session_repository,
        enrollment_repository,
        structure_repository,
    ):
        self.repository = repository
        self.session_repository = session_repository
        self.enrollment_repository = enrollment_repository
        self.structure_repository = structure_repository

    def create(self, *, study_session_id: int, topic_id: int):
        study_session = self.session_repository.get(study_session_id)
        if study_session is None:
            raise StudyNotFoundError("StudySession")
        enrollment = self.enrollment_repository.get(study_session.course_enrollment_id)
        if enrollment is None:
            raise StudyNotFoundError("CourseEnrollment")
        topic = self.structure_repository.get_topic(topic_id)
        if topic is None:
            raise StudyNotFoundError("Topic")
        unit = self.structure_repository.get_unit(topic.unit_id)
        if unit is None or unit.course_offering_id != enrollment.course_offering_id:
            raise StudyValidationError("Topic belongs to another CourseOffering")
        if self.repository.find(study_session_id, topic_id) is not None:
            raise StudyConflictError("StudySessionTopic already exists")
        return persisted(
            self.repository,
            StudySessionTopic(study_session_id=study_session_id, topic_id=topic_id),
            "StudySessionTopic",
        )

    def list(self, session_id: int | None = None):
        return self.repository.list(session_id)

    def last_studied(self, enrollment_id: int, topic_id: int) -> dict:
        enrollment = self.enrollment_repository.get(enrollment_id)
        if enrollment is None:
            raise StudyNotFoundError("CourseEnrollment")
        topic = self.structure_repository.get_topic(topic_id)
        if topic is None:
            raise StudyNotFoundError("Topic")
        unit = self.structure_repository.get_unit(topic.unit_id)
        if unit is None or unit.course_offering_id != enrollment.course_offering_id:
            raise StudyValidationError("Topic belongs to another CourseOffering")
        return {
            "course_enrollment_id": enrollment_id,
            "topic_id": topic_id,
            "last_studied_at": self.repository.latest(enrollment_id, topic_id),
        }


def persisted(repository, entity, resource: str):
    try:
        return repository.save(entity)
    except StudyRepositoryConflictError as error:
        raise StudyConflictError(f"{resource} persistence conflict") from error
