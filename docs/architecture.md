# StudyAI — Architecture

**Status:** Draft

This document defines StudyAI's initial technical architecture.

Its purpose is to describe how the backend is organized, the responsibility of each layer, permitted dependencies, and the principles that must be followed during development.

It does not define product requirements or specific business rules. Those concepts belong in `product.md`, `domain.md`, and release documents.

---

## 1. Architecture goals

The initial architecture must prioritize:

- clarity;
- simplicity;
- low coupling;
- separation of responsibilities;
- testability;
- maintainability;
- ease of understanding for humans and agents;
- the ability to evolve without early overengineering.

It must be structured enough to avoid mixing responsibilities without introducing abstractions that do not yet provide real value.

---

## 2. Initial technical stack

The backend uses:

- Python;
- FastAPI;
- Uvicorn;
- PostgreSQL;
- SQLAlchemy;
- Alembic;
- Pydantic;
- Pydantic Settings;
- pytest;
- HTTPX;
- Ruff;
- GitHub Actions.

This document defines the backend architecture. Current release scope is defined in `docs/releases/v0.1.md`.

---

## 3. General backend structure

The expected initial structure is:

```text
backend/
├── app/
│   ├── main.py
│   ├── database/
│   │   ├── __init__.py
│   │   └── db.py
│   ├── models/
│   │   └── __init__.py
│   ├── schemas/
│   │   └── __init__.py
│   ├── repositories/
│   │   └── __init__.py
│   ├── services/
│   │   └── __init__.py
│   └── routes/
│       └── __init__.py
├── tests/
├── requirements.txt
├── requirements-dev.txt
└── pytest.ini
```

The structure may evolve when real needs arise, but it must not grow in anticipation.

---

## 4. Main request flow

The normal HTTP request flow must be:

```text
Client
  ↓
Route
  ↓
Service
  ↓
Repository
  ↓
SQLAlchemy
  ↓
PostgreSQL
```

The response returns in reverse order. Each layer must keep a clear responsibility.

---

## 5. Routes

The `routes` layer is the system's HTTP boundary.

Responsibilities:

- define endpoints;
- receive parameters and request bodies;
- use input schemas;
- invoke services;
- transform results into HTTP responses;
- return appropriate HTTP status codes;
- expose errors consistently.

Routes must not contain SQL, access PostgreSQL directly, implement complex business rules, know internal persistence details, or duplicate domain validation.

Conceptual example:

```text
POST /courses
      ↓
route
      ↓
course_service.create_course(...)
```

Routes must remain thin.

---

## 6. Services

The `services` layer contains application and business logic.

It applies domain rules, validates invariants, coordinates repositories, decides whether operations are allowed, runs multi-entity flows, and keeps logic independent from HTTP.

Examples include allowing `final_grade` only for a UserCourse with an `approved` CourseStatus, disallowing personal academic activity for a UserCourse with a `future` CourseStatus, disallowing a grade for a future Assessment, and requiring a Faculty to belong to a valid University.

Services must not return HTTP-specific objects, choose HTTP status codes, contain SQL, or know unnecessary web-framework details.

```text
CourseService
    ↓
checks business rules
    ↓
CourseRepository
```

---

## 7. Repositories

The `repositories` layer encapsulates data access: queries, record creation, updates, deletion, entity retrieval, SQLAlchemy interaction, and persistence-specific handling.

Repositories must not contain business rules, decide academic validity, know HTTP, return HTTP status codes, or make product decisions.

```text
UserCourseRepository
    ↓
SQLAlchemy query
    ↓
PostgreSQL
```

---

## 8. Database

The `database` layer contains persistence configuration: engine configuration, session configuration, PostgreSQL connection, and helpers strictly related to database infrastructure.

It must not contain business logic, endpoints, domain decisions, or product validation.

---

## 9. Models

`models` represent persistent structures through SQLAlchemy. Initial examples are User, University, Faculty, Career, StudyPlan, Course, StudyPlanCourse, UserCareer, and UserCourse.

A model represents persistence and must not be confused with an input schema, response schema, business logic, or view model.

Models may represent columns, relationships, structural constraints, keys, and foreign keys. Complex business rules must not depend exclusively on database constraints.

---

## 10. Schemas

`schemas` represent data contracts. They validate request bodies, define responses, separate external data from internal models, and prevent direct exposure of SQLAlchemy models.

Create different schemas when useful:

```text
CourseCreate
CourseUpdate
CourseRead
```

Multiple schemas are not mandatory without a real difference. Avoid redundant schema definitions created only to follow a pattern.

---

## 11. Model / Schema separation

```text
Model
→ how data is persisted

Schema
→ what data enters or leaves the API
```

