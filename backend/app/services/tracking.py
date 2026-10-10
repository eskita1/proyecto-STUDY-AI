from app.models.tracking import EnrollmentTopic
from app.repositories.tracking import TrackingRepositoryConflictError


class TrackingNotFoundError(Exception):
    def __init__(self, resource: str) -> None:
        super().__init__(f"{resource} not found")


class TrackingConflictError(Exception):
    pass


class TrackingValidationError(Exception):
    pass


class EnrollmentTopicService:
    def __init__(
        self, repository, enrollment_repository, topic_repository, unit_repository
    ):
        self.repository = repository
        self.enrollment_repository = enrollment_repository
        self.topic_repository = topic_repository
        self.unit_repository = unit_repository

    def get(self, entity_id: int) -> EnrollmentTopic:
        entity = self.repository.get(entity_id)
        if entity is None:
            raise TrackingNotFoundError("EnrollmentTopic")
        return entity

    def list(self, course_enrollment_id: int | None = None):
        if (
            course_enrollment_id is not None
            and self.enrollment_repository.get(course_enrollment_id) is None
        ):
            raise TrackingNotFoundError("CourseEnrollment")
        return self.repository.list(course_enrollment_id)

    def create(self, **values):
        enrollment = self.enrollment_repository.get(values["course_enrollment_id"])
        if enrollment is None:
            raise TrackingNotFoundError("CourseEnrollment")
        topic = self.topic_repository.get_topic(values["topic_id"])
        if topic is None:
            raise TrackingNotFoundError("Topic")
        unit = self.unit_repository.get_unit(topic.unit_id)
        if unit is None or unit.course_offering_id != enrollment.course_offering_id:
            raise TrackingValidationError(
                "Topic must belong to the CourseEnrollment CourseOffering"
            )
        if self.repository.find(enrollment.id, topic.id) is not None:
            raise TrackingConflictError("EnrollmentTopic already exists")
        entity = EnrollmentTopic(
            **{
                key: str(value) if key.endswith("status") else value
                for key, value in values.items()
            }
        )
        return self._save(entity)

    def update(self, entity_id: int, **values):
        entity = self.get(entity_id)
        for field, value in values.items():
            setattr(entity, field, str(value) if field.endswith("status") else value)
        return self._save(entity)

    def _save(self, entity):
        try:
            return self.repository.save(entity)
        except TrackingRepositoryConflictError as error:
            raise TrackingConflictError(
                "EnrollmentTopic persistence conflict"
            ) from error


class ProgressService:
    def __init__(self, tracking_repository, enrollment_repository):
        self.tracking_repository = tracking_repository
        self.enrollment_repository = enrollment_repository

    def calculate(self, course_enrollment_id: int) -> dict:
        enrollment = self.enrollment_repository.get(course_enrollment_id)
        if enrollment is None:
            raise TrackingNotFoundError("CourseEnrollment")
        topics = self.tracking_repository.active_topics(enrollment.course_offering_id)
        states = {
            state.topic_id: state
            for state in self.tracking_repository.list(course_enrollment_id)
        }
        active_ids = [topic.id for topic in topics]
        seen_ids = [
            topic_id
            for topic_id in active_ids
            if topic_id in states and states[topic_id].course_progress_status == "SEEN"
        ]
        studied_ids = [
            topic_id
            for topic_id in active_ids
            if topic_id in states and states[topic_id].student_status == "STUDIED"
        ]
        both_ids = list(set(seen_ids) & set(studied_ids))
        gap_ids = [topic_id for topic_id in seen_ids if topic_id not in studied_ids]
        active_count = len(active_ids)
        return {
            "active_topic_count": active_count,
            "seen_topic_count": len(seen_ids),
            "studied_topic_count": len(studied_ids),
            "seen_and_studied_topic_count": len(both_ids),
            "course_progress": ratio(len(seen_ids), active_count),
            "student_progress": ratio(len(studied_ids), active_count),
            "catch_up_progress": ratio(len(both_ids), len(seen_ids)),
            "academic_gap_topic_ids": gap_ids,
        }


def ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator
