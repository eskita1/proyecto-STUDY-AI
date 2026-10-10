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
from app.repositories.academic import AcademicRepositoryConflictError
from app.schemas.academic import ChangeAction, CourseStructurePayload
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
        entity = self._pending(entity_id)
        entity.status = ProposalStatus.REJECTED
        entity.reviewed_at = datetime.now(UTC)
        return self._save(entity)

    def confirm(self, entity_id: int) -> ExtractionProposal:
        proposal = self._pending(entity_id)
        source = self.source_repository.get(proposal.academic_source_id)
        if source is None:
            raise AcademicNotFoundError("AcademicSource")
        if source.status != AcademicSourceStatus.PENDING:
            raise AcademicConflictError("AcademicSource is not PENDING")
        try:
            if source.course_offering_id is not None:
                payload = CourseStructurePayload.model_validate(proposal.extracted_data)
                self._apply(payload, source.course_offering_id, proposal.id)
            elif not proposal.extracted_data:
                raise AcademicValidationError(
                    "StudyPlan proposal extracted_data cannot be empty"
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
                "Invalid course academic structure payload"
            ) from error
        except (AcademicNotFoundError, AcademicValidationError, AcademicConflictError):
            self.structure_repository.rollback()
            raise
        except AcademicRepositoryConflictError as error:
            self.structure_repository.rollback()
            raise AcademicConflictError("Proposal confirmation conflict") from error
        return proposal

    def _pending(self, entity_id: int) -> ExtractionProposal:
        entity = self.get(entity_id)
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
