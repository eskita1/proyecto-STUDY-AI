import os
from collections.abc import Generator

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
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
    if not (make_url(TEST_DATABASE_URL).database or "").endswith("_test"):
        pytest.fail("Integration tests require a database name ending in '_test'")
    config = Config("alembic.ini")
    config.attributes["database_url"] = TEST_DATABASE_URL
    command.upgrade(config, "head")
    engine = create_engine(TEST_DATABASE_URL)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    engine.dispose()


@pytest.fixture
def client(test_session_factory) -> Generator[TestClient, None, None]:
    with test_session_factory() as session:
        session.execute(
            text(
                "TRUNCATE users, courses, universities "
                "RESTART IDENTITY CASCADE"
            )
        )
        session.commit()

    def override_get_db() -> Generator[Session, None, None]:
        with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create(client: TestClient, path: str, payload: dict) -> dict:
    response = client.post(path, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def institutional_chain(client: TestClient) -> dict[str, dict]:
    university = create(
        client, "/universities", {"name": "University", "country_code": "AR"}
    )
    faculty = create(
        client,
        "/faculties",
        {"university_id": university["id"], "name": "Engineering"},
    )
    career = create(
        client,
        "/careers",
        {"faculty_id": faculty["id"], "name": "Computer Engineering"},
    )
    study_plan = create(
        client,
        "/study-plans",
        {"career_id": career["id"], "name": "Plan 2026"},
    )
    course = create(client, "/courses", {"name": "Algorithms", "code": "ALG"})
    study_plan_course = create(
        client,
        "/study-plan-courses",
        {"study_plan_id": study_plan["id"], "course_id": course["id"]},
    )
    user = create(client, "/users", {})
    return {
        "university": university,
        "faculty": faculty,
        "career": career,
        "study_plan": study_plan,
        "course": course,
        "study_plan_course": study_plan_course,
        "user": user,
    }


def test_institutional_crud_and_relationships(client: TestClient):
    entities = institutional_chain(client)
    user_career = create(
        client,
        "/user-careers",
        {
            "user_id": entities["user"]["id"],
            "career_id": entities["career"]["id"],
            "study_plan_id": entities["study_plan"]["id"],
        },
    )

    assert client.get("/careers").json() == [entities["career"]]
    assert client.get(f"/user-careers/{user_career['id']}").json() == user_career
    updated = client.patch(
        f"/courses/{entities['course']['id']}",
        json={"name": "Advanced Algorithms"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Advanced Algorithms"
    assert client.delete(f"/user-careers/{user_career['id']}").status_code == 204


def test_scoped_uniqueness_and_parent_validation(client: TestClient):
    entities = institutional_chain(client)
    duplicate = client.post(
        "/careers",
        json={
            "faculty_id": entities["faculty"]["id"],
            "name": " computer   engineering ",
        },
    )
    assert duplicate.status_code == 409
    assert client.post(
        "/careers", json={"faculty_id": 999, "name": "Science"}
    ).status_code == 404
    duplicate_link = client.post(
        "/study-plan-courses",
        json={
            "study_plan_id": entities["study_plan"]["id"],
            "course_id": entities["course"]["id"],
        },
    )
    assert duplicate_link.status_code == 409


def test_user_career_rejects_plan_from_other_career(client: TestClient):
    entities = institutional_chain(client)
    other_career = create(
        client,
        "/careers",
        {"faculty_id": entities["faculty"]["id"], "name": "Mathematics"},
    )
    other_plan = create(
        client,
        "/study-plans",
        {"career_id": other_career["id"], "name": "Math Plan"},
    )
    response = client.post(
        "/user-careers",
        json={
            "user_id": entities["user"]["id"],
            "career_id": entities["career"]["id"],
            "study_plan_id": other_plan["id"],
        },
    )
    assert response.status_code == 422


def test_restrictive_deletion_and_openapi(client: TestClient):
    entities = institutional_chain(client)
    assert client.delete(f"/faculties/{entities['faculty']['id']}").status_code == 409
    schema = client.get("/openapi.json").json()
    for path in (
        "/users",
        "/careers",
        "/study-plans",
        "/courses",
        "/study-plan-courses",
        "/user-careers",
    ):
        assert path in schema["paths"]
