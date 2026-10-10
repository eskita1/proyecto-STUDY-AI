import os
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from threading import Event

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from app.database.db import get_db
from app.main import app
from app.repositories.academic import (
    AcademicSourceRepository,
    AcademicStructureRepository,
    ExtractionProposalRepository,
)
from app.services.academic import AcademicConflictError, ProposalService

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


class PausingProposalRepository(ExtractionProposalRepository):
    def __init__(self, session: Session, locked: Event, release: Event) -> None:
        super().__init__(session)
        self.locked = locked
        self.release = release

    def get_for_update(self, entity_id: int):
        entity = super().get_for_update(entity_id)
        self.locked.set()
        if not self.release.wait(timeout=5):
            raise RuntimeError("Timed out waiting to release proposal review")
        return entity


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


def setup_study_plans(client: TestClient) -> tuple[dict, dict]:
    university = post(
        client, "/universities", {"name": "University", "country_code": "AR"}
    )
    faculty = post(
        client,
        "/faculties",
        {"university_id": university["id"], "name": "Engineering"},
    )
    career = post(
        client,
        "/careers",
        {"faculty_id": faculty["id"], "name": "Computer Science"},
    )
    first = post(
        client,
        "/study-plans",
        {"career_id": career["id"], "name": "Plan 2026"},
    )
    second = post(
        client,
        "/study-plans",
        {"career_id": career["id"], "name": "Plan 2027"},
    )
    return first, second


def study_plan_source(client: TestClient, study_plan_id: int) -> dict:
    return post(
        client,
        "/academic-sources",
        {"type": "STUDY_PLAN", "study_plan_id": study_plan_id},
    )


def study_plan_proposal(
    client: TestClient, study_plan_id: int, courses: list[dict]
) -> dict:
    academic_source = study_plan_source(client, study_plan_id)
    return post(
        client,
        "/extraction-proposals",
        {
            "academic_source_id": academic_source["id"],
            "extracted_data": {"courses": courses},
        },
    )


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


def test_other_sources_are_informational_and_cannot_confirm_structure(
    client: TestClient,
):
    plan, offering = setup_offering(client)
    initial_relations = client.get("/study-plan-courses").json()
    sources = [
        post(
            client,
            "/academic-sources",
            {"type": "OTHER", "study_plan_id": plan["id"]},
        ),
        post(
            client,
            "/academic-sources",
            {"type": "OTHER", "course_offering_id": offering["id"]},
        ),
    ]
    payloads = [
        {"courses": [{"action": "CREATE", "name": "Must Not Exist"}]},
        structure_payload(),
    ]

    for academic_source, extracted_data in zip(sources, payloads, strict=True):
        proposal = post(
            client,
            "/extraction-proposals",
            {
                "academic_source_id": academic_source["id"],
                "extracted_data": extracted_data,
            },
        )
        response = client.post(f"/extraction-proposals/{proposal['id']}/confirm")
        assert response.status_code == 422
        assert "informational" in response.json()["detail"]
        assert client.get(f"/extraction-proposals/{proposal['id']}").json()[
            "status"
        ] == "PENDING"
        assert client.get(f"/academic-sources/{academic_source['id']}").json()[
            "status"
        ] == "PENDING"

    assert client.get("/study-plan-courses").json() == initial_relations
    assert client.get(f"/course-offerings/{offering['id']}/units").json() == []