```text
Course SQLAlchemy Model
        ≠
CourseCreate Pydantic Schema
        ≠
CourseRead Pydantic Schema
```

This allows persistence to evolve without directly coupling it to the HTTP contract.

---

## 12. Permitted dependencies between layers

Expected flow:

```text
routes → services → repositories → database / models
routes → schemas
services → domain concepts → repositories
```

Avoid:

```text
routes → database directly
routes → SQLAlchemy queries
repositories → routes
repositories → HTTPException
models → routes
```

---

## 13. Domain rules

Invariants from `domain.md` must be applied primarily in services and checked before persistence.

```text
UserCourse.status == approved → final_grade allowed
UserCourse.status == future → no personal Assessment grades
```

The database may reinforce invariants with constraints when reasonable, but must not be the only place where important domain logic is expressed.

---

## 14. Errors

Repositories may detect technical failures such as missing records, constraint violations, or persistence conflicts. Services interpret the problem in domain terms, such as `Course not found` or `final_grade is not allowed for a UserCourse with an active CourseStatus`. Routes transform those results into appropriate responses such as 404, 409, or 422.

Do not use `HTTPException` in repositories, and ideally not in services when that would couple logic too tightly to FastAPI.

---

## 15. Persistence

PostgreSQL is the primary database. SQLAlchemy must be the ORM/persistence-access layer.

Do not use direct SQL without a concrete, documented reason. Any future direct SQL must remain in a repository or persistence-infrastructure layer.

---

## 16. Migrations

Alembic must be the primary mechanism for changing the database schema. Creating tables, adding columns or relationships, and changing constraints must be represented by versioned migrations committed to Git.

Do not use `create_all()` as the main schema-evolution strategy. It may be used temporarily in tests for an explicit reason, but must not replace Alembic in the normal environment.

---

## 17. Configuration

Sensitive or environment-dependent configuration must come from environment variables, such as `DATABASE_URL` and `APP_ENV`.

Real values must be stored locally in `.env`; the repository must include a secret-free `.env.example`. Pydantic Settings may centralize and validate configuration.

Do not hardcode passwords, production URLs, credentials, secrets, or tokens.

---

## 18. Testing

Tests are part of the architecture and project harness. Initially, verify relevant behavior rather than maximizing coverage metrics.

Tests may progressively be divided into `tests/unit/` and `tests/integration/`, but this separation is unnecessary until enough volume exists. Unit tests are useful for business rules, isolated functions, and services. Integration tests are useful for endpoints, repositories, persistence, and interactions between layers.

---

## 19. Domain tests

Important invariants must have explicit tests. Current applicable examples include:

```text
UserCourse.status == approved + final_grade → valid
UserCourse.status == active + final_grade → invalid
UserCourse.status == future + final_grade → invalid
```

Assessment timing tests apply when Assessment enters the applicable release scope.

The intent is to turn domain rules into verifiable behavior.

---

## 20. Linting

Ruff is the initial static-analysis tool and must run with `ruff check .`.

Do not introduce multiple tools covering the same problem without a clear need. Black, mypy, Pyright, Bandit, or other tools may be evaluated later.

---

## 21. CI

GitHub Actions must run, at minimum:

```text
install dependencies
        ↓
pytest
        ↓
ruff check .
```

The same commands must work locally. CI must not use a completely different flow, and a change should not be considered complete if it breaks CI.

---

## 22. Main application

`app/main.py` must remain small. It creates the FastAPI instance, registers routers, holds strictly necessary global configuration, and adds lifecycle hooks when needed.

It must not become a collection point for business logic, database access, endpoint implementations, or unrelated configuration.

---

## 23. Organization by entity

Early versions may use a simple layered organization:

```text
routes/courses.py
services/courses.py
repositories/courses.py
schemas/courses.py
models/course.py
```

This is easy to understand while the project is small. Feature- or domain-based organization may be evaluated if the system grows substantially; do not migrate preemptively.

---

## 24. Imports and internal dependencies

Internal dependencies must follow the architectural flow:

```text
routes/courses.py → imports CourseService
services/courses.py → imports CourseRepository
```

Incorrect:

```text
routes/courses.py → imports database session → performs query
```

Dependencies must be visible and easy to follow.

---

## 25. Transactions

Transactions must remain simple. The layer managing commits and rollbacks must be defined consistently; each file must not decide independently when to commit.

As an initial principle, repositories perform persistence operations and services coordinate units of work. Exact commit management must remain consistent. If meaningful alternatives arise, the session and commit pattern may be documented in an ADR.

---

## 26. Async vs Sync

Do not introduce async programming only because FastAPI supports it. The backend may use a synchronous flow if that simplifies SQLAlchemy, testing, debugging, learning, and maintenance.

