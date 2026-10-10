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
        {"type": "PRACTICE_MATERIAL", "course_offering_id": offering_id},
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
            "course_progress_status": "NOT_SEEN",
            "student_status": "NOT_STARTED",
        },
    )
    return enrollment, topic, other_topic, state


def test_quick_practice_validates_counts_and_preserves_state(client: TestClient):
    enrollment, topic, _, state = setup(client)
    quick = post(
        client,
        "/practice-sessions",
        {
            "course_enrollment_id": enrollment["id"],
            "occurred_at": "2026-05-01T12:00:00Z",
            "source_type": "Worksheet",
            "source_name": "Set 1",
            "mode": "QUICK",
            "total_exercises": 5,
            "correct_exercises": 2,
            "partial_exercises": 1,
            "incorrect_exercises": 2,
        },
    )
    assert quick["mode"] == "QUICK"
    post(
        client,
        "/practice-session-topics",
        {"practice_session_id": quick["id"], "topic_id": topic["id"]},
    )
    invalid = client.post(
        "/practice-sessions",
        json={
            "course_enrollment_id": enrollment["id"],
            "occurred_at": "2026-05-01T12:00:00Z",
            "source_type": "Worksheet",
            "source_name": "Set 2",
            "mode": "QUICK",
            "total_exercises": 5,
            "correct_exercises": 5,
            "partial_exercises": 1,
            "incorrect_exercises": 0,
        },
    )
    assert invalid.status_code == 422
    assert (
        client.get(f"/enrollment-topics/{state['id']}").json()["student_status"]
        == "NOT_STARTED"
    )
    assert (
        client.get(f"/enrollment-topics/{state['id']}").json()["course_progress_status"]
        == "NOT_SEEN"
    )


def test_detailed_practice_uses_exercises_and_rejects_cross_offering(
    client: TestClient,
):
    enrollment, topic, other_topic, _ = setup(client)
    detailed = post(
        client,
        "/practice-sessions",
        {
            "course_enrollment_id": enrollment["id"],
            "occurred_at": "2026-05-01T12:00:00-03:00",
            "source_type": "Exam",
            "source_name": "2025 Final",
            "mode": "DETAILED",
        },
    )
    exercise = post(
        client,
        "/practice-exercises",
        {
            "practice_session_id": detailed["id"],
            "label": " Exercise 1 ",
            "result": "PARTIALLY_CORRECT",
        },
    )
    assert exercise["label"] == "Exercise 1"
    not_evaluated = post(
        client,
        "/practice-exercises",
        {
            "practice_session_id": detailed["id"],
            "label": "Exercise 2",
            "result": "NOT_EVALUATED",
        },
    )
    assert not_evaluated["result"] == "NOT_EVALUATED"
    post(
        client,
        "/practice-session-topics",
        {"practice_session_id": detailed["id"], "topic_id": topic["id"]},
    )
    assert (
        client.post(
            "/practice-session-topics",
            json={"practice_session_id": detailed["id"], "topic_id": other_topic["id"]},
        ).status_code
        == 422
    )
    quick = post(
        client,
        "/practice-sessions",
        {
            "course_enrollment_id": enrollment["id"],
            "occurred_at": "2026-05-02T12:00:00Z",
            "source_type": "Quiz",
            "source_name": "Q",
            "mode": "QUICK",
            "total_exercises": 0,
            "correct_exercises": 0,
            "partial_exercises": 0,
            "incorrect_exercises": 0,
        },
    )
    assert (
        client.post(
            "/practice-exercises",
            json={
                "practice_session_id": quick["id"],
                "label": "E",
                "result": "CORRECT",
            },
        ).status_code
        == 422
    )


def test_practice_mode_exclusivity_results_and_openapi(client: TestClient):
    enrollment, _, _, _ = setup(client)
    mixed = client.post(
        "/practice-sessions",
        json={
            "course_enrollment_id": enrollment["id"],
            "occurred_at": "2026-05-01T12:00:00Z",
            "source_type": "Exam",
            "source_name": "X",
            "mode": "DETAILED",
            "total_exercises": 0,
            "correct_exercises": 0,
            "partial_exercises": 0,
            "incorrect_exercises": 0,
        },
    )
    assert mixed.status_code == 422
    detailed = post(
        client,
        "/practice-sessions",
        {
            "course_enrollment_id": enrollment["id"],
            "occurred_at": "2026-05-01T12:00:00Z",
            "source_type": "Exam",
            "source_name": "X",
            "mode": "DETAILED",
        },
    )
    invalid_result = client.post(
        "/practice-exercises",
        json={"practice_session_id": detailed["id"], "label": "E", "result": "WRONG"},
    )
    assert invalid_result.status_code == 422
    schema = client.get("/openapi.json").json()
    assert "/practice-sessions" in schema["paths"]
    assert "/practice-exercises" in schema["paths"]
