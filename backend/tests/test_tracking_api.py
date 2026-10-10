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


def setup(client: TestClient) -> tuple[dict, dict, list[dict], dict]:
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
    source = post(
        client,
        "/academic-sources",
        {"type": "SYLLABUS", "course_offering_id": offering["id"]},
    )
    payload = {
        "units": [
            {
                "id": None,
                "action": "CREATE",
                "name": "Unit",
                "position": 1,
                "topics": [
                    {"id": None, "action": "CREATE", "name": "T1", "position": 1},
                    {"id": None, "action": "CREATE", "name": "T2", "position": 2},
                ],
            }
        ]
    }
    proposal = post(
        client,
        "/extraction-proposals",
        {"academic_source_id": source["id"], "extracted_data": payload},
    )
    assert (
        client.post(f"/extraction-proposals/{proposal['id']}/confirm").status_code
        == 200
    )
    topics = client.get(f"/course-offerings/{offering['id']}/topics").json()
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
    return offering, enrollment, topics, spc


def test_manual_states_allow_backward_transitions_and_duplicates_are_rejected(
    client: TestClient,
):
    _, enrollment, topics, _ = setup(client)
    state = post(
        client,
        "/enrollment-topics",
        {
            "course_enrollment_id": enrollment["id"],
            "topic_id": topics[0]["id"],
            "course_progress_status": "SEEN",
            "student_status": "STUDIED",
            "personal_note": "done",
        },
    )
    response = client.patch(
        f"/enrollment-topics/{state['id']}",
        json={"course_progress_status": "NOT_SEEN", "student_status": "IN_PROGRESS"},
    )
    assert response.status_code == 200
    assert response.json()["student_status"] == "IN_PROGRESS"
    duplicate = client.post(
        "/enrollment-topics",
        json={"course_enrollment_id": enrollment["id"], "topic_id": topics[0]["id"]},
    )
    assert duplicate.status_code == 409


def test_cross_offering_topic_is_rejected(client: TestClient):
    _, enrollment, _, spc = setup(client)
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
    source = post(
        client,
        "/academic-sources",
        {"type": "SYLLABUS", "course_offering_id": other["id"]},
    )
    payload = {
        "units": [
            {
                "id": None,
                "action": "CREATE",
                "name": "Other",
                "position": 1,
                "topics": [
                    {
                        "id": None,
                        "action": "CREATE",
                        "name": "Other topic",
                        "position": 1,
                    }
                ],
            }
        ]
    }
    proposal = post(
        client,
        "/extraction-proposals",
        {"academic_source_id": source["id"], "extracted_data": payload},
    )
    client.post(f"/extraction-proposals/{proposal['id']}/confirm")
    other_topic = client.get(f"/course-offerings/{other['id']}/topics").json()[0]
    response = client.post(
        "/enrollment-topics",
        json={"course_enrollment_id": enrollment["id"], "topic_id": other_topic["id"]},
    )
    assert response.status_code == 422


def test_progress_is_derived_and_removed_topics_are_excluded(client: TestClient):
    offering, enrollment, topics, _ = setup(client)
    post(
        client,
        "/enrollment-topics",
        {
            "course_enrollment_id": enrollment["id"],
            "topic_id": topics[0]["id"],
            "course_progress_status": "SEEN",
            "student_status": "STUDIED",
        },
    )
    state = post(
        client,
        "/enrollment-topics",
        {
            "course_enrollment_id": enrollment["id"],
            "topic_id": topics[1]["id"],
            "course_progress_status": "SEEN",
            "student_status": "IN_PROGRESS",
        },
    )
    metrics = client.get(f"/course-enrollments/{enrollment['id']}/progress").json()
    assert metrics["course_progress"] == 1.0
    assert metrics["student_progress"] == 0.5
    assert metrics["catch_up_progress"] == 0.5
    assert metrics["academic_gap_topic_ids"] == [topics[1]["id"]]

    source = post(
        client,
        "/academic-sources",
        {"type": "THEORETICAL_MATERIAL", "course_offering_id": offering["id"]},
    )
    remove = {
        "units": [
            {
                "id": client.get(f"/course-offerings/{offering['id']}/units").json()[0][
                    "id"
                ],
                "action": "UPDATE",
                "name": "Unit",
                "position": 1,
                "topics": [{"id": topics[1]["id"], "action": "REMOVE"}],
            }
        ]
    }
    proposal = post(
        client,
        "/extraction-proposals",
        {"academic_source_id": source["id"], "extracted_data": remove},
    )
    assert (
        client.post(f"/extraction-proposals/{proposal['id']}/confirm").status_code
        == 200
    )
    metrics = client.get(f"/course-enrollments/{enrollment['id']}/progress").json()
    assert metrics["active_topic_count"] == 1
    assert metrics["student_progress"] == 1.0
    assert (
        client.get(f"/enrollment-topics/{state['id']}").json()["student_status"]
        == "IN_PROGRESS"
    )


def test_zero_denominators_and_openapi(client: TestClient):
    offering, enrollment, topics, _ = setup(client)
    source = post(
        client,
        "/academic-sources",
        {"type": "SCHEDULE", "course_offering_id": offering["id"]},
    )
    unit_id = client.get(f"/course-offerings/{offering['id']}/units").json()[0]["id"]
    proposal = post(
        client,
        "/extraction-proposals",
        {
            "academic_source_id": source["id"],
            "extracted_data": {"units": [{"id": unit_id, "action": "REMOVE"}]},
        },
    )
    client.post(f"/extraction-proposals/{proposal['id']}/confirm")
    metrics = client.get(f"/course-enrollments/{enrollment['id']}/progress").json()
    assert metrics["course_progress"] is None
    assert metrics["student_progress"] is None
    assert metrics["catch_up_progress"] is None
    assert topics
    schema = client.get("/openapi.json").json()
    assert "/enrollment-topics" in schema["paths"]
    assert "/course-enrollments/{course_enrollment_id}/progress" in schema["paths"]
