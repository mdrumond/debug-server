# server-backend: worktree manager and session cache

- **ID**: T-003
- **Created**: 2024-07-30
- **Owner**: gpt-5-codex
- **Status**: Completed

## Goal
Provide the repository lifecycle services that manage the bare mirror, git worktree pool, dependency caches, and session lifecycle metadata so runner tasks can rapidly prepare isolated workspaces.

## Plan
1. Build a `debug_server/worktrees` module that initializes the bare repo (using bootstrap scripts) and maintains a pool of worktrees keyed by commit/branch, referencing metadata stored via [`.codex/tasks/server-backend-sqlite-metadata-store.md`](server-backend-sqlite-metadata-store.md).
2. Implement eviction + cleanup policies (LRU, TTL) and concurrency-safe leasing semantics for sessions.
3. Integrate dependency cache hashing (pip/conda lockfiles) to trigger environment sync only when needed, exposing APIs consumed by server-runner tasks.
4. Add CLI/admin commands to inspect pool health and reclaim leaked worktrees.

## Deliverables
- `debug_server/worktrees/__init__.py`, `pool.py`, `dependency_sync.py`.
- Tests + fixtures under `tests/worktrees/`.
- Admin utilities under `python -m debug_server.worktrees.inspect`.

## Tests & Examples
- **Test strategy:** Unit tests for leasing logic + integration tests that run against a temporary git repo to simulate sessions.
- **Commands to run tests:**
  ```bash
  pytest tests/worktrees
  pytest tests/integration/test_session_cache.py
  ```
* **Examples (how to run/use the feature):**
  ```bash
  python -m debug_server.worktrees.inspect --show-active
  python -m debug_server.worktrees.reclaim --older-than 1h
  ```

## Linting & Quality
* **Commands to lint/format:**
  ```bash
  ruff check debug_server/worktrees
  black debug_server/worktrees
  ```
* **Static analysis / type checks:**
  ```bash
  mypy debug_server/worktrees
  ```

## Documentation Updates
* [`docs/worktrees.md`](../../docs/worktrees.md)
* [`.codex/spec.md`](../spec.md)

## Notes / Risks
* Ensure git commands are safe against partial patches and validate with `git apply --check` before mutation.
* Concurrency controls must prevent two sessions from sharing the same workspace.
* Provide hooks for the observability task to emit metrics about pool utilization.

## Completion Notes

- Added the `debug_server/worktrees` package (`__init__`, `pool.py`, `dependency_sync.py`, `inspect.py`) implementing the
  bare-repo mirror, leasing semantics, dependency fingerprinting, and Typer admin commands.
- Expanded the metadata service with helpers to list/update worktrees and to resolve repositories by name.
- Documented the workflow in [`docs/worktrees.md`](../../docs/worktrees.md) and linked it from [`.codex/spec.md`](../spec.md).
- Created unit tests under `tests/worktrees/` plus an integration test for the session cache and wired a shared
  `metadata_store` fixture at `tests/conftest.py`.
- Verified style/quality via `ruff`, `black --check`, `mypy`, and executed `pytest` across the suite.
- Follow-up: cleared reclaimed worktree metadata so dependency sync runs after directories are removed and added
  `tests/worktrees/test_pool.py::test_reclaimed_worktree_requires_dependency_sync` to guard the behavior.

## Completion Checklist
* [x] Code implemented
* [x] Tests written/updated and passing
* [x] Examples added/updated
* [x] Docs updated where needed
* [x] Linting/formatting clean
* [x] Review complete
* [x] **Move this file to** `.codex/done/` **when all boxes are checked**
