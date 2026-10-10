from app.models.institutional import (
    Career,
    Course,
    StudyPlan,
    StudyPlanCourse,
    User,
    UserCareer,
)
from app.repositories.faculty import FacultyRepository
from app.repositories.institutional import (
    CareerRepository,
    CourseRepository,
    InstitutionalRepositoryConflictError,
    StudyPlanCourseRepository,
    StudyPlanRepository,
    UserCareerRepository,
    UserRepository,
)


class InstitutionalNotFoundError(Exception):
    def __init__(self, resource: str) -> None:
        self.resource = resource
        super().__init__(f"{resource} not found")


class InstitutionalConflictError(Exception):
    pass


class InstitutionalValidationError(Exception):
    pass


def normalize_name(name: str, resource: str) -> str:
    normalized = " ".join(name.split())
    if not normalized:
        raise InstitutionalValidationError(f"{resource} name cannot be empty")
    return normalized


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    def create(self) -> User:
        return self.repository.create()

    def get(self, entity_id: int) -> User:
        entity = self.repository.get(entity_id)
        if entity is None:
            raise InstitutionalNotFoundError("User")
        return entity

    def list(self) -> list[User]:
        return self.repository.list()

    def delete(self, entity_id: int) -> None:
        try:
            self.repository.delete(self.get(entity_id))
        except InstitutionalRepositoryConflictError as error:
            raise InstitutionalConflictError("User is referenced") from error


class CareerService:
    def __init__(
        self, repository: CareerRepository, faculty_repository: FacultyRepository
    ) -> None:
        self.repository = repository
        self.faculty_repository = faculty_repository

    def create(self, *, faculty_id: int, name: str) -> Career:
        return self._save(None, faculty_id=faculty_id, name=name)

    def get(self, entity_id: int) -> Career:
        entity = self.repository.get(entity_id)
        if entity is None:
            raise InstitutionalNotFoundError("Career")
        return entity

    def list(self) -> list[Career]:
        return self.repository.list()

    def update(
        self, entity_id: int, *, faculty_id: int | None = None, name: str | None = None
    ) -> Career:
        entity = self.get(entity_id)
        return self._save(
            entity,
            faculty_id=entity.faculty_id if faculty_id is None else faculty_id,
            name=entity.name if name is None else name,
        )

    def delete(self, entity_id: int) -> None:
        try:
            self.repository.delete(self.get(entity_id))
        except InstitutionalRepositoryConflictError as error:
            raise InstitutionalConflictError("Career is referenced") from error

    def _save(self, entity: Career | None, *, faculty_id: int, name: str) -> Career:
        if self.faculty_repository.get(faculty_id) is None:
            raise InstitutionalNotFoundError("Faculty")
        normalized = normalize_name(name, "Career")
        exclude_id = None if entity is None else entity.id
        if self.repository.find_equivalent(
            faculty_id=faculty_id, name=normalized, exclude_id=exclude_id
        ):
            raise InstitutionalConflictError("Career already exists in this Faculty")
        try:
            if entity is None:
                return self.repository.create(faculty_id=faculty_id, name=normalized)
            return self.repository.update(
                entity, faculty_id=faculty_id, name=normalized
            )
        except InstitutionalRepositoryConflictError as error:
            raise InstitutionalConflictError("Career persistence conflict") from error


