from datetime import UTC, datetime

from pydantic import ValidationError

from app.models.academic import (
    AcademicSource,
    AcademicSourceStatus,
    AcademicSourceType,
    ExtractionProposal,
    ProposalStatus,
    StructureStatus,
    Subtopic,
    Topic,
    Unit,
)
from app.models.institutional import Course, StudyPlanCourse
from app.repositories.academic import AcademicRepositoryConflictError
from app.schemas.academic import ChangeAction, CourseStructurePayload, StudyPlanPayload
from app.services.institutional import InstitutionalValidationError, normalize_name


class AcademicNotFoundError(Exception):
    def __init__(self, resource: str) -> None:
        super().__init__(f"{resource} not found")


class AcademicConflictError(Exception):
    pass


class AcademicValidationError(Exception):
    pass


class AcademicSourceService:
    def __init__(self, repository, study_plan_repository, offering_repository):
        self.repository = repository
        self.study_plan_repository = study_plan_repository
        self.offering_repository = offering_repository

    def get(self, entity_id: int) -> AcademicSource:
        entity = self.repository.get(entity_id)
        if entity is None:
            raise AcademicNotFoundError("AcademicSource")
        return entity

    def list(self):
        return self.repository.list()

    def create(self, *, type, study_plan_id=None, course_offering_id=None):
        source_type = str(type)
        has_plan = study_plan_id is not None
        has_offering = course_offering_id is not None
        if has_plan == has_offering:
            raise AcademicValidationError("AcademicSource requires exactly one owner")
        if source_type == AcademicSourceType.STUDY_PLAN and not has_plan:
            raise AcademicValidationError(
                "STUDY_PLAN source requires a StudyPlan owner"
            )
        course_types = {
            AcademicSourceType.SYLLABUS,
            AcademicSourceType.SCHEDULE,
            AcademicSourceType.THEORETICAL_MATERIAL,
            AcademicSourceType.PRACTICE_MATERIAL,
        }
        if source_type in course_types and not has_offering:
            raise AcademicValidationError(
                f"{source_type} source requires a CourseOffering owner"
            )
        if has_plan and self.study_plan_repository.get(study_plan_id) is None:
            raise AcademicNotFoundError("StudyPlan")
        if has_offering and self.offering_repository.get(course_offering_id) is None:
            raise AcademicNotFoundError("CourseOffering")
        entity = AcademicSource(
            type=source_type,
            status=AcademicSourceStatus.PENDING,
            study_plan_id=study_plan_id,
            course_offering_id=course_offering_id,
        )
        return self._save(entity)

    def supersede(self, entity_id: int) -> AcademicSource:
        entity = self.get(entity_id)
        if entity.status != AcademicSourceStatus.CONFIRMED:
            raise AcademicConflictError("Only a CONFIRMED source may be superseded")
        entity.status = AcademicSourceStatus.SUPERSEDED
        return self._save(entity)

    def _save(self, entity):
        try:
            return self.repository.save(entity)
        except AcademicRepositoryConflictError as error:
            raise AcademicConflictError(
                "AcademicSource persistence conflict"
            ) from error


