# StudyAI Domain

**Status:** V0.1 definition

This document defines the domain concepts, relationships, states, and invariants for StudyAI V0.1. It does not define endpoints, database tables, or framework-specific implementation details.

## 1. Domain overview

StudyAI separates four concerns:

1. institutional structure;
2. the concrete academic delivery of a Course;
3. the User's academic history and personal state;
4. activity records used to derive study and practice information.

The core relationships are:

```text
University -> Faculty -> Career -> StudyPlan -> StudyPlanCourse
                                         Course -> StudyPlanCourse

StudyPlanCourse -> CourseOffering -> Unit -> Topic -> Subtopic

User -> UserCareer
User -> UserCourse -> CourseEnrollment -> EnrollmentTopic
```

## 2. Institutional structure

### 2.1 University

`University` represents an institution.

A University may contain multiple Faculties.

### 2.2 Faculty

`Faculty` represents a faculty or academic unit within a University.

Every Faculty belongs to exactly one University. A Faculty may contain multiple Careers.

### 2.3 Career

`Career` represents a degree program.

Every Career belongs to exactly one Faculty. A Career may have multiple StudyPlans.

### 2.4 StudyPlan

`StudyPlan` represents a specific version of a Career's curriculum.

Every StudyPlan belongs to exactly one Career. A StudyPlan contains Courses through StudyPlanCourse relationships.

### 2.5 Course

`Course` represents an abstract course concept. It does not identify a curriculum placement, chair, section, academic period, or individual student's state.

The same Course may appear in multiple StudyPlans.

### 2.6 StudyPlanCourse

`StudyPlanCourse` represents a Course inside one specific StudyPlan.

It is the curriculum-specific course concept from which concrete CourseOfferings are delivered.

The institutional chain is:

```text
University -> Faculty -> Career -> StudyPlan -> StudyPlanCourse
```

with each StudyPlanCourse referring to a Course.

## 3. Concrete academic delivery

### 3.1 CourseOffering

`CourseOffering` represents the delivery of one StudyPlanCourse by a specific chair or section in a specific academic period or year.

A CourseOffering belongs to exactly one StudyPlanCourse. Its confirmed academic structure contains Units, Topics, and Subtopics.

Students share academic structure only when they belong to the same CourseOffering. Students enrolled in different CourseOfferings do not share confirmed academic structure merely because their offerings refer to the same StudyPlanCourse or Course.

### 3.2 Unit

`Unit` is a top-level content grouping within a CourseOffering.

A Unit has one of these statuses:

- `ACTIVE`
- `REMOVED`

`REMOVED` means the Unit is no longer part of the active confirmed structure. It must not be physically deleted.

### 3.3 Topic

`Topic` is a content item within a Unit.

Every Topic belongs to exactly one Unit.

A Topic has one of these statuses:

- `ACTIVE`
- `REMOVED`

`REMOVED` means the Topic is no longer part of the active confirmed structure. It must not be physically deleted.

### 3.4 Subtopic

`Subtopic` is a finer-grained content item within a Topic.

Every Subtopic belongs to exactly one Topic.

A Subtopic may be created only from a source supplied by a User, chair, or University. AI must not invent a Subtopic from general model knowledge.

## 4. Academic sources and confirmation

### 4.1 AcademicSource

`AcademicSource` represents material supplied as evidence for academic structure.

Its type is one of:

- `STUDY_PLAN`
- `SYLLABUS`
- `SCHEDULE`
- `THEORETICAL_MATERIAL`
- `PRACTICE_MATERIAL`
- `OTHER`

Its status is one of:

- `PENDING`
- `CONFIRMED`
- `SUPERSEDED`

`PENDING` identifies a source that has not yet been confirmed. `CONFIRMED` identifies a source accepted for use in the academic structure. `SUPERSEDED` identifies a source replaced by a later source without erasing its history.

An `OTHER` source may belong to either a StudyPlan or a CourseOffering, with
exactly one owner. In V0.1 it is reference or informational material only. It
does not define a mapping into confirmed StudyPlan or CourseOffering structure,
so an ExtractionProposal for an `OTHER` source cannot be confirmed. A failed
confirmation leaves both the proposal and confirmed domain unchanged.