class StudyPlanService:
    def __init__(
        self, repository: StudyPlanRepository, career_repository: CareerRepository
    ) -> None:
        self.repository = repository
        self.career_repository = career_repository

    def create(self, *, career_id: int, name: str) -> StudyPlan:
        return self._save(None, career_id=career_id, name=name)

    def get(self, entity_id: int) -> StudyPlan:
        entity = self.repository.get(entity_id)
        if entity is None:
            raise InstitutionalNotFoundError("StudyPlan")
        return entity

    def list(self) -> list[StudyPlan]:
        return self.repository.list()

    def update(
        self, entity_id: int, *, career_id: int | None = None, name: str | None = None
    ) -> StudyPlan:
        entity = self.get(entity_id)
        return self._save(
            entity,
            career_id=entity.career_id if career_id is None else career_id,
            name=entity.name if name is None else name,
        )

    def delete(self, entity_id: int) -> None:
        try:
            self.repository.delete(self.get(entity_id))
        except InstitutionalRepositoryConflictError as error:
            raise InstitutionalConflictError("StudyPlan is referenced") from error

    def _save(
        self, entity: StudyPlan | None, *, career_id: int, name: str
    ) -> StudyPlan:
        if self.career_repository.get(career_id) is None:
            raise InstitutionalNotFoundError("Career")
        normalized = normalize_name(name, "StudyPlan")
        exclude_id = None if entity is None else entity.id
        if self.repository.find_equivalent(
            career_id=career_id, name=normalized, exclude_id=exclude_id
        ):
            raise InstitutionalConflictError("StudyPlan already exists in this Career")
        try:
            if entity is None:
                return self.repository.create(career_id=career_id, name=normalized)
            return self.repository.update(entity, career_id=career_id, name=normalized)
        except InstitutionalRepositoryConflictError as error:
            raise InstitutionalConflictError(
                "StudyPlan persistence conflict"
            ) from error


class CourseService:
    def __init__(self, repository: CourseRepository) -> None:
        self.repository = repository

    def create(self, *, name: str, code: str | None = None) -> Course:
        return self._save(None, name=name, code=code)

    def get(self, entity_id: int) -> Course:
        entity = self.repository.get(entity_id)
        if entity is None:
            raise InstitutionalNotFoundError("Course")
        return entity

    def list(self) -> list[Course]:
        return self.repository.list()

    def update(
        self,
        entity_id: int,
        *,
        name: str | None = None,
        code: str | None = None,
        code_provided: bool = False,
    ) -> Course:
        entity = self.get(entity_id)
        return self._save(
            entity,
            name=entity.name if name is None else name,
            code=code if code_provided else entity.code,
        )

    def delete(self, entity_id: int) -> None:
        try:
            self.repository.delete(self.get(entity_id))
        except InstitutionalRepositoryConflictError as error:
            raise InstitutionalConflictError("Course is referenced") from error

    def _save(self, entity: Course | None, *, name: str, code: str | None) -> Course:
        normalized = normalize_name(name, "Course")
        exclude_id = None if entity is None else entity.id
        if self.repository.find_equivalent(name=normalized, exclude_id=exclude_id):
            raise InstitutionalConflictError("Course already exists")
        try:
            if entity is None:
                return self.repository.create(name=normalized, code=code)
            return self.repository.update(entity, name=normalized, code=code)
        except InstitutionalRepositoryConflictError as error:
            raise InstitutionalConflictError("Course persistence conflict") from error


class StudyPlanCourseService:
    def __init__(
        self,
        repository: StudyPlanCourseRepository,
        study_plan_repository: StudyPlanRepository,
        course_repository: CourseRepository,
    ) -> None:
        self.repository = repository
        self.study_plan_repository = study_plan_repository
        self.course_repository = course_repository

    def create(self, *, study_plan_id: int, course_id: int) -> StudyPlanCourse:
        return self._save(None, study_plan_id=study_plan_id, course_id=course_id)

    def get(self, entity_id: int) -> StudyPlanCourse:
        entity = self.repository.get(entity_id)
        if entity is None:
            raise InstitutionalNotFoundError("StudyPlanCourse")
        return entity

    def list(self) -> list[StudyPlanCourse]:
        return self.repository.list()

    def update(
        self,
        entity_id: int,
        *,
        study_plan_id: int | None = None,
        course_id: int | None = None,
    ) -> StudyPlanCourse:
        entity = self.get(entity_id)
        return self._save(
            entity,
            study_plan_id=(
                entity.study_plan_id if study_plan_id is None else study_plan_id
            ),
            course_id=entity.course_id if course_id is None else course_id,
        )

    def delete(self, entity_id: int) -> None:
        try:
            self.repository.delete(self.get(entity_id))
        except InstitutionalRepositoryConflictError as error:
            raise InstitutionalConflictError("StudyPlanCourse is referenced") from error

    def _save(
        self,
        entity: StudyPlanCourse | None,
        *,
        study_plan_id: int,
        course_id: int,
    ) -> StudyPlanCourse:
        if self.study_plan_repository.get(study_plan_id) is None:
            raise InstitutionalNotFoundError("StudyPlan")
        if self.course_repository.get(course_id) is None:
            raise InstitutionalNotFoundError("Course")
        exclude_id = None if entity is None else entity.id
        if self.repository.find_equivalent(
            study_plan_id=study_plan_id,
            course_id=course_id,
            exclude_id=exclude_id,
        ):
            raise InstitutionalConflictError("Course already belongs to StudyPlan")
        try:
            if entity is None:
                return self.repository.create(
                    study_plan_id=study_plan_id, course_id=course_id
                )
            return self.repository.update(
                entity, study_plan_id=study_plan_id, course_id=course_id
            )
        except InstitutionalRepositoryConflictError as error:
            raise InstitutionalConflictError(
                "StudyPlanCourse persistence conflict"
            ) from error


