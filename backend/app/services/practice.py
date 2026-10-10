from datetime import UTC

from app.models.practice import PracticeExercise, PracticeSession, PracticeSessionTopic
from app.repositories.practice import PracticeRepositoryConflictError
from app.services.institutional import InstitutionalValidationError, normalize_name


class PracticeNotFoundError(Exception):
    def __init__(self, resource: str) -> None:
        super().__init__(f"{resource} not found")


class PracticeConflictError(Exception):
    pass


class PracticeValidationError(Exception):
    pass


class PracticeSessionService:
    def __init__(self, repository, enrollment_repository):
        self.repository = repository
        self.enrollment_repository = enrollment_repository

    def get(self, entity_id: int):
        entity = self.repository.get(entity_id)
        if entity is None:
            raise PracticeNotFoundError("PracticeSession")
        return entity

    def list(self, enrollment_id: int | None = None):
        return self.repository.list(enrollment_id)

    def create(self, **values):
        if self.enrollment_repository.get(values["course_enrollment_id"]) is None:
            raise PracticeNotFoundError("CourseEnrollment")
        values["occurred_at"] = values["occurred_at"].astimezone(UTC)
        values["mode"] = str(values["mode"])
        try:
            values["source_type"] = normalize_name(
                values["source_type"], "Practice source type"
            )
            values["source_name"] = normalize_name(
                values["source_name"], "Practice source"
            )
        except InstitutionalValidationError as error:
            raise PracticeValidationError(str(error)) from error
        counts = [
            values.get(name)
            for name in (
                "total_exercises",
                "correct_exercises",
                "partial_exercises",
                "incorrect_exercises",
            )
        ]
        if values["mode"] == "QUICK":
            if any(value is None or value < 0 for value in counts):
                raise PracticeValidationError("QUICK mode requires non-negative counts")
            if counts[0] != sum(counts[1:]):
                raise PracticeValidationError(
                    "Practice counts must sum to total_exercises"
                )
        elif any(value is not None for value in counts):
            raise PracticeValidationError(
                "DETAILED mode cannot contain aggregate counts"
            )
        return persisted(self.repository, PracticeSession(**values), "PracticeSession")


class PracticeTopicService:
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

    def create(self, *, practice_session_id: int, topic_id: int):
        practice_session = self.session_repository.get(practice_session_id)
        if practice_session is None:
            raise PracticeNotFoundError("PracticeSession")
        enrollment = self.enrollment_repository.get(
            practice_session.course_enrollment_id
        )
        topic = self.structure_repository.get_topic(topic_id)
        if topic is None:
            raise PracticeNotFoundError("Topic")
        unit = self.structure_repository.get_unit(topic.unit_id)
        if (
            enrollment is None
            or unit is None
            or unit.course_offering_id != enrollment.course_offering_id
        ):
            raise PracticeValidationError("Topic belongs to another CourseOffering")
        if self.repository.find(practice_session_id, topic_id) is not None:
            raise PracticeConflictError("PracticeSessionTopic already exists")
        return persisted(
            self.repository,
            PracticeSessionTopic(
                practice_session_id=practice_session_id, topic_id=topic_id
            ),
            "PracticeSessionTopic",
        )

    def list(self, session_id: int | None = None):
        return self.repository.list(session_id)


class PracticeExerciseService:
    def __init__(self, repository, session_repository):
        self.repository = repository
        self.session_repository = session_repository

    def create(self, *, practice_session_id: int, label: str, result):
        practice_session = self.session_repository.get(practice_session_id)
        if practice_session is None:
            raise PracticeNotFoundError("PracticeSession")
        if practice_session.mode != "DETAILED":
            raise PracticeValidationError(
                "PracticeExercise requires a DETAILED session"
            )
        try:
            label = normalize_name(label, "PracticeExercise")
        except InstitutionalValidationError as error:
            raise PracticeValidationError(str(error)) from error
        entity = PracticeExercise(
            practice_session_id=practice_session_id, label=label, result=str(result)
        )
        return persisted(self.repository, entity, "PracticeExercise")

    def list(self, session_id: int | None = None):
        return self.repository.list(session_id)


def persisted(repository, entity, resource: str):
    try:
        return repository.save(entity)
    except PracticeRepositoryConflictError as error:
        raise PracticeConflictError(f"{resource} persistence conflict") from error
