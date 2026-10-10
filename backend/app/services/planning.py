from app.models.planning import Assessment, AssessmentTopic, CourseScheduleItem
from app.repositories.planning import PlanningRepositoryConflictError
from app.services.institutional import InstitutionalValidationError, normalize_name


class PlanningNotFoundError(Exception):
    def __init__(self, resource: str) -> None:
        super().__init__(f"{resource} not found")


class PlanningConflictError(Exception):
    pass


class PlanningValidationError(Exception):
    pass


class ScheduleService:
    def __init__(self, repository, offering_repository, structure_repository):
        self.repository = repository
        self.offering_repository = offering_repository
        self.structure_repository = structure_repository

    def get(self, entity_id: int):
        entity = self.repository.get(entity_id)
        if entity is None:
            raise PlanningNotFoundError("CourseScheduleItem")
        return entity

    def list(self):
        return self.repository.list()

    def create(self, **values):
        offering_id = values["course_offering_id"]
        if self.offering_repository.get(offering_id) is None:
            raise PlanningNotFoundError("CourseOffering")
        unit_id, topic_id = values.get("unit_id"), values.get("topic_id")
        if (unit_id is None) == (topic_id is None):
            raise PlanningValidationError("Exactly one schedule target is required")
        if unit_id is not None:
            unit = self.structure_repository.get_unit(unit_id)
            if unit is None:
                raise PlanningNotFoundError("Unit")
            if unit.course_offering_id != offering_id:
                raise PlanningValidationError("Unit belongs to another CourseOffering")
        if topic_id is not None:
            topic = self.structure_repository.get_topic(topic_id)
            if topic is None:
                raise PlanningNotFoundError("Topic")
            unit = self.structure_repository.get_unit(topic.unit_id)
            if unit is None or unit.course_offering_id != offering_id:
                raise PlanningValidationError("Topic belongs to another CourseOffering")
        return persisted(
            self.repository, CourseScheduleItem(**values), "CourseScheduleItem"
        )


class AssessmentService:
    def __init__(self, repository, offering_repository):
        self.repository = repository
        self.offering_repository = offering_repository

    def get(self, entity_id: int):
        entity = self.repository.get(entity_id)
        if entity is None:
            raise PlanningNotFoundError("Assessment")
        return entity

    def list(self):
        return self.repository.list()

    def create(self, **values):
        if self.offering_repository.get(values["course_offering_id"]) is None:
            raise PlanningNotFoundError("CourseOffering")
        values["type"] = str(values["type"])
        try:
            values["name"] = normalize_name(values["name"], "Assessment")
        except InstitutionalValidationError as error:
            raise PlanningValidationError(str(error)) from error
        return persisted(self.repository, Assessment(**values), "Assessment")


class AssessmentTopicService:
    def __init__(self, repository, assessment_repository, structure_repository):
        self.repository = repository
        self.assessment_repository = assessment_repository
        self.structure_repository = structure_repository

    def create(self, *, assessment_id: int, topic_id: int):
        assessment = self.assessment_repository.get(assessment_id)
        if assessment is None:
            raise PlanningNotFoundError("Assessment")
        topic = self.structure_repository.get_topic(topic_id)
        if topic is None:
            raise PlanningNotFoundError("Topic")
        unit = self.structure_repository.get_unit(topic.unit_id)
        if unit is None or unit.course_offering_id != assessment.course_offering_id:
            raise PlanningValidationError("Topic belongs to another CourseOffering")
        if self.repository.find(assessment_id, topic_id) is not None:
            raise PlanningConflictError("AssessmentTopic already exists")
        return persisted(
            self.repository,
            AssessmentTopic(assessment_id=assessment_id, topic_id=topic_id),
            "AssessmentTopic",
        )

    def list(self, assessment_id: int | None = None):
        return self.repository.list(assessment_id)


class AssessmentPreparationService:
    def __init__(
        self,
        assessment_repository,
        association_repository,
        structure_repository,
        enrollment_repository,
        tracking_repository,
    ):
        self.assessment_repository = assessment_repository
        self.association_repository = association_repository
        self.structure_repository = structure_repository
        self.enrollment_repository = enrollment_repository
        self.tracking_repository = tracking_repository

    def calculate(self, enrollment_id: int, assessment_id: int) -> dict:
        enrollment = self.enrollment_repository.get(enrollment_id)
        if enrollment is None:
            raise PlanningNotFoundError("CourseEnrollment")
        assessment = self.assessment_repository.get(assessment_id)
        if assessment is None:
            raise PlanningNotFoundError("Assessment")
        if enrollment.course_offering_id != assessment.course_offering_id:
            raise PlanningValidationError(
                "Assessment belongs to another CourseOffering"
            )
        topic_ids = []
        for relation in self.association_repository.list(assessment_id):
            topic = self.structure_repository.get_topic(relation.topic_id)
            unit = (
                None
                if topic is None
                else self.structure_repository.get_unit(topic.unit_id)
            )
            if (
                topic is not None
                and unit is not None
                and topic.status == "ACTIVE"
                and unit.status == "ACTIVE"
            ):
                topic_ids.append(topic.id)
        states = {
            state.topic_id: state
            for state in self.tracking_repository.list(enrollment_id)
        }
        studied = sum(
            topic_id in states and states[topic_id].student_status == "STUDIED"
            for topic_id in topic_ids
        )
        return {
            "assessment_id": assessment_id,
            "active_topic_count": len(topic_ids),
            "studied_topic_count": studied,
            "preparation_coverage": None if not topic_ids else studied / len(topic_ids),
        }


def persisted(repository, entity, resource: str):
    try:
        return repository.save(entity)
    except PlanningRepositoryConflictError as error:
        raise PlanningConflictError(f"{resource} persistence conflict") from error
