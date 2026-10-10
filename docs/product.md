# StudyAI Product

## Product vision

StudyAI helps university students understand the academic structure they share with their classmates, track their own progress and study activity, and organize practice and upcoming assessments without surrendering control of their academic state.

## Target user

The initial product is for university students enrolled in one or more concrete course offerings who need a reliable view of:

- what their course is expected to cover;
- what the course has actually covered;
- what they personally consider studied;
- what they have practiced;
- when they studied;
- which assessments are approaching.

## Core problem

Academic information is distributed across study plans, syllabi, schedules, theoretical material, practice material, and other documents. Students then maintain separate personal notes about what they have seen, studied, and practiced.

StudyAI brings those two kinds of information together while preserving the distinction between shared academic structure and each student's personal state.

## Value proposition

StudyAI provides a source-backed academic structure for each concrete course offering and lets each student maintain an independent record of progress, study sessions, and practice.

The product must make every important state understandable and user-controlled. It must not infer that a topic was covered merely because it was scheduled, infer that a student studied merely because a session was recorded, or treat practice as proof of progress or mastery.

## Product model

### Institutional structure

The institutional hierarchy is:

```text
University -> Faculty -> Career -> StudyPlan -> StudyPlanCourse
```

`Course` is an abstract course concept. `StudyPlanCourse` represents that Course in one specific StudyPlan.

### Concrete academic delivery

The structure used by students begins with a concrete delivery:

```text
StudyPlanCourse -> CourseOffering -> Unit -> Topic -> Subtopic
```

A `CourseOffering` identifies a specific chair or section in a specific academic period or year. Students share Units, Topics, Subtopics, schedules, and assessments only when they belong to the same CourseOffering.

### Source-backed structure

Students do not freely create or edit Units, Topics, or Subtopics. The academic structure comes from materials supplied by the User, chair, or University.

StudyAI may use AI to extract and propose structure, but the confirmed academic domain is reached only through this flow:

```text
source -> extraction -> proposed structure -> validation -> confirmed domain
```

AI must never write directly into the confirmed academic domain. It must not invent Subtopics from general model knowledge.

### Personal academic history

The User's personal relationships are:

```text
User -> UserCareer
User -> UserCourse -> CourseEnrollment -> EnrollmentTopic
```

`UserCourse` is the historical relationship between the User and a StudyPlanCourse. `CourseEnrollment` is one concrete attempt in a CourseOffering. `EnrollmentTopic` stores the User's own state for a Topic during that attempt.

## User-controlled progress

Two independent Topic states are visible to the User:

- actual course progress: whether the Topic has been seen in the CourseOffering;
- personal study state: whether the User has not started, is studying, or considers the Topic studied.

The User manually controls both states. StudyAI must not automatically change personal study state.

The User may move freely between personal study states, including backwards. `STUDIED` means only that the User considers the Topic studied; it does not imply practice or mastery.

Scheduled dates are plans and do not automatically mean that a Topic was seen. If confirmed academic content is later marked as removed, the User's existing personal state remains available.

## Study activity

Students can record StudySessions against a CourseEnrollment and associate them with one or more Topics.

Study sessions support:

- quick mode, with a start time and no end time;
- full mode, with both start and end times.

Recording a StudySession does not automatically change any Topic's personal study state. The most recent study time is derived from recorded sessions rather than stored as separate mutable state.

## Practice

Practice is recorded independently from course progress and personal study state.

Students can use:

- quick mode, with aggregate counts for total, correct, partially correct, and incorrect exercises;
- detailed mode, with individual PracticeExercises and their results.

Recording practice must not automatically change personal study state. Mastery is a separate concept and is not part of V0.1.

## Time and assessments

CourseScheduleItems express the planned timing and order of Units or Topics for a CourseOffering. A scheduled date represents a plan, not confirmation that the content was covered.

Assessments belong to a CourseOffering and may be associated with Topics. V0.1 supports midterms, finals, recovery assessments, assignments, quizzes, and other assessment types.

## Progress metrics

V0.1 presents metrics derived from confirmed academic structure and User-controlled state:

- course progress: seen active Topics divided by all active Topics;
- student progress: studied active Topics divided by all active Topics;
- catch-up progress: Topics that are both seen and studied divided by all seen Topics.

These metrics are derived views, not independently editable sources of truth.

## Product principles

- Preserve the distinction between institutional structure, a concrete CourseOffering, and personal student state.
- Share academic structure only among students in the same CourseOffering.
- Require source-backed, validated academic structure.
- Use AI to propose, never to silently confirm academic truth.
- Keep actual course progress, personal study state, Study, Practice, and Mastery separate.
- Keep the User in control of actual course progress and personal study state.
- Treat schedules as plans rather than evidence of completed events.
- Preserve historical and personal state when confirmed content is removed.
- Derive metrics from authoritative records instead of duplicating mutable state.

## V0.1 boundaries

V0.1 includes institutional structure, CourseOfferings, source-backed academic structure, personal enrollment and Topic state, StudySessions, PracticeSessions, schedules, assessments, and derived progress metrics.

V0.1 does not include:

- automatic changes to personal study state;
- AI writes directly to confirmed academic structure;
- AI-generated Subtopics based on general model knowledge;
- `RETAKING` or `DROPPED` enrollment states;
- Mastery;
- treating scheduled content as automatically seen.

## Success criteria

StudyAI V0.1 succeeds when a student can identify their concrete CourseOffering, inspect a validated source-backed structure, manually represent both course and personal progress, record study and practice without hidden state changes, view planned content and assessments, and understand how every displayed progress metric was derived.
