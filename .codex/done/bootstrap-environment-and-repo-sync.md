# bootstrap: environment and repository bootstrap

- **ID**: T-001
- **Created**: 2024-07-30
- **Owner**: gpt-5-codex
- **Status**: Open

## Goal
Produce reproducible scripts and documentation so operators can provision the Conda-first runtime, initialize the bare upstream repository mirror, and configure global settings (auth secrets, storage paths). All downstream work (backend, API, runner, CLI) depends on these guarantees.

## Plan
1. Author `.codex/environment.md` commands plus a `scripts/bootstrap.py` (or shell) that installs Python dependencies, creates the Conda env, and verifies required system binaries.
2. Implement repo initialization helpers that clone/fetch the bare repository mirror plus optional submodules. Expose settings via `config/bootstrap.toml`.
3. Provide smoke-test commands (dry-run mode) to validate credentials, filesystem permissions, and SQLite file access for later server-backend tasks (see [`.codex/tasks/server-backend-sqlite-metadata-store.md`](server-backend-sqlite-metadata-store.md)).
4. Document how subsequent tasks consume these artifacts (env activation script, config file paths) so there is no ambiguity for other contributors.

## Deliverables
- `scripts/bootstrap.py` (or shell equivalent) and updates to `.codex/environment.md`.
- `config/bootstrap.toml` template plus documentation in `README.md` or `.codex/spec.md`.
- Smoke-test routine referenced by downstream tasks.

## Tests & Examples
- **Test strategy:** Integration smoke tests validating environment + repo bootstrap.
- **Commands to run tests:**
  ```bash
  pytest tests/bootstrap
  ./scripts/bootstrap.py --check
  ```
* **Examples (how to run/use the feature):**
  ```bash
  ./scripts/bootstrap.py --config config/bootstrap.toml
  source .venv/bin/activate && python -m debug_server.config doctor
  ```

## Linting & Quality
* **Commands to lint/format:**
  ```bash
  ruff check scripts/bootstrap.py
  black scripts/bootstrap.py
  ```
* **Static analysis / type checks:**
  ```bash
  mypy scripts/bootstrap.py
  ```

## Documentation Updates
* [`.codex/environment.md`](../environment.md)
* [`.codex/spec.md`](../spec.md)
* [`README.md`](../../README.md)

## Notes / Risks
* The scripts must be idempotent to avoid corrupting caches.
* Need to guard against hosts without Conda by providing a fallback virtualenv path.
* Secrets management should not be hard-coded; rely on environment variables for tokens.

## Completion Checklist
* [ ] Code implemented
* [ ] Tests written/updated and passing
* [ ] Examples added/updated
* [ ] Docs updated where needed
* [ ] Linting/formatting clean
* [ ] Review complete
* [ ] **Move this file to** `.codex/done/` **when all boxes are checked**
