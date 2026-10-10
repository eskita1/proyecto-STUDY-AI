from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.enrollment import CourseEnrollment, CourseOffering, UserCourse


class EnrollmentRepositoryConflictError(Exception):
    pass


def commit(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise EnrollmentRepositoryConflictError from error


class UserCourseRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, entity_id: int) -> UserCourse | None:
        return self.session.get(UserCourse, entity_id)

    def list(self) -> list[UserCourse]:
        return list(self.session.scalars(select(UserCourse).order_by(UserCourse.id)))

    def save(self, entity: UserCourse) -> UserCourse:
        self.session.add(entity)
        commit(self.session)
        self.session.refresh(entity)
        return entity

    def delete(self, entity) -> None:
        self.session.delete(entity)
        commit(self.session)

    def find_equivalent(
        self, user_id: int, study_plan_course_id: int
    ) -> UserCourse | None:
        return self.session.scalar(
            select(UserCourse).where(
                UserCourse.user_id == user_id,
                UserCourse.study_plan_course_id == study_plan_course_id,
            )
        )

    def has_enrollments(self, entity_id: int) -> bool:
        statement = (
            select(CourseEnrollment.id)
            .where(CourseEnrollment.user_course_id == entity_id)
            .limit(1)
        )
        return self.session.scalar(statement) is not None


class CourseOfferingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, entity_id: int) -> CourseOffering | None:
        return self.session.get(CourseOffering, entity_id)

    def list(self) -> list[CourseOffering]:
        return list(
            self.session.scalars(select(CourseOffering).order_by(CourseOffering.id))
        )

    def save(self, entity: CourseOffering) -> CourseOffering:
        self.session.add(entity)
        commit(self.session)
        self.session.refresh(entity)
        return entity

    def delete(self, entity: CourseOffering) -> None:
        self.session.delete(entity)
        commit(self.session)

    def find_equivalent(
        self,
        study_plan_course_id: int,
        name: str,
        academic_year: int,
        term: str,
        exclude_id: int | None = None,
    ) -> CourseOffering | None:
        statement = select(CourseOffering).where(
            CourseOffering.study_plan_course_id == study_plan_course_id,
            func.lower(CourseOffering.name) == name.lower(),
            CourseOffering.academic_year == academic_year,
            CourseOffering.term == term,
        )
        if exclude_id is not None:
            statement = statement.where(CourseOffering.id != exclude_id)
        return self.session.scalar(statement)

    def has_enrollments(self, entity_id: int) -> bool:
        statement = (
            select(CourseEnrollment.id)
            .where(CourseEnrollment.course_offering_id == entity_id)
            .limit(1)
        )
        return self.session.scalar(statement) is not None


class CourseEnrollmentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, entity_id: int) -> CourseEnrollment | None:
        return self.session.get(CourseEnrollment, entity_id)

    def list(self) -> list[CourseEnrollment]:
        return list(
            self.session.scalars(
                select(CourseEnrollment).order_by(CourseEnrollment.created_at)
            )
        )

    def save(self, entity: CourseEnrollment) -> CourseEnrollment:
        self.session.add(entity)
        commit(self.session)
        self.session.refresh(entity)
        return entity

    def delete(self, entity: CourseEnrollment) -> None:
        self.session.delete(entity)
        commit(self.session)

    def find_active(
        self, user_course_id: int, exclude_id: int | None = None
    ) -> CourseEnrollment | None:
        statement = select(CourseEnrollment).where(
            CourseEnrollment.user_course_id == user_course_id,
            CourseEnrollment.status == "IN_PROGRESS",
        )
        if exclude_id is not None:
            statement = statement.where(CourseEnrollment.id != exclude_id)
        return self.session.scalar(statement)
