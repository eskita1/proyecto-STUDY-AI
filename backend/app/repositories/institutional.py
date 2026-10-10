from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.institutional import (
    Career,
    Course,
    StudyPlan,
    StudyPlanCourse,
    User,
    UserCareer,
)


class InstitutionalRepositoryConflictError(Exception):
    pass


def commit(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise InstitutionalRepositoryConflictError from error


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self) -> User:
        user = User()
        self.session.add(user)
        commit(self.session)
        self.session.refresh(user)
        return user

    def get(self, entity_id: int) -> User | None:
        return self.session.get(User, entity_id)

    def list(self) -> list[User]:
        return list(self.session.scalars(select(User).order_by(User.id)))

    def delete(self, entity: User) -> None:
        self.session.delete(entity)
        commit(self.session)


class CareerRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, *, faculty_id: int, name: str) -> Career:
        entity = Career(faculty_id=faculty_id, name=name)
        self.session.add(entity)
        commit(self.session)
        self.session.refresh(entity)
        return entity

    def get(self, entity_id: int) -> Career | None:
        return self.session.get(Career, entity_id)

    def list(self) -> list[Career]:
        return list(self.session.scalars(select(Career).order_by(Career.id)))

    def find_equivalent(
        self, *, faculty_id: int, name: str, exclude_id: int | None = None
    ) -> Career | None:
        statement = select(Career).where(
            Career.faculty_id == faculty_id, func.lower(Career.name) == name.lower()
        )
        if exclude_id is not None:
            statement = statement.where(Career.id != exclude_id)
        return self.session.scalar(statement)

    def update(self, entity: Career, *, faculty_id: int, name: str) -> Career:
        entity.faculty_id = faculty_id
        entity.name = name
        commit(self.session)
        self.session.refresh(entity)
        return entity

    def delete(self, entity: Career) -> None:
        self.session.delete(entity)
        commit(self.session)


class StudyPlanRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, *, career_id: int, name: str) -> StudyPlan:
        entity = StudyPlan(career_id=career_id, name=name)
        self.session.add(entity)
        commit(self.session)
        self.session.refresh(entity)
        return entity

    def get(self, entity_id: int) -> StudyPlan | None:
        return self.session.get(StudyPlan, entity_id)

    def list(self) -> list[StudyPlan]:
        return list(self.session.scalars(select(StudyPlan).order_by(StudyPlan.id)))

    def find_equivalent(
        self, *, career_id: int, name: str, exclude_id: int | None = None
    ) -> StudyPlan | None:
        statement = select(StudyPlan).where(
            StudyPlan.career_id == career_id,
            func.lower(StudyPlan.name) == name.lower(),
        )
        if exclude_id is not None:
            statement = statement.where(StudyPlan.id != exclude_id)
        return self.session.scalar(statement)

    def update(self, entity: StudyPlan, *, career_id: int, name: str) -> StudyPlan:
        entity.career_id = career_id
        entity.name = name
        commit(self.session)
        self.session.refresh(entity)
        return entity

    def delete(self, entity: StudyPlan) -> None:
        self.session.delete(entity)
        commit(self.session)


class CourseRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, *, name: str, code: str | None) -> Course:
        entity = Course(name=name, code=code)
        self.session.add(entity)
        commit(self.session)
        self.session.refresh(entity)
        return entity

    def get(self, entity_id: int) -> Course | None:
        return self.session.get(Course, entity_id)

    def list(self) -> list[Course]:
        return list(self.session.scalars(select(Course).order_by(Course.id)))

    def find_equivalent(
        self, *, name: str, exclude_id: int | None = None
    ) -> Course | None:
        statement = select(Course).where(func.lower(Course.name) == name.lower())
        if exclude_id is not None:
            statement = statement.where(Course.id != exclude_id)
        return self.session.scalar(statement)

    def update(self, entity: Course, *, name: str, code: str | None) -> Course:
        entity.name = name
        entity.code = code
        commit(self.session)
        self.session.refresh(entity)
        return entity

    def delete(self, entity: Course) -> None:
        self.session.delete(entity)
        commit(self.session)


class StudyPlanCourseRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, *, study_plan_id: int, course_id: int) -> StudyPlanCourse:
        entity = StudyPlanCourse(study_plan_id=study_plan_id, course_id=course_id)
        self.session.add(entity)
        commit(self.session)
        self.session.refresh(entity)
        return entity

    def get(self, entity_id: int) -> StudyPlanCourse | None:
        return self.session.get(StudyPlanCourse, entity_id)

    def list(self) -> list[StudyPlanCourse]:
        statement = select(StudyPlanCourse).order_by(StudyPlanCourse.id)
        return list(self.session.scalars(statement))

    def find_equivalent(
        self,
        *,
        study_plan_id: int,
        course_id: int,
        exclude_id: int | None = None,
    ) -> StudyPlanCourse | None:
        statement = select(StudyPlanCourse).where(
            StudyPlanCourse.study_plan_id == study_plan_id,
            StudyPlanCourse.course_id == course_id,
        )
        if exclude_id is not None:
            statement = statement.where(StudyPlanCourse.id != exclude_id)
        return self.session.scalar(statement)

    def update(
        self, entity: StudyPlanCourse, *, study_plan_id: int, course_id: int
    ) -> StudyPlanCourse:
        entity.study_plan_id = study_plan_id
        entity.course_id = course_id
        commit(self.session)
        self.session.refresh(entity)
        return entity

    def delete(self, entity: StudyPlanCourse) -> None:
        self.session.delete(entity)
        commit(self.session)


class UserCareerRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, *, user_id: int, career_id: int, study_plan_id: int) -> UserCareer:
        entity = UserCareer(
            user_id=user_id, career_id=career_id, study_plan_id=study_plan_id
        )
        self.session.add(entity)
        commit(self.session)
        self.session.refresh(entity)
        return entity

    def get(self, entity_id: int) -> UserCareer | None:
        return self.session.get(UserCareer, entity_id)

    def list(self) -> list[UserCareer]:
        return list(self.session.scalars(select(UserCareer).order_by(UserCareer.id)))

    def find_equivalent(
        self, *, user_id: int, career_id: int, exclude_id: int | None = None
    ) -> UserCareer | None:
        statement = select(UserCareer).where(
            UserCareer.user_id == user_id, UserCareer.career_id == career_id
        )
        if exclude_id is not None:
            statement = statement.where(UserCareer.id != exclude_id)
        return self.session.scalar(statement)

    def update(
        self,
        entity: UserCareer,
        *,
        user_id: int,
        career_id: int,
        study_plan_id: int,
    ) -> UserCareer:
        entity.user_id = user_id
        entity.career_id = career_id
        entity.study_plan_id = study_plan_id
        commit(self.session)
        self.session.refresh(entity)
        return entity

    def delete(self, entity: UserCareer) -> None:
        self.session.delete(entity)
        commit(self.session)