The architecture may migrate to async only for a concrete need. Consistency is more important than mixing styles.

---

## 27. Dependency Injection

FastAPI `Depends` may be used for infrastructure dependencies such as database sessions, configuration, and future authentication dependencies.

Do not build a custom dependency-injection framework. Keep it simple.

---

## 28. Serialization

Responses must use Pydantic schemas when they help control exposed fields, avoid returning internal details, document OpenAPI correctly, and maintain stable contracts.

Do not return uncontrolled database structures directly.

---

## 29. Validation

Structural validation belongs mainly in schemas and covers required fields, incorrect types, and empty strings.

Domain validation belongs mainly in services, for example disallowing `final_grade` for a UserCourse with an `active` CourseStatus.

Persistence validation may be reinforced through the database, for example valid foreign keys and unique constraints.

Do not mix these three levels.

---

## 30. OpenAPI / Swagger

FastAPI must maintain usable OpenAPI documentation. Schemas, responses, and status codes must allow the API to be tested through Swagger.

Exhaustive manual documentation for every endpoint is not required unless the applicable release scope requires it, but contracts must be clear.

---

## 31. Security

Authentication scope is defined in the applicable release document. Regardless of scope, do not store secrets in Git; validate inputs; avoid unsafe SQL; do not expose sensitive internal details; and do not blindly trust external data.

When authentication is added, it must be documented through a specific decision.

---

## 32. Logging

Use standard logging when needed. Do not add external logging frameworks without a concrete need.

Logs must help explain errors, operational state, and technical failures. They must not replace error handling.

---

## 33. External dependencies

Before adding a dependency, confirm a concrete need. Consider whether the current stack can solve the problem reasonably, whether the dependency reduces real complexity, whether it adds unnecessary maintenance, whether it is stable and widely used enough, and whether the problem is current or hypothetical.

Avoid dependencies added “just in case.”

---

## 34. Simplicity principle

Given two correct implementations, prefer the one that is easier to understand and maintain.

Do not introduce unnecessary interfaces, factories, extra layers, redundant wrappers, enterprise patterns without a concrete problem, or generic repositories without current value.

The goal is a clear system, not demonstrating a large number of patterns.

---

## 35. Consistency principle

Before introducing a new solution, review how similar problems are solved in the repository. Agents must prefer reasonable existing patterns.

If an existing pattern must change, do so deliberately and document it.

---

## 36. Localized-change principle

A task must modify the smallest reasonable surface of the system. Avoid unrelated refactors within a feature.

This reduces risk, conflicts, PR size, agent context consumption, and review difficulty.

---

## 37. Architecture and agents

The architecture must be understandable to coding agents. An agent should quickly determine where to add an endpoint, business rule, query, schema, or test.

`AGENTS.md` must reference this document for architecture or backend implementation tasks. The full architecture should not need to be repeated in every prompt.

---

## 38. Architectural changes

A change is architectural when it significantly affects layer flow, general project structure, persistence strategy, transaction management, configuration strategy, component contracts, or core technology.

Such changes must not happen silently during feature work. When necessary, document them as architectural decisions under `docs/decisions/`.

---

## 39. ADRs

`docs/decisions/` stores Architecture Decision Records. Future examples include `001-sync-sqlalchemy.md`, `002-authentication-strategy.md`, and `003-course-identity.md`.

Use an ADR for a significant decision with real alternatives. Do not create ADRs for trivial decisions.

---

## 40. Current architectural exclusions

Do not yet implement:

- microservices;
- event-driven architecture;
- message brokers;
- Redis;
- Celery;
- CQRS;
- event sourcing;
- GraphQL;
- Kubernetes;
- multiple databases;
- service mesh;
- distributed architecture.

Consider these technologies only when a real need appears.

---

## 41. Responsibility summary

```text
ROUTES
HTTP

SERVICES
business/application logic

REPOSITORIES
persistence operations

MODELS
database representation

SCHEMAS
API data contracts

DATABASE
connection and persistence infrastructure

TESTS
behavior verification

MIGRATIONS
database schema evolution
```

---

## 42. Main architecture rule

```text
HTTP
 ↓
Route
 ↓
Service
 ↓
Repository
 ↓
Database
```

Business rules must remain in services. Data access must remain in repositories. Routes must remain thin.

If an implementation breaks this separation, there must be an explicit, documented reason.

---

## 43. Criterion for evaluating new decisions

For every new technical decision, ask:

> Does this make StudyAI clearer, more verifiable, and easier to evolve for the problem that exists today?

If the answer depends mainly on hypothetical future needs, the decision should probably be postponed.
