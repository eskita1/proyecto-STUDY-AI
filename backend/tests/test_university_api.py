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
        cleanup_session.execute(text("DELETE FROM universities"))
        cleanup_session.commit()

    def override_get_db() -> Generator[Session, None, None]:
        with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_university_crud(client: TestClient):
    create_response = client.post(
        "/universities",
        json={
            "name": "  Universidad   de Buenos Aires ",
            "country_code": "ar",
        },
    )
    assert create_response.status_code == 201
    university = create_response.json()
    assert university["name"] == "Universidad de Buenos Aires"
    assert university["country_code"] == "AR"

    get_response = client.get(f"/universities/{university['id']}")
    assert get_response.status_code == 200
    assert get_response.json() == university

    list_response = client.get("/universities")
    assert list_response.status_code == 200
    assert list_response.json() == [university]

    update_response = client.patch(
        f"/universities/{university['id']}",
        json={"name": "Universidad Nacional de Buenos Aires"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Universidad Nacional de Buenos Aires"
    assert update_response.json()["country_code"] == "AR"

    delete_response = client.delete(f"/universities/{university['id']}")
    assert delete_response.status_code == 204
    assert client.get(f"/universities/{university['id']}").status_code == 404


def test_duplicate_name_is_case_and_whitespace_insensitive(client: TestClient):
    first_response = client.post(
        "/universities",
        json={"name": "Universidad de Buenos Aires", "country_code": "AR"},
    )
    duplicate_response = client.post(
        "/universities",
        json={"name": " universidad   DE buenos aires ", "country_code": "ar"},
    )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409


def test_same_name_is_allowed_in_different_countries(client: TestClient):
    first_response = client.post(
        "/universities",
        json={"name": "National University", "country_code": "AR"},
    )
    second_response = client.post(
        "/universities",
        json={"name": "National University", "country_code": "UY"},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201


@pytest.mark.parametrize(
    ("payload", "expected_status"),
    [
        ({"name": "   ", "country_code": "AR"}, 422),
        ({"name": "University", "country_code": "ARG"}, 422),
        ({"name": "University", "country_code": "A1"}, 422),
    ],
)
def test_create_validates_input(
    client: TestClient,
    payload: dict[str, str],
    expected_status: int,
):
    response = client.post("/universities", json=payload)

    assert response.status_code == expected_status


def test_update_rejects_empty_payload_and_duplicate(client: TestClient):
    first = client.post(
        "/universities",
        json={"name": "University One", "country_code": "AR"},
    ).json()
    second = client.post(
        "/universities",
        json={"name": "University Two", "country_code": "AR"},
    ).json()

    assert client.patch(f"/universities/{first['id']}", json={}).status_code == 422
    duplicate_response = client.patch(
        f"/universities/{second['id']}",
        json={"name": " university one "},
    )
    assert duplicate_response.status_code == 409


def test_database_unique_index_rejects_case_insensitive_duplicate(
    test_session_factory,
):
    with test_session_factory() as session:
        session.execute(text("DELETE FROM universities"))
        session.execute(
            text(
                "INSERT INTO universities (name, country_code) "
                "VALUES ('University', 'AR')"
            )
        )
        session.commit()

        with pytest.raises(IntegrityError):
            session.execute(
                text(
                    "INSERT INTO universities (name, country_code) "
                    "VALUES ('UNIVERSITY', 'AR')"
                )
            )
            session.commit()
        session.rollback()


def test_database_constraints_reject_noncanonical_values(test_session_factory):
    with test_session_factory() as session:
        with pytest.raises(IntegrityError):
            session.execute(
                text(
                    "INSERT INTO universities (name, country_code) "
                    "VALUES ('  University', 'ar')"
                )
            )
            session.commit()
        session.rollback()
