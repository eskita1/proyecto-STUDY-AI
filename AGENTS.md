# StudyAI Agent Instructions

This file is the operational router for coding agents working in this repository.

## 1. Project and current release

StudyAI is an academic progress and study-planning system for university students.

The current release is `V0.1`.

The authoritative implementation scope is:

`docs/releases/v0.1.md`

Implement only what the current task and current release require.

## 2. Context routing

For every implementation task:
- read `AGENTS.md`;
- read `docs/releases/v0.1.md`.

Read additionally only when relevant:
- product behavior -> `docs/product.md`
- domain rules -> `docs/domain.md`
- backend architecture -> `docs/architecture.md`
- future release placement -> `docs/roadmap.md`
- architectural decisions -> relevant files in `docs/decisions/`

If source-of-truth documents conflict, do not guess. Report the conflict and identify the affected files.

## 3. Context and token efficiency

Context/token efficiency is mandatory.

- Read only files relevant to the task.
- Inspect targeted files and directories before broader searches.
- Do not scan the repository “just in case.”
- Do not reread context already understood during the same task.
- Reuse existing patterns instead of rediscovering documented behavior.
- Do not restate repository documentation unless the task requires it.

## 4. Release scope discipline

- Treat `docs/releases/v0.1.md` as the exclusive source of current scope.
- Do not implement future capabilities merely because they appear in product, domain, or roadmap documents.
- Do not expand scope, anticipate features, or add speculative support.
- Preserve explicit out-of-scope boundaries.

## 5. Essential backend rules

The dependency direction is:

```text
routes -> services -> repositories -> database
```

- Routes own HTTP concerns.
- Services own application logic and domain rules.
- Repositories own persistence access.
- Do not bypass layers without an explicit, documented reason.
- Read `docs/architecture.md` before backend structural changes.

Database work must use SQLAlchemy and Alembic.

- Do not make manual schema changes.
- Include a migration for schema changes.
- Do not rewrite migration history without explicit authorization.

## 6. Domain and decision boundaries

- Do not invent or silently change domain semantics.
- Read `docs/domain.md` before changing entities, relationships, ownership, state, or invariants.
- Preserve documented distinctions and business rules.
- - Do not make undocumented product, domain, architecture, persistence, API, or release-scope decisions.
- When a required decision is undefined, stop at that boundary and report the exact decision needed.
- Preserve completed work that does not depend on the unresolved decision.

## 7. Development principles

- Make the smallest correct change.
- Do not refactor unrelated code.
- Do not introduce premature abstractions or layers.
- Reuse reasonable existing patterns.
- Prefer explicit, readable code over clever designs.
- Add no dependency unless the current task concretely requires it.
- Inspect existing code before creating a new implementation.
- Do not weaken valid tests to make the suite pass.

## 8. Validation

For backend changes, run from `backend/`:

```bash
pytest
ruff check .
```

When useful, also run:

```bash
git diff --check
```

- Add or update tests when behavior changes.
- Run checks proportional to the change.
- Do not claim checks that were not executed.
- Do not consider a task complete when it knowingly breaks tests, Ruff, or CI.

## 9. Git and change discipline

- Keep changes localized and reviewable.
- Preserve existing user changes and unrelated work.
- Do not reset, overwrite, or delete work outside the task.
- Do not rewrite history, force-push, create branches, or switch branches unless requested.
- Do not commit virtual environments, secrets, caches, local databases, or temporary artifacts.
- Update only documentation owned by the behavior changed in the task.

## 10. Language

All source code, identifiers, tests, technical documentation, commit messages, and developer-facing text must be written in English. User-facing content may be localized independently.

## 11. Completion report

Keep the final report concise and include only:

- files created or modified;
- tests and checks executed;
- results;
- blockers or unresolved decisions.

Do not add a narrative unless requested.