### 4.2 Confirmation flow

Units, Topics, and Subtopics are not freely created or edited by Users. They must originate in provided academic sources and pass through this flow:

```text
source -> extraction -> proposed structure -> validation -> confirmed domain
```

The extracted or proposed structure is not the confirmed academic domain. Validation is the boundary at which proposed information may become confirmed.

AI may assist with extraction and proposals. AI must never write directly into the confirmed academic domain.

## 5. User academic relationships

### 5.1 User

`User` represents a person using StudyAI. The V0.1 User is a university student.

### 5.2 UserCareer

`UserCareer` represents the relationship between a User and a Career, including the StudyPlan applicable to that User's Career.

A User may have more than one UserCareer.

### 5.3 UserCourse

`UserCourse` represents the historical relationship between a User and a StudyPlanCourse.

It persists across concrete attempts. Attempt-specific status, final grade, Topic state, Study, and Practice do not belong directly to UserCourse.

### 5.4 CourseEnrollment

`CourseEnrollment` represents one concrete attempt or enrollment by a User in a CourseOffering.

Conceptual fields:

- `user_course_id`
- `course_offering_id`
- `status`
- `final_grade`

Its status is one of:

- `IN_PROGRESS`
- `PASSED`
- `FAILED`

`RETAKING` and `DROPPED` are not V0.1 statuses.

The CourseEnrollment connects the User's historical UserCourse to the CourseOffering whose academic structure is shared for that attempt.

### 5.5 EnrollmentTopic

`EnrollmentTopic` represents a User's state for a Topic within one CourseEnrollment.

Conceptual fields:

- `course_enrollment_id`
- `topic_id`
- `course_progress_status`
- `student_status`
- `personal_note`

`course_progress_status` is one of:

- `NOT_SEEN`
- `SEEN`

`student_status` is one of:

- `NOT_STARTED`
- `IN_PROGRESS`
- `STUDIED`

The User manually controls both `course_progress_status` and `student_status`.

StudyAI must not automatically change `student_status`. The User may move freely between student states, including backwards.

`STUDIED` means that the User considers the Topic studied. It does not imply Practice or Mastery. Only `STUDIED` counts as completed for student-progress metrics.

A scheduled date does not automatically change `course_progress_status` to `SEEN`.

If the related Topic later becomes `REMOVED`, the EnrollmentTopic and its existing personal state must be preserved.

## 6. Study activity

### 6.1 StudySession

`StudySession` records study activity for one CourseEnrollment.

Conceptual fields:

- `course_enrollment_id`
- `started_at`
- `ended_at`, nullable
- `note`

Two modes are supported:

- quick mode, in which `ended_at` is absent;
- full mode, in which both `started_at` and `ended_at` are present.

Creating a StudySession must not automatically change any EnrollmentTopic `student_status`.

### 6.2 StudySessionTopic

`StudySessionTopic` associates a StudySession with a Topic studied during that session.

A StudySession may be associated with multiple Topics, and a Topic may be associated with multiple StudySessions.

### 6.3 Last studied time

`last_studied_at` is derived from the latest related StudySession. It must not be stored as a redundant source of truth.

## 7. Practice

### 7.1 PracticeSession

`PracticeSession` records Practice for one CourseEnrollment.

Conceptual fields:

- `course_enrollment_id`
- `occurred_at`
- `source_type`
- `source_name`
- `note`

Practice is independent from course progress and personal study state. Creating or updating Practice must not automatically modify EnrollmentTopic `student_status`.

### 7.2 PracticeSessionTopic

`PracticeSessionTopic` associates a PracticeSession with a Topic practiced during that session.

A PracticeSession may be associated with multiple Topics, and a Topic may be associated with multiple PracticeSessions.

### 7.3 Quick mode

Quick mode records aggregate counts:

- `total_exercises`
- `correct_exercises`
- `partial_exercises`
- `incorrect_exercises`

### 7.4 Detailed mode

Detailed mode records individual PracticeExercises.

`PracticeExercise` has these conceptual fields:

- `practice_session_id`
- `label`
- `result`

The result is one of:

- `CORRECT`
- `PARTIALLY_CORRECT`
- `INCORRECT`
- `NOT_EVALUATED`

