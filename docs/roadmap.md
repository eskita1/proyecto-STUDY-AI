# StudyAI Roadmap

This roadmap describes implementation order. `docs/releases/v0.1.md` is the exclusive source of current release scope, and the product and domain documents define behavior and invariants.

## V0.1 — Source-backed academic tracking

V0.1 is delivered incrementally in this order.

### 1. Technical foundation and University slice

- FastAPI application and health endpoint;
- PostgreSQL, SQLAlchemy, and Alembic;
- environment-based configuration;
- tests, Ruff, CI, and Swagger/OpenAPI;
- existing University model and API slice.

### 2. Institutional foundation

- `User`;
- `Faculty`;
- `Career`;
- `StudyPlan`;
- `Course`;
- `StudyPlanCourse`;
- `UserCareer`.

### 3. Enrollment

- `UserCourse` as the historical relationship between a User and a StudyPlanCourse;
- `CourseOffering` for a specific chair or section and academic year or term;
- `CourseEnrollment` as one concrete attempt in a CourseOffering;
- CourseEnrollment `status` and `final_grade`;
- `IN_PROGRESS`, `PASSED`, and `FAILED` enrollment statuses.

### 4. Source-backed academic structure

- `AcademicSource`;
- source extraction and proposed structure;
- validation before confirmation;
- confirmed `Unit`, `Topic`, and `Subtopic` structure per CourseOffering.

The required flow is:

```text
source -> extraction -> proposed structure -> validation -> confirmed domain
```

### 5. Student tracking and derived progress

- `EnrollmentTopic` per CourseEnrollment and Topic;
- `course_progress_status`: `NOT_SEEN` or `SEEN`;
- `student_status`: `NOT_STARTED`, `IN_PROGRESS`, or `STUDIED`;
- personal notes;
- derived course progress, student progress, catch-up progress, academic gaps, and assessment preparation coverage.

Derived metrics are computed from authoritative records and are not stored as independent sources of truth. `STUDIED` does not imply Practice or Mastery.

### 6. Schedules and assessments

- `CourseScheduleItem`;
- `Assessment`;
- `AssessmentTopic`.

Schedules represent plans and do not automatically mark Topics as `SEEN`.

### 7. Study sessions

- `StudySession`;
- `StudySessionTopic`;
- quick and full session modes;
- derived `last_studied_at`.

StudySessions do not automatically change `student_status`.

### 8. Practice

- `PracticeSession`;
- `PracticeSessionTopic`;
- quick aggregate mode;
- `PracticeExercise` detailed mode.

Practice is separate from Progress and Mastery and does not automatically change `student_status`.

### 9. Integration hardening

- migration-chain verification;
- domain, service, repository, and API tests;
- CourseOffering isolation and relationship validation;
- derived-metric verification;
- complete Swagger/OpenAPI coverage for included behavior;
- green pytest, Ruff, and CI checks.

## Beyond V0.1

Later releases may add capabilities such as Mastery, recommendations, and broader AI assistance. Their scope and ordering require future product and release decisions and must not be implemented as part of V0.1.
