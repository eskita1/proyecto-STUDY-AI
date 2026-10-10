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


def add_structure(
    client: TestClient, offering_id: int, label: str
) -> tuple[dict, dict]:
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
                "name": f"Unit {label}",
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
    assert (
        client.post(f"/extraction-proposals/{proposal['id']}/confirm").status_code
        == 200
    )
    return (
        client.get(f"/course-offerings/{offering_id}/units").json()[0],
        client.get(f"/course-offerings/{offering_id}/topics").json()[0],
    )


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
    unit, topic = add_structure(client, offering["id"], "A")
    _, other_topic = add_structure(client, other["id"], "B")
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
            "student_status": "STUDIED",
        },
    )
    return offering, other, unit, topic, other_topic, enrollment, state


def test_schedule_target_rules_and_no_progress_mutation(client: TestClient):
    offering, _, unit, topic, other_topic, _, state = setup(client)
    item = post(
        client,
        "/course-schedule-items",
        {
            "course_offering_id": offering["id"],
            "scheduled_date": "2026-04-01",
            "unit_id": unit["id"],
            "position": 1,
        },
    )
    assert item["topic_id"] is None
    both = client.post(
        "/course-schedule-items",
        json={
            "course_offering_id": offering["id"],
            "scheduled_date": "2026-04-02",
            "unit_id": unit["id"],
            "topic_id": topic["id"],
            "position": 2,
        },
    )
    assert both.status_code == 422
    cross = client.post(
        "/course-schedule-items",
        json={
            "course_offering_id": offering["id"],
            "scheduled_date": "2026-04-03",
            "topic_id": other_topic["id"],
            "position": 3,
        },
    )
    assert cross.status_code == 422
    assert (
        client.get(f"/enrollment-topics/{state['id']}").json()["course_progress_status"]
        == "NOT_SEEN"
    )


def test_assessment_topics_and_preparation_coverage(client: TestClient):
    offering, _, _, topic, other_topic, enrollment, _ = setup(client)
    assessment = post(
        client,
        "/assessments",
        {
            "course_offering_id": offering["id"],
            "name": "  Midterm 1 ",
            "type": "MIDTERM",
            "date": "2026-05-01",
        },
    )
    assert assessment["name"] == "Midterm 1"
    relation = post(
        client,
        "/assessment-topics",
        {"assessment_id": assessment["id"], "topic_id": topic["id"]},
    )
    assert relation["topic_id"] == topic["id"]
    assert (
        client.post(
            "/assessment-topics",
            json={"assessment_id": assessment["id"], "topic_id": topic["id"]},
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/assessment-topics",
            json={"assessment_id": assessment["id"], "topic_id": other_topic["id"]},
        ).status_code
        == 422
    )
    coverage = client.get(
        f"/course-enrollments/{enrollment['id']}/assessments/{assessment['id']}/preparation"
    ).json()
    assert coverage["active_topic_count"] == 1
    assert coverage["preparation_coverage"] == 1.0


def test_assessment_zero_denominator_and_openapi(client: TestClient):
    offering, _, _, _, _, enrollment, _ = setup(client)
    assessment = post(
        client,
        "/assessments",
        {
            "course_offering_id": offering["id"],
            "name": "Final",
            "type": "FINAL",
            "date": "2026-12-01",
        },
    )
    coverage = client.get(
        f"/course-enrollments/{enrollment['id']}/assessments/{assessment['id']}/preparation"
    ).json()
    assert coverage["preparation_coverage"] is None
    schema = client.get("/openapi.json").json()
    assert "/course-schedule-items" in schema["paths"]
    assert "/assessment-topics" in schema["paths"]