### 7.5 Mastery boundary

Practice does not imply Mastery. Mastery remains a separate concept and is outside V0.1.

## 8. Time and assessments

### 8.1 CourseScheduleItem

`CourseScheduleItem` represents a planned academic date and ordering within a CourseOffering.

Conceptual fields:

- `course_offering_id`
- `scheduled_date`
- `unit_id`, optional
- `topic_id`, optional
- `position`

A schedule date represents a plan, not a confirmed event. It must not automatically mark a Topic as `SEEN`.

### 8.2 Assessment

`Assessment` represents an assessment belonging to a CourseOffering.

Conceptual fields:

- `course_offering_id`
- `name`
- `type`
- `date`
- `description`

Its type is one of:

- `MIDTERM`
- `FINAL`
- `RECOVERY`
- `ASSIGNMENT`
- `QUIZ`
- `OTHER`

### 8.3 AssessmentTopic

`AssessmentTopic` associates an Assessment with a Topic included in or relevant to that Assessment.

An Assessment may be associated with multiple Topics, and a Topic may be associated with multiple Assessments.

## 9. Derived metrics

Metrics are derived from confirmed academic structure and EnrollmentTopic state. They must not be stored as independent sources of truth.

The effective active Topic set is:

```text
effective_active_topics = topics where Topic.status == ACTIVE
                          and Unit.status == ACTIVE
```

A Topic under a removed Unit is therefore excluded even when the Topic row
itself remains `ACTIVE`.

Course progress is:

```text
course_progress = SEEN effective active Topics / all effective active Topics
```

Student progress is:

```text
student_progress = STUDIED effective active Topics / all effective active Topics
```

Catch-up progress is:

```text
catch_up_progress = SEEN_AND_STUDIED effective active Topics
                    / all SEEN effective active Topics
```

Academic gaps are:

```text
academic_gaps = effective active Topics where course_progress_status == SEEN
                and student_status != STUDIED
```

Assessment preparation coverage is:

```text
assessment_preparation_coverage = STUDIED effective active assessment Topics
                                  / all effective active assessment Topics
```

Only effective active Topics participate in these metrics. Only `STUDIED`
counts as completed. A metric with a zero denominator returns `null`.

## 10. Domain invariants

- Every Faculty belongs to exactly one University.
- Every Career belongs to exactly one Faculty.
- Every StudyPlan belongs to exactly one Career.
- StudyPlanCourse, not Course, represents a Course's placement in a StudyPlan.
- Every CourseOffering belongs to one StudyPlanCourse and identifies a specific chair or section and academic period or year.
- Students share academic structure only within the same CourseOffering.
- Every Topic belongs to exactly one Unit.
- Every Subtopic belongs to exactly one Topic.
- Units and Topics marked `REMOVED` are preserved rather than physically deleted.
- Topics under a `REMOVED` Unit are excluded from effective active Topic metrics.
- Units, Topics, and Subtopics originate in supplied academic sources and require validation before confirmation.
- AI never writes directly into the confirmed academic domain.
- AI never invents Subtopics from general model knowledge.
- UserCourse is historical; CourseEnrollment represents one concrete attempt.
- CourseEnrollment status is limited to `IN_PROGRESS`, `PASSED`, and `FAILED` in V0.1.
- The User manually controls actual course progress and personal study state.
- StudyAI never automatically changes `student_status`.
- The User may move freely between student states, including backwards.
- `STUDIED` does not imply Practice or Mastery.
- StudySessions and PracticeSessions never automatically change `student_status`.
- Schedule dates are plans and never automatically mark Topics as `SEEN`.
- Removing a Topic never discards existing personal state.
- `last_studied_at` and progress metrics are derived, not separately stored sources of truth.
- Practice and Progress are independent.
- Mastery is outside V0.1.

## 11. Out-of-scope states and concepts

The following are explicitly outside V0.1:

- `RETAKING` as a CourseEnrollment status;
- `DROPPED` as a CourseEnrollment status;
- Mastery;
- automatic state transitions based on schedules, StudySessions, or PracticeSessions;
- AI-generated confirmed academic structure without validation;
- Subtopics invented from general model knowledge.
