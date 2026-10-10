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
    TEST_DATABASE_URL is None, reason="TEST_DATABASE_URL is required"
)


@pytest.fixture(scope="module")
def factory():
    assert TEST_DATABASE_URL is not None
    if not (make_url(TEST_DATABASE_URL).database or "").endswith("_test"):
        pytest.fail("Integration tests require a database name ending in '_test'")
    config = Config("alembic.ini")
    config.attributes["database_url"] = TEST_DATABASE_URL
    command.upgrade(config, "head")
    engine = create_engine(TEST_DATABASE_URL)
    yield sessionmaker(bind=engine, expire_on_commit=False)
    engine.dispose()


@pytest.fixture
def client(factory) -> Generator[TestClient, None, None]:
    with factory() as session:
        session.execute(
            text("TRUNCATE users, courses, universities RESTART IDENTITY CASCADE")
        )
        session.commit()

    def override() -> Generator[Session, None, None]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def post(client: TestClient, path: str, payload: dict) -> dict:
    response = client.post(path, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def setup_chain(client: TestClient) -> tuple[dict, dict, dict]:
    university = post(client, "/universities", {"name": "U", "country_code": "AR"})
    faculty = post(
        client, "/faculties", {"university_id": university["id"], "name": "F"}
    )
    career = post(client, "/careers", {"faculty_id": faculty["id"], "name": "Career"})
    plan = post(client, "/study-plans", {"career_id": career["id"], "name": "Plan"})
    course = post(client, "/courses", {"name": "Algorithms"})
    spc = post(
        client,
        "/study-plan-courses",
        {"study_plan_id": plan["id"], "course_id": course["id"]},
    )
    user = post(client, "/users", {})
    user_course = post(
        client,
        "/user-courses",
        {"user_id": user["id"], "study_plan_course_id": spc["id"]},
    )
    offering = post(
        client,
        "/course-offerings",
        {
            "study_plan_course_id": spc["id"],
            "name": "  Chair   A ",
            "academic_year": 2026,
            "term": "FIRST_TERM",
            "start_date": "2026-03-01",
            "end_date": "2026-07-01",
        },
    )
    return spc, user_course, offering


def test_enrollment_flow_and_history(client: TestClient):
    _, user_course, offering = setup_chain(client)
    assert offering["name"] == "Chair A"
    first = post(
        client,
        "/course-enrollments",
        {
            "user_course_id": user_course["id"],
            "course_offering_id": offering["id"],
            "status": "IN_PROGRESS",
        },
    )
    assert "final_grade" in first and "created_at" in first
    finished = client.patch(
        f"/course-enrollments/{first['id']}",
        json={"status": "FAILED", "final_grade": "Absent"},
    )
    assert finished.status_code == 200
    second = post(
        client,
        "/course-enrollments",
        {
            "user_course_id": user_course["id"],
            "course_offering_id": offering["id"],
            "status": "PASSED",
            "final_grade": "A",
        },
    )
    assert second["final_grade"] == "A"
    assert len(client.get("/course-enrollments").json()) == 2


def test_enrollment_rules(client: TestClient):
    _, user_course, offering = setup_chain(client)
    payload = {
        "user_course_id": user_course["id"],
        "course_offering_id": offering["id"],
        "status": "IN_PROGRESS",
    }
    assert client.post("/course-enrollments", json=payload).status_code == 201
    assert client.post("/course-enrollments", json=payload).status_code == 409
    payload["final_grade"] = "10"
    assert client.post("/course-enrollments", json=payload).status_code == 422
    payload["status"] = "DROPPED"
    assert client.post("/course-enrollments", json=payload).status_code == 422


def test_cross_course_enrollment_and_offering_dates_are_rejected(client: TestClient):
    _, user_course, _ = setup_chain(client)
    course = post(client, "/courses", {"name": "Databases"})
    plan_id = client.get("/study-plans").json()[0]["id"]
    other_spc = post(
        client,
        "/study-plan-courses",
        {"study_plan_id": plan_id, "course_id": course["id"]},
    )
    bad_dates = client.post(
        "/course-offerings",
        json={
            "study_plan_course_id": other_spc["id"],
            "name": "B",
            "academic_year": 2026,
            "term": "ANNUAL",
            "start_date": "2026-12-01",
            "end_date": "2026-03-01",
        },
    )
    assert bad_dates.status_code == 422
    other = post(
        client,
        "/course-offerings",
        {
            "study_plan_course_id": other_spc["id"],
            "name": "B",
            "academic_year": 2026,
            "term": "ANNUAL",
        },
    )
    response = client.post(
        "/course-enrollments",
        json={
            "user_course_id": user_course["id"],
            "course_offering_id": other["id"],
            "status": "FAILED",
        },
    )
    assert response.status_code == 422


def test_openapi_contains_enrollment_contracts(client: TestClient):
    schema = client.get("/openapi.json").json()
    for path in ("/user-courses", "/course-offerings", "/course-enrollments"):
        assert path in schema["paths"]