@pytest.mark.parametrize(
    ("first_action", "second_action", "expected_status", "expected_units"),
    [
        ("confirm", "confirm", "CONFIRMED", 1),
        ("confirm", "reject", "CONFIRMED", 1),
        ("reject", "confirm", "REJECTED", 0),
    ],
)
def test_proposal_review_is_serialized(
    client: TestClient,
    factory,
    first_action: str,
    second_action: str,
    expected_status: str,
    expected_units: int,
):
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
    locked = Event()
    release = Event()
    second_started = Event()

    def review(action: str, pause_after_lock: bool):
        with factory() as session:
            proposal_repository = (
                PausingProposalRepository(session, locked, release)
                if pause_after_lock
                else ExtractionProposalRepository(session)
            )
            service = ProposalService(
                proposal_repository,
                AcademicSourceRepository(session),
                AcademicStructureRepository(session),
            )
            if not pause_after_lock:
                second_started.set()
            return getattr(service, action)(proposal["id"])

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(review, first_action, True)
        assert locked.wait(timeout=5)
        second = executor.submit(review, second_action, False)
        assert second_started.wait(timeout=5)
        with pytest.raises(FutureTimeoutError):
            second.result(timeout=0.2)
        release.set()
        assert first.result(timeout=5).status == expected_status
        with pytest.raises(AcademicConflictError):
            second.result(timeout=5)

    assert client.get(f"/extraction-proposals/{proposal['id']}").json()[
        "status"
    ] == expected_status
    assert len(client.get(f"/course-offerings/{offering['id']}/units").json()) == (
        expected_units
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
            "academic_source_id": source(
                client, offering["id"], "THEORETICAL_MATERIAL"
            )["id"],
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


def test_study_plan_confirmation_creates_relations_with_existing_and_new_courses(
    client: TestClient,
):
    study_plan, _ = setup_study_plans(client)
    existing = post(client, "/courses", {"name": "Algorithms", "code": "CS-101"})
    proposal = study_plan_proposal(
        client,
        study_plan["id"],
        [
            {
                "action": "CREATE",
                "study_plan_course_id": None,
                "course_id": existing["id"],
                "name": None,
                "code": None,
            },
            {
                "action": "CREATE",
                "study_plan_course_id": None,
                "course_id": None,
                "name": "  Mathematical   Analysis II ",
                "code": "61.03",
            },
        ],
    )

    response = client.post(f"/extraction-proposals/{proposal['id']}/confirm")

    assert response.status_code == 200
    assert response.json()["status"] == "CONFIRMED"
    courses = client.get("/courses").json()
    created = next(
        item for item in courses if item["name"] == "Mathematical Analysis II"
    )
    assert created["code"] == "61.03"
    relations = client.get("/study-plan-courses").json()
    assert {(item["study_plan_id"], item["course_id"]) for item in relations} == {
        (study_plan["id"], existing["id"]),
        (study_plan["id"], created["id"]),
    }


def test_study_plan_confirmation_rejects_duplicate_course_and_stays_pending(
    client: TestClient,
):
    study_plan, _ = setup_study_plans(client)
    course = post(client, "/courses", {"name": "Algorithms"})
    post(
        client,
        "/study-plan-courses",
        {"study_plan_id": study_plan["id"], "course_id": course["id"]},
    )
    proposal = study_plan_proposal(
        client,
        study_plan["id"],
        [
            {
                "action": "CREATE",
                "study_plan_course_id": None,
                "course_id": course["id"],
            }
        ],
    )

    response = client.post(f"/extraction-proposals/{proposal['id']}/confirm")

    assert response.status_code == 409
    assert (
        client.get(f"/extraction-proposals/{proposal['id']}").json()["status"]
        == "PENDING"
    )


def test_study_plan_confirmation_updates_only_relation_owned_course_id(
    client: TestClient,
):
    study_plan, _ = setup_study_plans(client)
    old_course = post(client, "/courses", {"name": "Old Course"})
    new_course = post(client, "/courses", {"name": "New Course"})
    relation = post(
        client,
        "/study-plan-courses",
        {"study_plan_id": study_plan["id"], "course_id": old_course["id"]},
    )
    proposal = study_plan_proposal(
        client,
        study_plan["id"],
        [
            {
                "action": "UPDATE",
                "study_plan_course_id": relation["id"],
                "course_id": new_course["id"],
            }
        ],
    )

    response = client.post(f"/extraction-proposals/{proposal['id']}/confirm")

    assert response.status_code == 200
    updated = client.get(f"/study-plan-courses/{relation['id']}").json()
    assert updated["course_id"] == new_course["id"]
    assert client.get(f"/courses/{old_course['id']}").json()["name"] == "Old Course"


def test_study_plan_confirmation_rejects_foreign_relation_and_course_mutation(
    client: TestClient,
):
    first_plan, second_plan = setup_study_plans(client)
    course = post(client, "/courses", {"name": "Algorithms"})
    foreign_relation = post(
        client,
        "/study-plan-courses",
        {"study_plan_id": second_plan["id"], "course_id": course["id"]},
    )
    foreign_proposal = study_plan_proposal(
        client,
        first_plan["id"],
        [
            {
                "action": "UPDATE",
                "study_plan_course_id": foreign_relation["id"],
                "course_id": course["id"],
            }
        ],
    )
    mutation_proposal = study_plan_proposal(
        client,
        second_plan["id"],
        [
            {
                "action": "UPDATE",
                "study_plan_course_id": foreign_relation["id"],
                "course_id": course["id"],
                "name": "Renamed globally",
            }
        ],
    )

    assert (
        client.post(
            f"/extraction-proposals/{foreign_proposal['id']}/confirm"
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/extraction-proposals/{mutation_proposal['id']}/confirm"
        ).status_code
        == 422
    )
    assert client.get(f"/courses/{course['id']}").json()["name"] == "Algorithms"


def test_study_plan_confirmation_removes_only_unreferenced_relation(
    client: TestClient,
):
    study_plan, _ = setup_study_plans(client)
    unused_course = post(client, "/courses", {"name": "Unused"})
    used_course = post(client, "/courses", {"name": "Used"})
    unused = post(
        client,
        "/study-plan-courses",
        {"study_plan_id": study_plan["id"], "course_id": unused_course["id"]},
    )
    used = post(
        client,
        "/study-plan-courses",
        {"study_plan_id": study_plan["id"], "course_id": used_course["id"]},
    )
    user = post(client, "/users", {})
    post(
        client,
        "/user-courses",
        {
            "user_id": user["id"],
            "study_plan_course_id": used["id"],
        },
    )
    remove_unused = study_plan_proposal(
        client,
        study_plan["id"],
        [{"action": "REMOVE", "study_plan_course_id": unused["id"]}],
    )
    remove_used = study_plan_proposal(
        client,
        study_plan["id"],
        [{"action": "REMOVE", "study_plan_course_id": used["id"]}],
    )

    assert (
        client.post(f"/extraction-proposals/{remove_unused['id']}/confirm").status_code
        == 200
    )
    assert client.get(f"/study-plan-courses/{unused['id']}").status_code == 404
    failure = client.post(f"/extraction-proposals/{remove_used['id']}/confirm")
    assert failure.status_code == 409
    assert "referenced" in failure.json()["detail"]
    assert client.get(f"/study-plan-courses/{used['id']}").status_code == 200


def test_invalid_study_plan_action_rolls_back_every_change(client: TestClient):
    study_plan, _ = setup_study_plans(client)
    proposal = study_plan_proposal(
        client,
        study_plan["id"],
        [
            {
                "action": "CREATE",
                "study_plan_course_id": None,
                "course_id": None,
                "name": "Must Roll Back",
                "code": "ROLLBACK",
            },
            {
                "action": "UPDATE",
                "study_plan_course_id": 999,
                "course_id": 999,
            },
        ],
    )

    response = client.post(f"/extraction-proposals/{proposal['id']}/confirm")

    assert response.status_code == 404
    assert all(
        course["name"] != "Must Roll Back" for course in client.get("/courses").json()
    )
    assert client.get("/study-plan-courses").json() == []
    assert (
        client.get(f"/extraction-proposals/{proposal['id']}").json()["status"]
        == "PENDING"
    )


def test_invalid_study_plan_payload_is_rejected(client: TestClient):
    study_plan, _ = setup_study_plans(client)
    academic_source = study_plan_source(client, study_plan["id"])
    proposal = post(
        client,
        "/extraction-proposals",
        {
            "academic_source_id": academic_source["id"],
            "extracted_data": {"courses": [{"action": "CREATE"}]},
        },
    )

    response = client.post(f"/extraction-proposals/{proposal['id']}/confirm")

    assert response.status_code == 422
    assert (
        client.get(f"/extraction-proposals/{proposal['id']}").json()["status"]
        == "PENDING"
    )
