from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.university import University


class UniversityRepositoryConflictError(Exception):
    pass


class UniversityRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, *, name: str, country_code: str) -> University:
        university = University(name=name, country_code=country_code)
        self.session.add(university)
        self._commit()
        self.session.refresh(university)
        return university

    def get(self, university_id: int) -> University | None:
        return self.session.get(University, university_id)

    def list(self) -> list[University]:
        statement = select(University).order_by(University.id)
        return list(self.session.scalars(statement))

    def find_by_name_and_country(
        self,
        *,
        name: str,
        country_code: str,
        exclude_id: int | None = None,
    ) -> University | None:
        statement = select(University).where(
            University.country_code == country_code,
            func.lower(University.name) == name.lower(),
        )
        if exclude_id is not None:
            statement = statement.where(University.id != exclude_id)
        return self.session.scalar(statement)

    def update(
        self,
        university: University,
        *,
        name: str,
        country_code: str,
    ) -> University:
        university.name = name
        university.country_code = country_code
        self._commit()
        self.session.refresh(university)
        return university

    def delete(self, university: University) -> None:
        self.session.delete(university)
        self._commit()

    def _commit(self) -> None:
        try:
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            raise UniversityRepositoryConflictError from error