class ProposalService:
    def __init__(self, proposal_repository, source_repository, structure_repository):
        self.proposal_repository = proposal_repository
        self.source_repository = source_repository
        self.structure_repository = structure_repository

    def get(self, entity_id: int) -> ExtractionProposal:
        entity = self.proposal_repository.get(entity_id)
        if entity is None:
            raise AcademicNotFoundError("ExtractionProposal")
        return entity

    def list(self):
        return self.proposal_repository.list()

    def create(self, *, academic_source_id: int, extracted_data: dict):
        source = self.source_repository.get(academic_source_id)
        if source is None:
            raise AcademicNotFoundError("AcademicSource")
        if source.status != AcademicSourceStatus.PENDING:
            raise AcademicConflictError("Proposals require a PENDING AcademicSource")
        entity = ExtractionProposal(
            academic_source_id=academic_source_id,
            status=ProposalStatus.PENDING,
            extracted_data=extracted_data,
        )
        return self._save(entity)

    def reject(self, entity_id: int) -> ExtractionProposal:
        try:
            entity = self._pending_for_review(entity_id)
            entity.status = ProposalStatus.REJECTED
            entity.reviewed_at = datetime.now(UTC)
            return self._save(entity)
        except (AcademicNotFoundError, AcademicConflictError):
            self.structure_repository.rollback()
            raise

    def confirm(self, entity_id: int) -> ExtractionProposal:
        try:
            proposal = self._pending_for_review(entity_id)
            source = self.source_repository.get_for_update(proposal.academic_source_id)
            if source is None:
                raise AcademicNotFoundError("AcademicSource")
            if source.status != AcademicSourceStatus.PENDING:
                raise AcademicConflictError("AcademicSource is not PENDING")
            if source.type == AcademicSourceType.OTHER:
                raise AcademicValidationError(
                    "OTHER sources are informational and cannot confirm structure"
                )
            if source.course_offering_id is not None:
                payload = CourseStructurePayload.model_validate(proposal.extracted_data)
                self._apply(payload, source.course_offering_id, proposal.id)
            elif (
                source.type == AcademicSourceType.STUDY_PLAN
                and source.study_plan_id is not None
                and source.course_offering_id is None
            ):
                payload = StudyPlanPayload.model_validate(proposal.extracted_data)
                self._apply_study_plan(payload, source.study_plan_id)
            else:
                raise AcademicValidationError(
                    "StudyPlan-owned proposal confirmation payload is not defined"
                )
            proposal.status = ProposalStatus.CONFIRMED
            proposal.reviewed_at = datetime.now(UTC)
            source.status = AcademicSourceStatus.CONFIRMED
            self.structure_repository.add(proposal)
            self.structure_repository.add(source)
            self.structure_repository.commit()
        except ValidationError as error:
            self.structure_repository.rollback()
            raise AcademicValidationError(
                "Invalid academic proposal payload"
            ) from error
        except (AcademicNotFoundError, AcademicValidationError, AcademicConflictError):
            self.structure_repository.rollback()
            raise
        except AcademicRepositoryConflictError as error:
            self.structure_repository.rollback()
            raise AcademicConflictError("Proposal confirmation conflict") from error
        return proposal

    def _pending_for_review(self, entity_id: int) -> ExtractionProposal:
        entity = self.proposal_repository.get_for_update(entity_id)
        if entity is None:
            raise AcademicNotFoundError("ExtractionProposal")
        if entity.status != ProposalStatus.PENDING:
            raise AcademicConflictError("Only a PENDING proposal may be reviewed")
        return entity

    def _save(self, entity):
        try:
            return self.proposal_repository.save(entity)
        except AcademicRepositoryConflictError as error:
            raise AcademicConflictError(
                "ExtractionProposal persistence conflict"
            ) from error

    def _apply(self, payload, offering_id: int, proposal_id: int) -> None:
        seen: set[tuple[str, int]] = set()
        for change in payload.units:
            unit = self._unit(change, offering_id, proposal_id, seen)
            if change.action == ChangeAction.REMOVE:
                continue
            for topic_change in change.topics:
                topic = self._topic(topic_change, unit, offering_id, proposal_id, seen)
                if topic_change.action == ChangeAction.REMOVE:
                    continue
                for subtopic_change in topic_change.subtopics:
                    self._subtopic(
                        subtopic_change, topic, offering_id, proposal_id, seen
                    )

    def _apply_study_plan(self, payload: StudyPlanPayload, study_plan_id: int) -> None:
        seen: set[int] = set()
        for change in payload.courses:
            if change.study_plan_course_id is not None:
                if change.study_plan_course_id in seen:
                    raise AcademicValidationError(
                        "StudyPlanCourse id appears more than once"
                    )
                seen.add(change.study_plan_course_id)
            if change.action == ChangeAction.CREATE:
                self._create_study_plan_course(change, study_plan_id)
            elif change.action == ChangeAction.UPDATE:
                self._update_study_plan_course(change, study_plan_id)
            else:
                self._remove_study_plan_course(change, study_plan_id)

    def _create_study_plan_course(self, change, study_plan_id: int) -> None:
        if change.course_id is not None:
            course = self.structure_repository.get_course(change.course_id)
            if course is None:
                raise AcademicNotFoundError("Course")
        else:
            course_name = normalized(change.name, "Course")
            if self.structure_repository.find_course_by_name(course_name) is not None:
                raise AcademicConflictError(
                    "Course already exists; reference it by course_id"
                )
            course = Course(name=course_name, code=change.code)
            self.structure_repository.add(course)
        if (
            self.structure_repository.find_study_plan_course(study_plan_id, course.id)
            is not None
        ):
            raise AcademicConflictError("Course already belongs to StudyPlan")
        self.structure_repository.add(
            StudyPlanCourse(study_plan_id=study_plan_id, course_id=course.id)
        )

    def _update_study_plan_course(self, change, study_plan_id: int) -> None:
        relation = self._owned_study_plan_course(
            change.study_plan_course_id, study_plan_id
        )
        course = self.structure_repository.get_course(change.course_id)
        if course is None:
            raise AcademicNotFoundError("Course")
        if (
            self.structure_repository.find_study_plan_course(
                study_plan_id, course.id, exclude_id=relation.id
            )
            is not None
        ):
            raise AcademicConflictError("Course already belongs to StudyPlan")
        relation.course_id = course.id
        self.structure_repository.add(relation)

    def _remove_study_plan_course(self, change, study_plan_id: int) -> None:
        relation = self._owned_study_plan_course(
            change.study_plan_course_id, study_plan_id
        )
        try:
            self.structure_repository.delete_study_plan_course(relation)
        except AcademicRepositoryConflictError as error:
            raise AcademicConflictError(
                "StudyPlanCourse is referenced and cannot be removed"
            ) from error

    def _owned_study_plan_course(
        self, study_plan_course_id: int, study_plan_id: int
    ) -> StudyPlanCourse:
        relation = self.structure_repository.get_study_plan_course(study_plan_course_id)
        if relation is None:
            raise AcademicNotFoundError("StudyPlanCourse")
        if relation.study_plan_id != study_plan_id:
            raise AcademicValidationError(
                "StudyPlanCourse belongs to another StudyPlan"
            )
        return relation

    def _unit(self, change, offering_id, proposal_id, seen) -> Unit:
        unit = (
            None if change.id is None else self.structure_repository.get_unit(change.id)
        )
        self._unique_reference("Unit", change.id, seen)
        if change.action != ChangeAction.CREATE:
            if unit is None:
                raise AcademicNotFoundError("Unit")
            if unit.course_offering_id != offering_id:
                raise AcademicValidationError("Unit belongs to another CourseOffering")
        if change.action == ChangeAction.CREATE:
            unit = Unit(course_offering_id=offering_id, status=StructureStatus.ACTIVE)
        if change.action == ChangeAction.REMOVE:
            unit.status = StructureStatus.REMOVED
        else:
            unit.name = normalized(change.name, "Unit")
            unit.description = change.description
            unit.position = change.position
            unit.status = StructureStatus.ACTIVE
        unit.confirmed_from_proposal_id = proposal_id
        self.structure_repository.add(unit)
        return unit

    def _topic(self, change, unit, offering_id, proposal_id, seen) -> Topic:
        topic = (
            None
            if change.id is None
            else self.structure_repository.get_topic(change.id)
        )
        self._unique_reference("Topic", change.id, seen)
        if change.action != ChangeAction.CREATE:
            if topic is None:
                raise AcademicNotFoundError("Topic")
            owner = self.structure_repository.get_unit(topic.unit_id)
            if (
                owner is None
                or owner.course_offering_id != offering_id
                or topic.unit_id != unit.id
            ):
                raise AcademicValidationError(
                    "Topic does not belong to the proposed Unit"
                )
        if change.action == ChangeAction.CREATE:
            topic = Topic(unit_id=unit.id, status=StructureStatus.ACTIVE)
        if change.action == ChangeAction.REMOVE:
            topic.status = StructureStatus.REMOVED
        else:
            topic.name = normalized(change.name, "Topic")
            topic.position = change.position
            topic.status = StructureStatus.ACTIVE
        topic.confirmed_from_proposal_id = proposal_id
        self.structure_repository.add(topic)
        return topic

    def _subtopic(self, change, topic, offering_id, proposal_id, seen) -> None:
        entity = (
            None
            if change.id is None
            else self.structure_repository.get_subtopic(change.id)
        )
        self._unique_reference("Subtopic", change.id, seen)
        if change.action != ChangeAction.CREATE:
            if entity is None:
                raise AcademicNotFoundError("Subtopic")
            owner_topic = self.structure_repository.get_topic(entity.topic_id)
            owner_unit = (
                None
                if owner_topic is None
                else self.structure_repository.get_unit(owner_topic.unit_id)
            )
            if (
                owner_unit is None
                or owner_unit.course_offering_id != offering_id
                or entity.topic_id != topic.id
            ):
                raise AcademicValidationError(
                    "Subtopic does not belong to the proposed Topic"
                )
        if change.action == ChangeAction.REMOVE:
            self.structure_repository.delete_subtopic(entity)
            return
        if change.action == ChangeAction.CREATE:
            entity = Subtopic(topic_id=topic.id)
        entity.name = normalized(change.name, "Subtopic")
        entity.position = change.position
        entity.confirmed_from_proposal_id = proposal_id
        self.structure_repository.add(entity)

    @staticmethod
    def _unique_reference(resource: str, entity_id: int | None, seen: set) -> None:
        if entity_id is None:
            return
        key = (resource, entity_id)
        if key in seen:
            raise AcademicValidationError(f"{resource} id appears more than once")
        seen.add(key)


class AcademicStructureService:
    def __init__(self, repository, offering_repository):
        self.repository = repository
        self.offering_repository = offering_repository

    def _ensure_offering(self, offering_id: int) -> None:
        if self.offering_repository.get(offering_id) is None:
            raise AcademicNotFoundError("CourseOffering")

    def list_units(self, offering_id: int):
        self._ensure_offering(offering_id)
        return self.repository.list_units(offering_id)

    def list_topics(self, offering_id: int):
        self._ensure_offering(offering_id)
        return self.repository.list_topics(offering_id)

    def list_subtopics(self, offering_id: int):
        self._ensure_offering(offering_id)
        return self.repository.list_subtopics(offering_id)


def normalized(value: str | None, resource: str) -> str:
    try:
        return normalize_name(value or "", resource)
    except InstitutionalValidationError as error:
        raise AcademicValidationError(str(error)) from error
