# StudyAI — Domain

**Status:** Draft

This document defines StudyAI's main domain concepts, their relationships, and the business rules that must be preserved.

It does not define endpoints, tables, frameworks, or implementation details.

---

## 1. User

`User` represents a person who uses StudyAI.

The primary User is a University student.

The model must remain open to other User types.

Possible future examples:

- student;
- teacher;
- administrator;
- other academic roles.

The domain must not assume that every `User` will always be exclusively a student.

---

## 2. University

`University` represents a University institution.

Universities form a centralized academic catalog shared by all Users. The catalog
must support institutions from any country; initial validation and testing focus
on Argentine institutions without restricting the model to Argentina.

A University has:

- an automatically generated integer identifier;
- a required name, stored with its original capitalization and normalized
  whitespace;
- a required uppercase ISO 3166-1 alpha-2 country code.

University names must be unique within a country when compared without regard to
case or trivial whitespace differences. Country-code validation in V0.1 verifies
the two-letter format; maintaining a separate country registry is not required.

Examples:

- University of Buenos Aires;
- National University of La Plata;
- National Technological University.

A University may contain multiple Faculties or academic units.

Relationship:

```text
University
    1
    │
    └─── *
       Faculty
```

---

## 3. Faculty

`Faculty` represents a Faculty or academic unit belonging to a University.

A `Faculty` always belongs to a `University`.

A Faculty may offer multiple Careers.

Relationship:

```text
University
    │
    ▼
Faculty
    │
    ▼
Career
```

---

## 4. Career

`Career` represents a University degree program.

Examples:

- Computer Engineering;
- Civil Engineering;
- Bachelor's Degree in Economics.

A Career belongs to a Faculty.

A Career may have multiple StudyPlans over time.

Relationships:

```text
Faculty
   1
   │
   └─── *
      Career
```

and:

```text
Career
   1
   │
   └─── *
     StudyPlan
```

---

## 5. StudyPlan

`StudyPlan` represents a specific version of a Career's curriculum.

It must be identifiable through attributes such as:

- name;
- year;
- version.

Examples:

- Plan 2020;
- Plan 2023;
- Plan 2026.

The same Career may have multiple StudyPlans.

A StudyPlan belongs to exactly one Career.

---

## 6. Course

`Course` represents an academic Course as an independent concept.

Examples:

- Mathematical Analysis II;
- Physics I;
- Algorithms and Programming;
- Databases.

`Course` does not represent a User's academic state.

Therefore, information such as:

- approved;
- active;
- future;
- `final_grade`;

does NOT belong directly to `Course`.

The same Course may appear in multiple StudyPlans.

---

## 7. StudyPlanCourse

`StudyPlanCourse` represents the occurrence of a Course within a specific StudyPlan.

This concept must be distinguished from `Course` because the same Course may belong to different StudyPlans.

This relationship may contain StudyPlan-specific information such as:

- Course code;
- recommended year;
- recommended semester/term;
- position within the StudyPlan;
- other characteristics specific to that StudyPlan.

Relationship:

```text
StudyPlan
    │
    ▼
StudyPlanCourse
    │
    ▼
Course
```

This allows:

```text
Course: Mathematical Analysis II
```

to appear in:

```text
Plan 2020
Plan 2023
Plan 2026
```

without creating three conceptually different Courses.

---

## 8. UserCareer

`UserCareer` represents the relationship between a User and a Career.

It is necessary because a User may be enrolled in more than one Career at the same time.

Example:

```text
User
 ├── Computer Engineering
 └── Bachelor's Degree in Mathematics
```

Each relationship may be associated with a specific StudyPlan.

Therefore, a User may simultaneously have:

```text
Career A
→ StudyPlan A

Career B
→ StudyPlan B
```

The model must not assume that a User can have only one Career.

---

## 9. UserCourse

`UserCourse` represents the academic relationship between a User and a Course.

This concept contains information belonging to the student's personal academic history, not to the Course.

For example:

- CourseStatus;
- `final_grade`;
- future information related to the User's personal Course activity.

Relationship:

```text
User
   │
   ▼
UserCourse
   │
   ▼
Course
```

---

## 10. CourseStatus

The `UserCourse` relationship may have one of these states:

### approved

A `UserCourse with status == approved` represents a Course the User took and passed.

### active

A `UserCourse with status == active` represents a Course the User is currently taking.

### future

A `UserCourse with status == future` represents a Course that belongs to the User's academic journey but has not yet been taken.

CourseStatus belongs exclusively to `UserCourse`.

For example:

```text
Course:
Mathematical Analysis II
```

may be represented as:

```text
UserCourse for User A: status == approved
UserCourse for User B: status == active
UserCourse for User C: status == future
```

The Course itself has no CourseStatus.

---

## 11. final_grade

`final_grade` represents the definitive grade earned by the User in a Course.

It belongs to `UserCourse`.

### Invariant

A `final_grade` may exist ONLY when:

```text
UserCourse.status == approved
```

Therefore:

```text
UserCourse with status == approved
+ final_grade
→ valid
```

but:

```text
UserCourse with status == active
+ final_grade
→ invalid
```

and:

```text
UserCourse with status == future
+ final_grade
→ invalid
```

The exact grading scale is not yet defined globally because it may vary between institutions.

---

## 12. Assessment

The domain must distinguish `final_grade` from grades earned during a Course.

