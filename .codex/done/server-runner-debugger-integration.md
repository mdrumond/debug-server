# server-runner: debugger orchestration and tunnels

- **ID**: T-005
- **Created**: 2024-07-30
- **Owner**: gpt-5-codex
- **Status**: Completed

## Goal
Extend the runner to launch debug sessions via `debugpy`, `gdb`, and `lldb`, expose remote control channels, and integrate with the metadata + API layers so clients can drive step/continue/variables interactions.

## Plan
1. Build debugger adapters that wrap the worker supervisor from [`.codex/tasks/server-runner-worker-engine.md`](server-runner-worker-engine.md), abstracting command start/stop with debugger flags.
2. Implement a tunnel manager that exposes DAP/WebSocket endpoints per session, authenticated via bearer tokens stored by [`.codex/tasks/server-backend-sqlite-metadata-store.md`](server-backend-sqlite-metadata-store.md).
3. Provide APIs/events consumed by server API tasks (see [`.codex/tasks/server-api-debug-streams.md`](server-api-debug-streams.md)) to control debugger lifecycle and stream variable snapshots/logs.
4. Document supported debuggers and add integration tests for Python (`debugpy`) plus mock tests for native debuggers.

## Deliverables
- `debug_server/runner/debuggers/__init__.py`, `debugpy_adapter.py`, `gdb_adapter.py`, `lldb_adapter.py`.
- Tunnel management utilities and config entries.
- Tests covering debugger flows.

## Tests & Examples
- **Test strategy:** Integration tests for debugpy flows; mocked unit tests for gdb/lldb command orchestration.
- **Commands to run tests:**
  ```bash
  pytest tests/runner/test_debugpy_adapter.py
  pytest tests/runner/test_debugger_tunnels.py
  ```
* **Examples (how to run/use the feature):**
  ```bash
  python -m debug_server.runner.debuggers.debugpy_adapter --session 123 --module app.main
  python -m debug_server.runner.debuggers.gdb_adapter --session 456 --binary ./a.out
  ```

## Linting & Quality
* **Commands to lint/format:**
  ```bash
  ruff check debug_server/runner/debuggers
  black debug_server/runner/debuggers
  ```
* **Static analysis / type checks:**
  ```bash
  mypy debug_server/runner/debuggers
  ```

## Documentation Updates
* [`docs/debugging.md`](../../docs/debugging.md)
* [`.codex/spec.md`](../spec.md)

## Notes / Risks
* Need to secure tunnel endpoints (auth + TTL) to avoid unauthorized debugger access.
* Provide fallback when host lacks native debuggers by surfacing clear errors.
* Coordinate port allocation with CLI + MCP so clients can attach reliably.

## Updates
- Adjusted debugger tunnel metadata to publish TCP URIs that match the adapters' raw socket listeners, preventing clients from
  attempting WebSocket upgrades on unavailable routes.
- Tests: `tests/runner/test_debugger_tunnels.py`.

## Completion Checklist
* [x] Code implemented
* [x] Tests written/updated and passing — `tests/runner/test_debugpy_adapter.py`, `tests/runner/test_debugger_tunnels.py`
* [x] Examples added/updated
* [x] Docs updated where needed
* [x] Linting/formatting clean
* [x] Review complete
* [x] **Move this file to** `.codex/done/` **when all boxes are checked**
