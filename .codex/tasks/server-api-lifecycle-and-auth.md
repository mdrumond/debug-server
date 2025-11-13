# server-api: lifecycle endpoints and bearer auth

- **ID**: T-006
- **Created**: 2024-07-30
- **Owner**: gpt-5-codex
- **Status**: Open

## Goal
Implement the FastAPI application surface for repository initialization, session lifecycle, command queueing, artifact downloads, and bearer-token authentication over HTTP/WebSocket, aligning with the architecture described in `.codex/spec.md`.

## Plan
1. Consume metadata helpers from [`.codex/tasks/server-backend-sqlite-metadata-store.md`](server-backend-sqlite-metadata-store.md) to implement repository + session routes.
2. Integrate with the worktree/runner orchestration (see [`.codex/tasks/server-runner-worker-engine.md`](server-runner-worker-engine.md)) to create/terminate sessions and dispatch commands.
3. Implement `HTTPBearer` auth, token management endpoints, and middleware for audit logging.
4. Provide OpenAPI schema + docs plus Pydantic models shared with CLI + MCP.

## Deliverables
- `debug_server/api/main.py`, `routers/repository.py`, `routers/sessions.py`, `routers/commands.py`.
- Shared Pydantic schemas under `debug_server/api/schemas.py`.
- Auth middleware utilities.

## Tests & Examples
- **Test strategy:** FastAPI APITestClient unit/integration tests that mock runner + DB layers.
- **Commands to run tests:**
  ```bash
  pytest tests/api
  ```
* **Examples (how to run/use the feature):**
  ```bash
  uvicorn debug_server.api.main:app --reload
  http --auth-type=bearer --auth="TOKEN" POST :8000/sessions commit=HEAD
  ```

## Linting & Quality
* **Commands to lint/format:**
  ```bash
  ruff check debug_server/api
  black debug_server/api
  ```
* **Static analysis / type checks:**
  ```bash
  mypy debug_server/api
  ```

## Documentation Updates
* [`README.md`](../../README.md)
* [`docs/api.md`](../../docs/api.md)
* [`.codex/spec.md`](../spec.md)

## Notes / Risks
* Need to ensure WebSocket upgrades share the same bearer token validation flow.
* Provide rate limiting/throttling hooks for future hardening.
* Expose health and readiness endpoints consumed by observability tasks.

## Completion Checklist
* [ ] Code implemented
* [ ] Tests written/updated and passing
* [ ] Examples added/updated
* [ ] Docs updated where needed
* [ ] Linting/formatting clean
* [ ] Review complete
* [ ] **Move this file to** `.codex/done/` **when all boxes are checked**