class UserCareerService:
    def __init__(
        self,
        repository: UserCareerRepository,
        user_repository: UserRepository,
        career_repository: CareerRepository,
        study_plan_repository: StudyPlanRepository,
    ) -> None:
        self.repository = repository
        self.user_repository = user_repository
        self.career_repository = career_repository
        self.study_plan_repository = study_plan_repository

    def create(self, *, user_id: int, career_id: int, study_plan_id: int) -> UserCareer:
        return self._save(
            None,
            user_id=user_id,
            career_id=career_id,
            study_plan_id=study_plan_id,
        )

    def get(self, entity_id: int) -> UserCareer:
        entity = self.repository.get(entity_id)
        if entity is None:
            raise InstitutionalNotFoundError("UserCareer")
        return entity

    def list(self) -> list[UserCareer]:
        return self.repository.list()

    def update(
        self,
        entity_id: int,
        *,
        user_id: int | None = None,
        career_id: int | None = None,
        study_plan_id: int | None = None,
    ) -> UserCareer:
        entity = self.get(entity_id)
        return self._save(
            entity,
            user_id=entity.user_id if user_id is None else user_id,
            career_id=entity.career_id if career_id is None else career_id,
            study_plan_id=(
                entity.study_plan_id if study_plan_id is None else study_plan_id
            ),
        )

    def delete(self, entity_id: int) -> None:
        try:
            self.repository.delete(self.get(entity_id))
        except InstitutionalRepositoryConflictError as error:
            raise InstitutionalConflictError("UserCareer is referenced") from error

    def _save(
        self,
        entity: UserCareer | None,
        *,
        user_id: int,
        career_id: int,
        study_plan_id: int,
    ) -> UserCareer:
        if self.user_repository.get(user_id) is None:
            raise InstitutionalNotFoundError("User")
        if self.career_repository.get(career_id) is None:
            raise InstitutionalNotFoundError("Career")
        study_plan = self.study_plan_repository.get(study_plan_id)
        if study_plan is None:
            raise InstitutionalNotFoundError("StudyPlan")
        if study_plan.career_id != career_id:
            raise InstitutionalValidationError(
                "StudyPlan does not belong to the selected Career"
            )
        exclude_id = None if entity is None else entity.id
        if self.repository.find_equivalent(
            user_id=user_id, career_id=career_id, exclude_id=exclude_id
        ):
            raise InstitutionalConflictError("UserCareer already exists")
        try:
            if entity is None:
                return self.repository.create(
                    user_id=user_id,
                    career_id=career_id,
                    study_plan_id=study_plan_id,
                )
            return self.repository.update(
                entity,
                user_id=user_id,
                career_id=career_id,
                study_plan_id=study_plan_id,
            )
        except InstitutionalRepositoryConflictError as error:
            raise InstitutionalConflictError(
                "UserCareer persistence conflict"
            ) from error
