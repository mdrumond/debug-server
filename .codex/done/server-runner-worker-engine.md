# server-runner: worker engine and command execution lifecycle

- **ID**: T-004
- **Created**: 2024-07-30
- **Owner**: gpt-5-codex
- **Status**: Completed

## Goal
Implement the worker supervisor that spawns per-session processes, provisions Conda/virtualenvs, applies patches, executes commands, streams logs, and reports status via the metadata store. This is the heart of the execution service.

## Plan
1. Consume worktree + dependency leasing APIs from [`.codex/tasks/server-backend-worktree-and-session-cache.md`](server-backend-worktree-and-session-cache.md) to hydrate a workspace per session.
2. Build a worker supervisor module that launches subprocesses under resource limits, streams stdout/stderr incrementally, and reports command lifecycle events via the DB helpers from [`.codex/tasks/server-backend-sqlite-metadata-store.md`](server-backend-sqlite-metadata-store.md).
3. Implement environment sync hooks (pip/conda) with caching and log structured metadata for observability.
4. Provide gRPC/WebSocket-safe log stream abstraction for use by API + CLI tasks.

## Deliverables
- `debug_server/runner/supervisor.py`, `environment.py`, `log_stream.py`.
- Worker configuration files (e.g., `config/runner.toml`).
- Tests for runner lifecycle under `tests/runner/`.

## Tests & Examples
- **Test strategy:** Integration tests that spawn fake commands, plus unit tests for log streaming and patch application.
- **Commands to run tests:**
  ```bash
  pytest tests/runner
  pytest tests/integration/test_worker_supervisor.py
  ```
* **Examples (how to run/use the feature):**
  ```bash
  python -m debug_server.runner.supervisor --session 123
  python -m debug_server.runner.supervisor --dry-run --command "pytest"
  ```

## Linting & Quality
* **Commands to lint/format:**
  ```bash
  ruff check debug_server/runner
  black debug_server/runner
  ```
* **Static analysis / type checks:**
  ```bash
  mypy debug_server/runner
  ```

## Documentation Updates
* [`docs/runner.md`](../../docs/runner.md)
* [`.codex/spec.md`](../spec.md)

## Notes / Risks
* Need careful resource cleanup on crashes to prevent leaked processes.
* Worker needs to surface structured exit reasons for CLI + MCP.
* Provide hooks for debugger integration task (see [`.codex/tasks/server-runner-debugger-integration.md`](server-runner-debugger-integration.md)).

## Completion Notes

- Added the `debug_server.runner` package with environment provisioning,
  log streaming, and the `WorkerSupervisor` orchestration logic plus a default
  `config/runner.toml` layout.
- Documented the workflow in [`docs/runner.md`](../../docs/runner.md) and
  linked the implementation from [`.codex/spec.md`](../spec.md).
- Created unit tests covering environment cache invalidation, log
  subscriptions, supervisor behavior, and an integration test that exercises
  a real `WorktreePool` lease.
- Added regression coverage for command spawn failures to ensure the
  supervisor records a `FAILED` status and publishes the log artifact even
  when `subprocess.Popen` cannot start, verified via
  `python -m pytest tests/runner/test_supervisor.py`.
- Addressed follow-up review feedback by removing unused imports and
  delegating git repository bootstrapping in
  `tests/runner/test_supervisor.py` to the shared
  `tests.worktrees.conftest.init_git_repo` helper.
- Recorded test + lint runs for traceability:
  - `python -m pytest tests/runner`
  - `python -m pytest tests/integration/test_worker_supervisor.py`
  - `ruff check debug_server/runner tests/runner tests/integration/test_worker_supervisor.py`
  - `black --check debug_server/runner tests/runner tests/integration/test_worker_supervisor.py`
  - `mypy debug_server/runner`

## Completion Checklist
* [x] Code implemented
* [x] Tests written/updated and passing
* [x] Examples added/updated
* [x] Docs updated where needed
* [x] Linting/formatting clean
* [x] Review complete
* [x] **Move this file to** `.codex/done/` **when all boxes are checked**
