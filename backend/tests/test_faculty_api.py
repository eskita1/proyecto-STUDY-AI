import os
from collections.abc import Generator

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from app.database.db import get_db
from app.main import app

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="TEST_DATABASE_URL is required for PostgreSQL integration tests",
)


@pytest.fixture(scope="module")
def test_session_factory():
    assert TEST_DATABASE_URL is not None
    database_name = make_url(TEST_DATABASE_URL).database or ""
    if not database_name.endswith("_test"):
        pytest.fail("Integration tests require a database name ending in '_test'")

    alembic_config = Config("alembic.ini")
    alembic_config.attributes["database_url"] = TEST_DATABASE_URL
    command.upgrade(alembic_config, "head")

    engine = create_engine(TEST_DATABASE_URL)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    engine.dispose()


@pytest.fixture
def client(test_session_factory) -> Generator[TestClient, None, None]:
    with test_session_factory() as cleanup_session:
        cleanup_session.execute(
            text("TRUNCATE faculties, universities RESTART IDENTITY")
        )
        cleanup_session.commit()

    def override_get_db() -> Generator[Session, None, None]:
        with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_university(client: TestClient, name: str, country_code: str) -> dict:
    response = client.post(
        "/universities",
        json={"name": name, "country_code": country_code},
    )
    assert response.status_code == 201
    return response.json()


def test_faculty_crud_and_move_between_universities(client: TestClient):
    first_university = create_university(client, "University One", "AR")
    second_university = create_university(client, "University Two", "UY")

    create_response = client.post(
        "/faculties",
        json={
            "university_id": first_university["id"],
            "name": "  Facultad   de Ingeniería ",
        },
    )
    assert create_response.status_code == 201
    faculty = create_response.json()
    assert faculty == {
        "id": faculty["id"],
        "university_id": first_university["id"],
        "name": "Facultad de Ingeniería",
    }

    get_response = client.get(f"/faculties/{faculty['id']}")
    assert get_response.status_code == 200
    assert get_response.json() == faculty

    list_response = client.get("/faculties")
    assert list_response.status_code == 200
    assert list_response.json() == [faculty]

    update_response = client.patch(
        f"/faculties/{faculty['id']}",
        json={
            "university_id": second_university["id"],
            "name": "School of Engineering",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json() == {
        "id": faculty["id"],
        "university_id": second_university["id"],
        "name": "School of Engineering",
    }

    delete_response = client.delete(f"/faculties/{faculty['id']}")
    assert delete_response.status_code == 204
    assert client.get(f"/faculties/{faculty['id']}").status_code == 404


def test_create_rejects_missing_university(client: TestClient):
    response = client.post(
        "/faculties",
        json={"university_id": 999, "name": "Engineering"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "University not found"}


def test_create_rejects_blank_name(client: TestClient):
    university = create_university(client, "University", "AR")

    response = client.post(
        "/faculties",
        json={"university_id": university["id"], "name": "   "},
    )

    assert response.status_code == 422


def test_duplicate_name_is_case_and_whitespace_insensitive(client: TestClient):
    university = create_university(client, "University", "AR")
    first_response = client.post(
        "/faculties",
        json={"university_id": university["id"], "name": "Engineering"},
    )
    duplicate_response = client.post(
        "/faculties",
        json={
            "university_id": university["id"],
            "name": "  engineering  ",
        },
    )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409


def test_same_name_is_allowed_in_different_universities(client: TestClient):
    first_university = create_university(client, "University One", "AR")
    second_university = create_university(client, "University Two", "UY")

    first_response = client.post(
        "/faculties",
        json={"university_id": first_university["id"], "name": "Engineering"},
    )
    second_response = client.post(
        "/faculties",
        json={"university_id": second_university["id"], "name": "Engineering"},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201


def test_move_rejects_duplicate_in_destination_university(client: TestClient):
    first_university = create_university(client, "University One", "AR")
    second_university = create_university(client, "University Two", "UY")
    moving = client.post(
        "/faculties",
        json={"university_id": first_university["id"], "name": "Engineering"},
    ).json()
    client.post(
        "/faculties",
        json={"university_id": second_university["id"], "name": "engineering"},
    )

    response = client.patch(
        f"/faculties/{moving['id']}",
        json={"university_id": second_university["id"]},
    )

    assert response.status_code == 409


def test_missing_faculty_and_invalid_updates(client: TestClient):
    assert client.get("/faculties/999").status_code == 404
    assert client.patch("/faculties/999", json={"name": "Science"}).status_code == 404
    assert client.delete("/faculties/999").status_code == 404
    assert client.patch("/faculties/999", json={}).status_code == 422


def test_university_delete_is_restricted_while_faculty_exists(client: TestClient):
    university = create_university(client, "University", "AR")
    faculty = client.post(
        "/faculties",
        json={"university_id": university["id"], "name": "Engineering"},
    ).json()

    delete_response = client.delete(f"/universities/{university['id']}")

    assert delete_response.status_code == 409
    assert client.get(f"/faculties/{faculty['id']}").status_code == 200


def test_database_rejects_invalid_university_reference(test_session_factory):
    with test_session_factory() as session:
        session.execute(text("TRUNCATE faculties, universities RESTART IDENTITY"))
        session.commit()

        with pytest.raises(IntegrityError):
            session.execute(
                text(
                    "INSERT INTO faculties (university_id, name) "
                    "VALUES (999, 'Engineering')"
                )
            )
            session.commit()
        session.rollback()


def test_database_enforces_scoped_case_insensitive_uniqueness(
    test_session_factory,
):
    with test_session_factory() as session:
        session.execute(text("TRUNCATE faculties, universities RESTART IDENTITY"))
        university_id = session.scalar(
            text(
                "INSERT INTO universities (name, country_code) "
                "VALUES ('University', 'AR') RETURNING id"
            )
        )
        session.execute(
            text(
                "INSERT INTO faculties (university_id, name) "
                "VALUES (:university_id, 'Engineering')"
            ),
            {"university_id": university_id},
        )
        session.commit()

        with pytest.raises(IntegrityError):
            session.execute(
                text(
                    "INSERT INTO faculties (university_id, name) "
                    "VALUES (:university_id, 'ENGINEERING')"
                ),
                {"university_id": university_id},
            )
            session.commit()
        session.rollback()


def test_database_rejects_noncanonical_name(test_session_factory):
    with test_session_factory() as session:
        session.execute(text("TRUNCATE faculties, universities RESTART IDENTITY"))
        university_id = session.scalar(
            text(
                "INSERT INTO universities (name, country_code) "
                "VALUES ('University', 'AR') RETURNING id"
            )
        )
        session.commit()

        with pytest.raises(IntegrityError):
            session.execute(
                text(
                    "INSERT INTO faculties (university_id, name) "
                    "VALUES (:university_id, '  Engineering')"
                ),
                {"university_id": university_id},
            )
            session.commit()
        session.rollback()


def test_openapi_includes_faculty_contracts(client: TestClient):
    schema = client.get("/openapi.json").json()

    assert "/faculties" in schema["paths"]
    assert "/faculties/{faculty_id}" in schema["paths"]
    assert "FacultyCreate" in schema["components"]["schemas"]
    assert "FacultyUpdate" in schema["components"]["schemas"]
    assert "FacultyRead" in schema["components"]["schemas"]
