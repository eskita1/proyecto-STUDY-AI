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


def structure(client: TestClient, offering_id: int, label: str) -> dict:
    source = post(
        client,
        "/academic-sources",
        {"type": "SYLLABUS", "course_offering_id": offering_id},
    )
    data = {
        "units": [
            {
                "id": None,
                "action": "CREATE",
                "name": label,
                "position": 1,
                "topics": [
                    {
                        "id": None,
                        "action": "CREATE",
                        "name": f"Topic {label}",
                        "position": 1,
                    }
                ],
            }
        ]
    }
    proposal = post(
        client,
        "/extraction-proposals",
        {"academic_source_id": source["id"], "extracted_data": data},
    )
    client.post(f"/extraction-proposals/{proposal['id']}/confirm")
    return client.get(f"/course-offerings/{offering_id}/topics").json()[0]


def setup(client: TestClient):
    university = post(client, "/universities", {"name": "U", "country_code": "AR"})
    faculty = post(
        client, "/faculties", {"university_id": university["id"], "name": "F"}
    )
    career = post(client, "/careers", {"faculty_id": faculty["id"], "name": "C"})
    plan = post(client, "/study-plans", {"career_id": career["id"], "name": "P"})
    course = post(client, "/courses", {"name": "Course"})
    spc = post(
        client,
        "/study-plan-courses",
        {"study_plan_id": plan["id"], "course_id": course["id"]},
    )
    offering = post(
        client,
        "/course-offerings",
        {
            "study_plan_course_id": spc["id"],
            "name": "A",
            "academic_year": 2026,
            "term": "ANNUAL",
        },
    )
    other = post(
        client,
        "/course-offerings",
        {
            "study_plan_course_id": spc["id"],
            "name": "B",
            "academic_year": 2026,
            "term": "ANNUAL",
        },
    )
    topic = structure(client, offering["id"], "A")
    other_topic = structure(client, other["id"], "B")
    user = post(client, "/users", {})
    user_course = post(
        client,
        "/user-courses",
        {"user_id": user["id"], "study_plan_course_id": spc["id"]},
    )
    enrollment = post(
        client,
        "/course-enrollments",
        {
            "user_course_id": user_course["id"],
            "course_offering_id": offering["id"],
            "status": "IN_PROGRESS",
        },
    )
    state = post(
        client,
        "/enrollment-topics",
        {
            "course_enrollment_id": enrollment["id"],
            "topic_id": topic["id"],
            "student_status": "NOT_STARTED",
        },
    )
    return enrollment, topic, other_topic, state


def test_quick_and_full_sessions_derive_latest_without_state_change(client: TestClient):
    enrollment, topic, _, state = setup(client)
    quick = post(
        client,
        "/study-sessions",
        {
            "course_enrollment_id": enrollment["id"],
            "started_at": "2026-04-01T12:00:00-03:00",
            "note": "quick",
        },
    )
    assert quick["ended_at"] is None
    post(
        client,
        "/study-session-topics",
        {"study_session_id": quick["id"], "topic_id": topic["id"]},
    )
    full = post(
        client,
        "/study-sessions",
        {
            "course_enrollment_id": enrollment["id"],
            "started_at": "2026-04-02T12:00:00-03:00",
            "ended_at": "2026-04-02T13:00:00-03:00",
        },
    )
    post(
        client,
        "/study-session-topics",
        {"study_session_id": full["id"], "topic_id": topic["id"]},
    )
    latest = client.get(
        f"/course-enrollments/{enrollment['id']}/topics/{topic['id']}/last-studied"
    ).json()
    assert latest["last_studied_at"].startswith("2026-04-02T15:00:00")
    assert (
        client.get(f"/enrollment-topics/{state['id']}").json()["student_status"]
        == "NOT_STARTED"
    )


def test_study_validation_and_cross_offering(client: TestClient):
    enrollment, _, other_topic, _ = setup(client)
    invalid_order = client.post(
        "/study-sessions",
        json={
            "course_enrollment_id": enrollment["id"],
            "started_at": "2026-04-02T12:00:00Z",
            "ended_at": "2026-04-01T12:00:00Z",
        },
    )
    assert invalid_order.status_code == 422
    naive = client.post(
        "/study-sessions",
        json={
            "course_enrollment_id": enrollment["id"],
            "started_at": "2026-04-02T12:00:00",
        },
    )
    assert naive.status_code == 422
    session = post(
        client,
        "/study-sessions",
        {
            "course_enrollment_id": enrollment["id"],
            "started_at": "2026-04-02T12:00:00Z",
        },
    )
    assert (
        client.post(
            "/study-session-topics",
            json={"study_session_id": session["id"], "topic_id": other_topic["id"]},
        ).status_code
        == 422
    )


def test_duplicate_topic_and_openapi(client: TestClient):
    enrollment, topic, _, _ = setup(client)
    session = post(
        client,
        "/study-sessions",
        {
            "course_enrollment_id": enrollment["id"],
            "started_at": "2026-04-02T12:00:00Z",
        },
    )
    payload = {"study_session_id": session["id"], "topic_id": topic["id"]}
    assert client.post("/study-session-topics", json=payload).status_code == 201
    assert client.post("/study-session-topics", json=payload).status_code == 409
    schema = client.get("/openapi.json").json()
    assert "/study-sessions" in schema["paths"]
