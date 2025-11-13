# server-api: debug control and streaming endpoints

- **ID**: T-007
- **Created**: 2024-07-30
- **Owner**: gpt-5-codex
- **Status**: Open

## Goal
Expose WebSocket endpoints and REST hooks that let clients open debugger sessions, send control commands (step, continue, eval), and stream logs/variables, backed by the runner debugger adapters.

## Plan
1. Extend the FastAPI app from [`.codex/tasks/server-api-lifecycle-and-auth.md`](server-api-lifecycle-and-auth.md) with WebSocket routers for `/sessions/{id}/debug` and `/sessions/{id}/logs`.
2. Integrate with debugger adapters delivered in [`.codex/tasks/server-runner-debugger-integration.md`](server-runner-debugger-integration.md) to bridge API events to runner commands.
3. Provide streaming codecs (JSON, chunked text) and enforce bearer authentication per connection.
4. Document protocol semantics for CLI + MCP implementers.

## Deliverables
- `debug_server/api/routers/debug.py`, `routers/logs.py`.
- Shared schema docs and streaming protocol description.
- Tests using FastAPI WebSocket test client.

## Tests & Examples
- **Test strategy:** Async integration tests for WebSocket routes + unit tests for serialization helpers.
- **Commands to run tests:**
  ```bash
  pytest tests/api/test_debug_ws.py
  pytest tests/api/test_log_streams.py
  ```
* **Examples (how to run/use the feature):**
  ```bash
  websocat -H "Authorization: Bearer TOKEN" ws://localhost:8000/sessions/123/debug
  http --auth-type=bearer --auth="TOKEN" GET :8000/sessions/123/logs
  ```

## Linting & Quality
* **Commands to lint/format:**
  ```bash
  ruff check debug_server/api/routers
  black debug_server/api/routers
  ```
* **Static analysis / type checks:**
  ```bash
  mypy debug_server/api/routers
  ```

## Documentation Updates
* [`docs/debugging.md`](../../docs/debugging.md)
* [`docs/api.md`](../../docs/api.md)
* [`.codex/spec.md`](../spec.md)

## Notes / Risks
* Need to enforce per-session authorization so clients cannot attach to others' sessions.
* Streaming endpoints must gracefully handle runner restarts.
* Provide metrics instrumentation for observability.

## Completion Checklist
* [ ] Code implemented
* [ ] Tests written/updated and passing
* [ ] Examples added/updated
* [ ] Docs updated where needed
* [ ] Linting/formatting clean
* [ ] Review complete
* [ ] **Move this file to** `.codex/done/` **when all boxes are checked**