`Assessment` represents an evaluation instance.

Examples:

- midterm;
- make-up exam;
- practical assignment;
- exam;
- another evaluation instance.

An Assessment may have:

- date;
- type;
- result;
- grade;
- associated Course.

Partial grades must belong to these instances and must not be confused with `final_grade`.

---

## 13. Assessment timing rule

A User cannot record a grade for an Assessment that has not yet occurred.

If:

```text
assessment.date > current_date
```

then:

```text
assessment.grade
```

cannot exist yet.

The Assessment itself may exist in advance to represent a future date.

Valid example before the exam:

```text
Midterm 1
Date: 10/17
Grade: null
```

After the Assessment has occurred:

```text
Midterm 1
Date: 10/17
Grade: 8
```

---

## 14. Rules for UserCourse with status == future

A `UserCourse with status == future` represents a Course the User has not yet taken.

For this UserCourse:

- `final_grade` cannot exist;
- personal partial grades cannot exist;
- completed Course activity cannot be recorded;
- topics must not be loaded as part of the User's personal tracking.

The system may know institutional information about the Course.

For example:

- name;
- code;
- StudyPlan position;
- suggested year.

But the User does not yet have active academic tracking for it.

---

## 15. Topics

`Topic` represents an academic topic belonging to Course content.

Examples:

```text
Mathematical Analysis II
├── Topology
├── Partial derivatives
├── Differentiability
└── Implicit functions
```

Topics are a central part of the domain. Their implementation scope is defined by the applicable release document.

### Initial rule

Topic tracking must exist only for UserCourse relationships where the User has started taking the Course.

A `UserCourse with status == future` must not contain personal Topic activity.

---

## 16. CoursePace

`CoursePace` represents how far a Course has currently advanced.

Example:

```text
Course: Mathematical Analysis II

Last topic covered:
Implicit functions
```

It must not be confused with the User's personal Progress.

---

## 17. Progress

`Progress` represents the User's personal advancement through Course content.

Initially, it is understood as exposure to and work on academic content.

For example:

- attended the lecture;
- reviewed the content;
- studied the theory.

`Progress` does not mean Mastery.

Its formal definition must be specified before implementing the corresponding version.

---

## 18. Practice

`Practice` represents the User's practical activity.

In the future, it may consider:

- completed exercises;
- correct exercises;
- incorrect exercises;
- retries;
- results;
- comments;
- difficulties.

It must not be confused with theoretical Progress or Mastery.

---

## 19. Mastery

`Mastery` represents a User's level of consolidated understanding of a topic.

It must consider the connection between:

- theoretical understanding;
- practical application.

A User may have:

```text
high Progress
+
little Practice
+
low Mastery
```

These concepts must remain independent.

---

## 20. Main relationships

The initial conceptual model can be visualized as:

```text
University
    │
    ▼
Faculty
    │
    ▼
Career
    │
    ▼
StudyPlan
    │
    ▼
StudyPlanCourse
    │
    ▼
Course
```

On the User side:

```text
User
 │
 ├── UserCareer
 │       │
 │       ├── Career
 │       └── StudyPlan
 │
 └── UserCourse
         │
         ├── Course
         ├── CourseStatus
         └── final_grade
```

Additional UserCourse relationships:

```text
UserCourse
    │
    ├── Assessments
    ├── Topics
    ├── Progress
    ├── Practice
    └── Mastery
```

---

## 21. Initial invariants

The following rules must be treated as domain invariants:

### Academic structure

- a `Faculty` belongs to a `University`;
- a `Career` belongs to a `Faculty`;
- a `StudyPlan` belongs to a `Career`;
- a Course may appear in multiple StudyPlans;
- a User may be associated with multiple Careers;
- each UserCareer may use a different StudyPlan.

### UserCourse state

- CourseStatus belongs to `UserCourse`, not to `Course`;
- `final_grade` belongs to `UserCourse`, not to `Course`;
- a `final_grade` may exist only for a `UserCourse with status == approved`;
- a `UserCourse with status == future` cannot have a `final_grade`;
- a `UserCourse with status == future` cannot have personal partial grades;
- a `UserCourse with status == future` cannot record personal academic activity.

### Assessments

- a future Assessment may exist;
- a grade for a future Assessment cannot exist until the Assessment has occurred.

### Topic tracking by UserCourse status

- topics belong to UserCourse tracking where the User has started taking the Course;
- a `UserCourse with status == future` must not have personal Topic tracking.

---

## 22. Separation between institutional and personal information

A central domain distinction is between:

### Institutional information

Describes the academic system.

Examples:

- University;
- Faculty;
- Career;
- StudyPlan;
- Courses;
- codes;
- StudyPlan position.

### User information

Describes the User's relationship with that academic system.

Examples:

- enrolled Career;
- selected StudyPlan;
- CourseStatus;
- `final_grade`;
- Assessments;
- Progress;
- Practice;
- Mastery.

This separation must be preserved in future domain decisions.

---

## 23. Open questions

The following domain decisions remain open:

- global grade format;
- exact Assessment modeling;
- formal definition of Topic;
- Progress calculation;
- Practice calculation;
- Mastery calculation;
- formal representation of CoursePace;
- Course prerequisites;
- elective Courses;
- Course equivalencies;
- StudyPlan changes;
- Career changes;
- Courses shared between Careers.

These decisions must be resolved when the corresponding scope requires them.
