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


def post(client: TestClient, path: str, payload: dict | None = None) -> dict:
    response = client.post(path, json={} if payload is None else payload)
    assert response.status_code == 201, response.text
    return response.json()


def setup_offering(
    client: TestClient, course_name: str = "Calculus"
) -> tuple[dict, dict]:
    university = post(client, "/universities", {"name": "U", "country_code": "AR"})
    faculty = post(
        client, "/faculties", {"university_id": university["id"], "name": "F"}
    )
    career = post(client, "/careers", {"faculty_id": faculty["id"], "name": "C"})
    plan = post(client, "/study-plans", {"career_id": career["id"], "name": "P"})
    course = post(client, "/courses", {"name": course_name})
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
            "name": "Chair",
            "academic_year": 2026,
            "term": "ANNUAL",
        },
    )
    return plan, offering


def source(client: TestClient, offering_id: int, source_type: str = "SYLLABUS") -> dict:
    return post(
        client,
        "/academic-sources",
        {"type": source_type, "course_offering_id": offering_id},
    )


def structure_payload() -> dict:
    return {
        "units": [
            {
                "id": None,
                "action": "CREATE",
                "name": "  Differentiability ",
                "description": None,
                "position": 1,
                "topics": [
                    {
                        "id": None,
                        "action": "CREATE",
                        "name": "Partial derivatives",
                        "position": 1,
                        "subtopics": [
                            {
                                "id": None,
                                "action": "CREATE",
                                "name": "Definition",
                                "position": 1,
                            }
                        ],
                    }
                ],
            }
        ]
    }


def test_source_ownership_rules(client: TestClient):
    plan, offering = setup_offering(client)
    plan_source = post(
        client,
        "/academic-sources",
        {"type": "STUDY_PLAN", "study_plan_id": plan["id"]},
    )
    assert plan_source["status"] == "PENDING"
    assert (
        post(
            client,
            "/academic-sources",
            {"type": "OTHER", "course_offering_id": offering["id"]},
        )["type"]
        == "OTHER"
    )
    both = client.post(
        "/academic-sources",
        json={
            "type": "OTHER",
            "study_plan_id": plan["id"],
            "course_offering_id": offering["id"],
        },
    )
    assert both.status_code == 422
    wrong = client.post(
        "/academic-sources", json={"type": "SYLLABUS", "study_plan_id": plan["id"]}
    )
    assert wrong.status_code == 422

    proposal = post(
        client,
        "/extraction-proposals",
        {
            "academic_source_id": plan_source["id"],
            "extracted_data": {"items": []},
        },
    )
    assert (
        client.post(f"/extraction-proposals/{proposal['id']}/confirm").status_code
        == 422
    )
    assert (
        client.get(f"/extraction-proposals/{proposal['id']}").json()["status"]
        == "PENDING"
    )


def test_confirmation_creates_structure_and_provenance(client: TestClient):
    _, offering = setup_offering(client)
    academic_source = source(client, offering["id"])
    proposal = post(
        client,
        "/extraction-proposals",
        {
            "academic_source_id": academic_source["id"],
            "extracted_data": structure_payload(),
        },
    )
    confirmed = client.post(f"/extraction-proposals/{proposal['id']}/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "CONFIRMED"
    units = client.get(f"/course-offerings/{offering['id']}/units").json()
    topics = client.get(f"/course-offerings/{offering['id']}/topics").json()
    subtopics = client.get(f"/course-offerings/{offering['id']}/subtopics").json()
    assert units[0]["name"] == "Differentiability"
    assert units[0]["confirmed_from_proposal_id"] == proposal["id"]
    assert topics[0]["confirmed_from_proposal_id"] == proposal["id"]
    assert subtopics[0]["confirmed_from_proposal_id"] == proposal["id"]
    assert (
        client.post(f"/extraction-proposals/{proposal['id']}/confirm").status_code
        == 409
    )


def test_rejection_and_invalid_confirmation_leave_structure_unchanged(
    client: TestClient,
):
    _, offering = setup_offering(client)
    rejected = post(
        client,
        "/extraction-proposals",
        {
            "academic_source_id": source(client, offering["id"])["id"],
            "extracted_data": structure_payload(),
        },
    )
    assert (
        client.post(f"/extraction-proposals/{rejected['id']}/reject").status_code == 200
    )
    assert client.get(f"/course-offerings/{offering['id']}/units").json() == []

    invalid = structure_payload()
    invalid["units"].append(
        {"id": 999, "action": "UPDATE", "name": "Missing", "position": 2, "topics": []}
    )
    proposal = post(
        client,
        "/extraction-proposals",
        {
            "academic_source_id": source(
                client, offering["id"], "THEORETICAL_MATERIAL"
            )["id"],
            "extracted_data": invalid,
        },
    )
    assert (
        client.post(f"/extraction-proposals/{proposal['id']}/confirm").status_code
        == 404
    )
    assert client.get(f"/course-offerings/{offering['id']}/units").json() == []
    assert (
        client.get(f"/extraction-proposals/{proposal['id']}").json()["status"]
        == "PENDING"
    )


def test_update_remove_and_offering_isolation(client: TestClient):
    _, offering = setup_offering(client)
    first_source = source(client, offering["id"])
    first = post(
        client,
        "/extraction-proposals",
        {
            "academic_source_id": first_source["id"],
            "extracted_data": structure_payload(),
        },
    )
    assert (
        client.post(f"/extraction-proposals/{first['id']}/confirm").status_code == 200
    )
    unit = client.get(f"/course-offerings/{offering['id']}/units").json()[0]
    topic = client.get(f"/course-offerings/{offering['id']}/topics").json()[0]
    subtopic = client.get(f"/course-offerings/{offering['id']}/subtopics").json()[0]
    changes = {
        "units": [
            {
                "id": unit["id"],
                "action": "UPDATE",
                "name": "Derivatives",
                "position": 1,
                "description": "Updated",
                "topics": [
                    {
                        "id": topic["id"],
                        "action": "UPDATE",
                        "name": "Partial derivatives",
                        "position": 1,
                        "subtopics": [{"id": subtopic["id"], "action": "REMOVE"}],
                    }
                ],
            }
        ]
    }
    second = post(
        client,
        "/extraction-proposals",
        {
            "academic_source_id": source(client, offering["id"], "OTHER")["id"],
            "extracted_data": changes,
        },
    )
    assert (
        client.post(f"/extraction-proposals/{second['id']}/confirm").status_code == 200
    )
    assert (
        client.get(f"/course-offerings/{offering['id']}/units").json()[0]["name"]
        == "Derivatives"
    )
    assert client.get(f"/course-offerings/{offering['id']}/subtopics").json() == []

    remove = {"units": [{"id": unit["id"], "action": "REMOVE"}]}
    third = post(
        client,
        "/extraction-proposals",
        {
            "academic_source_id": source(client, offering["id"], "SCHEDULE")["id"],
            "extracted_data": remove,
        },
    )
    assert (
        client.post(f"/extraction-proposals/{third['id']}/confirm").status_code == 200
    )
    assert (
        client.get(f"/course-offerings/{offering['id']}/units").json()[0]["status"]
        == "REMOVED"
    )


def test_academic_openapi_contracts(client: TestClient):
    schema = client.get("/openapi.json").json()
    for path in (
        "/academic-sources",
        "/extraction-proposals",
        "/course-offerings/{offering_id}/units",
    ):
        assert path in schema["paths"]
