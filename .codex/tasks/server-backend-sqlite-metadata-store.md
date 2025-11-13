# server-backend: sqlite metadata store and SQLModel schema

- **ID**: T-002
- **Created**: 2024-07-30
- **Owner**: gpt-5-codex
- **Status**: Open

## Goal
Design and implement the SQLite + SQLModel persistence layer that tracks repositories, worktrees, sessions, commands, artifacts, auth tokens, and debugger state. This backs the FastAPI services and runner components described elsewhere.

## Plan
1. Using the bootstrap artifacts from [`.codex/tasks/bootstrap-environment-and-repo-sync.md`](bootstrap-environment-and-repo-sync.md), create the SQLModel models and Alembic migrations for all metadata tables outlined in `.codex/spec.md`.
2. Implement a persistence service module that provides CRUD helpers plus transactional APIs (e.g., reserve worktree, record command logs, store artifact metadata) with optimistic locking safeguards.
3. Add seed scripts for initial admin account/token generation and CLI utilities for migrations.
4. Provide fixtures/mocks for server-backend consumers (API + runner tasks) so they can test without hitting the real DB.

## Deliverables
- `debug_server/db/models.py`, `debug_server/db/session.py`, `debug_server/db/migrations/`.
- Management commands such as `python -m debug_server.db.migrate upgrade`.
- Fixtures for tests under `tests/db/`.

## Tests & Examples
- **Test strategy:** Unit tests for models + integration tests covering migrations and transactional helpers.
- **Commands to run tests:**
  ```bash
  pytest tests/db
  pytest tests/integration/test_db_transactions.py
  ```
* **Examples (how to run/use the feature):**
  ```bash
  python -m debug_server.db.migrate upgrade head
  python -m debug_server.db.admin create-token --user ops
  ```

## Linting & Quality
* **Commands to lint/format:**
  ```bash
  ruff check debug_server/db
  black debug_server/db
  ```
* **Static analysis / type checks:**
  ```bash
  mypy debug_server/db
  ```

## Documentation Updates
* [`README.md`](../../README.md)
* [`.codex/spec.md`](../spec.md)
* [`docs/architecture.md`](../../docs/architecture.md) (create if missing to explain DB schema)

## Notes / Risks
* Ensure SQLite pragmas support WAL mode for concurrent runners.
* Later Postgres support should remain possible (avoid SQLite-only syntax).
* Provide DB health-check endpoints for observability task (see [`.codex/tasks/observability-pipeline.md`](observability-pipeline.md)).

## Completion Checklist
* [ ] Code implemented
* [ ] Tests written/updated and passing
* [ ] Examples added/updated
* [ ] Docs updated where needed
* [ ] Linting/formatting clean
* [ ] Review complete
* [ ] **Move this file to** `.codex/done/` **when all boxes are checked**
