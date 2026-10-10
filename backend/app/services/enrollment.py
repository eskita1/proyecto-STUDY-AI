from app.models.enrollment import (
    CourseEnrollment,
    CourseOffering,
    EnrollmentStatus,
    UserCourse,
)
from app.repositories.enrollment import EnrollmentRepositoryConflictError
from app.services.institutional import InstitutionalValidationError, normalize_name


class EnrollmentNotFoundError(Exception):
    def __init__(self, resource: str) -> None:
        super().__init__(f"{resource} not found")


class EnrollmentConflictError(Exception):
    pass


class EnrollmentValidationError(Exception):
    pass


def persist(repository, entity, resource: str):
    try:
        return repository.save(entity)
    except EnrollmentRepositoryConflictError as error:
        raise EnrollmentConflictError(f"{resource} persistence conflict") from error


def delete(repository, entity, resource: str) -> None:
    try:
        repository.delete(entity)
    except EnrollmentRepositoryConflictError as error:
        raise EnrollmentConflictError(f"{resource} is referenced") from error


class UserCourseService:
    def __init__(self, repository, user_repository, study_plan_course_repository):
        self.repository = repository
        self.user_repository = user_repository
        self.study_plan_course_repository = study_plan_course_repository

    def get(self, entity_id: int) -> UserCourse:
        entity = self.repository.get(entity_id)
        if entity is None:
            raise EnrollmentNotFoundError("UserCourse")
        return entity

    def list(self):
        return self.repository.list()

    def create(self, *, user_id: int, study_plan_course_id: int):
        return self._save(None, user_id, study_plan_course_id)

    def update(self, entity_id: int, **values):
        entity = self.get(entity_id)
        return self._save(
            entity,
            values.get("user_id", entity.user_id),
            values.get("study_plan_course_id", entity.study_plan_course_id),
        )

    def delete(self, entity_id: int) -> None:
        delete(self.repository, self.get(entity_id), "UserCourse")

    def _save(self, entity, user_id: int, study_plan_course_id: int):
        if self.user_repository.get(user_id) is None:
            raise EnrollmentNotFoundError("User")
        if self.study_plan_course_repository.get(study_plan_course_id) is None:
            raise EnrollmentNotFoundError("StudyPlanCourse")
        duplicate = self.repository.find_equivalent(user_id, study_plan_course_id)
        if duplicate is not None and (entity is None or duplicate.id != entity.id):
            raise EnrollmentConflictError("UserCourse already exists")
        if entity is None:
            entity = UserCourse(
                user_id=user_id, study_plan_course_id=study_plan_course_id
            )
        else:
            entity.user_id = user_id
            entity.study_plan_course_id = study_plan_course_id
        return persist(self.repository, entity, "UserCourse")


class CourseOfferingService:
    def __init__(self, repository, study_plan_course_repository):
        self.repository = repository
        self.study_plan_course_repository = study_plan_course_repository

    def get(self, entity_id: int) -> CourseOffering:
        entity = self.repository.get(entity_id)
        if entity is None:
            raise EnrollmentNotFoundError("CourseOffering")
        return entity

    def list(self):
        return self.repository.list()

    def create(self, **values):
        return self._save(None, values)

    def update(self, entity_id: int, **values):
        return self._save(self.get(entity_id), values)

    def delete(self, entity_id: int) -> None:
        delete(self.repository, self.get(entity_id), "CourseOffering")

    def _save(self, entity, values):
        current = (
            {}
            if entity is None
            else {
                "study_plan_course_id": entity.study_plan_course_id,
                "name": entity.name,
                "academic_year": entity.academic_year,
                "term": entity.term,
                "start_date": entity.start_date,
                "end_date": entity.end_date,
            }
        )
        current.update(values)
        required = ("study_plan_course_id", "name", "academic_year", "term")
        if any(current.get(field) is None for field in required):
            raise EnrollmentValidationError(
                "CourseOffering required fields cannot be null"
            )
        if (
            self.study_plan_course_repository.get(current["study_plan_course_id"])
            is None
        ):
            raise EnrollmentNotFoundError("StudyPlanCourse")
        try:
            current["name"] = normalize_name(current["name"], "CourseOffering")
        except InstitutionalValidationError as error:
            raise EnrollmentValidationError(str(error)) from error
        current["term"] = str(current["term"])
        start_date, end_date = current["start_date"], current["end_date"]
        if start_date is not None and end_date is not None and end_date < start_date:
            raise EnrollmentValidationError("end_date must be on or after start_date")
        duplicate = self.repository.find_equivalent(
            current["study_plan_course_id"],
            current["name"],
            current["academic_year"],
            current["term"],
            None if entity is None else entity.id,
        )
        if duplicate is not None:
            raise EnrollmentConflictError("CourseOffering already exists")
        if entity is None:
            entity = CourseOffering(**current)
        else:
            for field, value in current.items():
                setattr(entity, field, value)
        return persist(self.repository, entity, "CourseOffering")


class CourseEnrollmentService:
    def __init__(self, repository, user_course_repository, course_offering_repository):
        self.repository = repository
        self.user_course_repository = user_course_repository
        self.course_offering_repository = course_offering_repository

    def get(self, entity_id: int) -> CourseEnrollment:
        entity = self.repository.get(entity_id)
        if entity is None:
            raise EnrollmentNotFoundError("CourseEnrollment")
        return entity

    def list(self):
        return self.repository.list()

    def create(self, **values):
        return self._save(None, values)

    def update(self, entity_id: int, **values):
        return self._save(self.get(entity_id), values)

    def delete(self, entity_id: int) -> None:
        delete(self.repository, self.get(entity_id), "CourseEnrollment")

    def _save(self, entity, values):
        current = (
            {}
            if entity is None
            else {
                "user_course_id": entity.user_course_id,
                "course_offering_id": entity.course_offering_id,
                "status": entity.status,
                "final_grade": entity.final_grade,
            }
        )
        current.update(values)
        required = ("user_course_id", "course_offering_id", "status")
        if any(current.get(field) is None for field in required):
            raise EnrollmentValidationError(
                "CourseEnrollment required fields cannot be null"
            )
        current["status"] = str(current["status"])
        user_course = self.user_course_repository.get(current["user_course_id"])
        if user_course is None:
            raise EnrollmentNotFoundError("UserCourse")
        offering = self.course_offering_repository.get(current["course_offering_id"])
        if offering is None:
            raise EnrollmentNotFoundError("CourseOffering")
        if user_course.study_plan_course_id != offering.study_plan_course_id:
            raise EnrollmentValidationError(
                "CourseOffering must belong to UserCourse StudyPlanCourse"
            )
        if current["status"] == EnrollmentStatus.IN_PROGRESS:
            if current["final_grade"] is not None:
                raise EnrollmentValidationError(
                    "final_grade must be null for an IN_PROGRESS enrollment"
                )
            active = self.repository.find_active(
                current["user_course_id"], None if entity is None else entity.id
            )
            if active is not None:
                raise EnrollmentConflictError(
                    "UserCourse already has an IN_PROGRESS enrollment"
                )
        if entity is None:
            entity = CourseEnrollment(**current)
        else:
            for field, value in current.items():
                setattr(entity, field, value)
        return persist(self.repository, entity, "CourseEnrollment")
