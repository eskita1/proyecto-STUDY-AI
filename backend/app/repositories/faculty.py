from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.faculty import Faculty


class FacultyRepositoryConflictError(Exception):
    pass


class FacultyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, *, university_id: int, name: str) -> Faculty:
        faculty = Faculty(university_id=university_id, name=name)
        self.session.add(faculty)
        self._commit()
        self.session.refresh(faculty)
        return faculty

    def get(self, faculty_id: int) -> Faculty | None:
        return self.session.get(Faculty, faculty_id)

    def list(self) -> list[Faculty]:
        statement = select(Faculty).order_by(Faculty.id)
        return list(self.session.scalars(statement))

    def find_by_name_and_university(
        self,
        *,
        name: str,
        university_id: int,
        exclude_id: int | None = None,
    ) -> Faculty | None:
        statement = select(Faculty).where(
            Faculty.university_id == university_id,
            func.lower(Faculty.name) == name.lower(),
        )
        if exclude_id is not None:
            statement = statement.where(Faculty.id != exclude_id)
        return self.session.scalar(statement)

    def update(
        self,
        faculty: Faculty,
        *,
        university_id: int,
        name: str,
    ) -> Faculty:
        faculty.university_id = university_id
        faculty.name = name
        self._commit()
        self.session.refresh(faculty)
        return faculty

    def delete(self, faculty: Faculty) -> None:
        self.session.delete(faculty)
        self._commit()

    def _commit(self) -> None:
        try:
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            raise FacultyRepositoryConflictError from error
