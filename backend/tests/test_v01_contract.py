from app.database.db import Base
from app.main import app


def test_v01_models_are_registered_and_openapi_surface_is_complete():
    required_tables = {
        "universities",
        "faculties",
        "careers",
        "study_plans",
        "courses",
        "study_plan_courses",
        "users",
        "user_careers",
        "user_courses",
        "course_offerings",
        "course_enrollments",
        "academic_sources",
        "extraction_proposals",
        "units",
        "topics",
        "subtopics",
        "enrollment_topics",
        "course_schedule_items",
        "assessments",
        "assessment_topics",
        "study_sessions",
        "study_session_topics",
        "practice_sessions",
        "practice_session_topics",
        "practice_exercises",
    }
    assert required_tables <= set(Base.metadata.tables)

    schema = app.openapi()
    required_paths = {
        "/universities",
        "/faculties",
        "/careers",
        "/study-plans",
        "/courses",
        "/study-plan-courses",
        "/users",
        "/user-careers",
        "/user-courses",
        "/course-offerings",
        "/course-enrollments",
        "/academic-sources",
        "/extraction-proposals",
        "/extraction-proposals/{entity_id}/confirm",
        "/enrollment-topics",
        "/course-enrollments/{course_enrollment_id}/progress",
        "/course-schedule-items",
        "/assessments",
        "/assessment-topics",
        "/study-sessions",
        "/study-session-topics",
        "/practice-sessions",
        "/practice-session-topics",
        "/practice-exercises",
    }
    assert required_paths <= set(schema["paths"])


def test_derived_values_are_not_writable_or_stored():
    schema = app.openapi()["components"]["schemas"]
    for request_schema in schema.values():
        properties = request_schema.get("properties", {})
        if request_schema.get("title", "").endswith(("Create", "Update")):
            assert "course_progress" not in properties
            assert "student_progress" not in properties
            assert "catch_up_progress" not in properties
            assert "last_studied_at" not in properties

    for table in Base.metadata.tables.values():
        columns = set(table.columns.keys())
        assert "course_progress" not in columns
        assert "student_progress" not in columns
        assert "catch_up_progress" not in columns
        assert "last_studied_at" not in columns
