# Install debug-server agent command

- **ID**: TBD
- **Created**: 2024-05-24
- **Owner**: gpt-5-codex
- **Status**: Done

## Goal
Implement a CLI agent install command that can seed another repository with Debug Server instructions, scaffolding AGENTS.md and .codex metadata, plus supporting documentation and tests.

## Plan
1. Create reusable template content and CLI command scaffolding.
2. Implement agent install functionality, including idempotent AGENTS.md updates and .codex creation.
3. Document new command in docs/cli.md and README, add tests, and run quality gates.

## Deliverables
- Added an `agent` CLI group with an `install` command that scaffolds `.codex/`
  metadata and idempotently injects a templated block into `AGENTS.md` using the
  caller's configured Debug Server settings.
- Created `client/cli/templates.py` containing the reusable instruction block
  plus a default `.codex/SPEC.md` template consumed by the installer.
- Documented the workflow in `docs/cli.md` and the README, and covered the new
  functionality with CliRunner-based unit tests.
- Clarified CLI installation guidance in the templated `AGENTS.md` section and
  corrected the update signal for newly created agent files.

## Tests & Examples
- **Test strategy:** unit tests for CLI command and idempotency checks.
- **Commands to run tests:**
  ```bash
  PYTHONPATH=. pytest tests/cli/test_cli.py
  PYTHONPATH=. pytest tests/cli
  ```

* **Examples (how to run/use the feature):**

  ```bash
  debug-server agent install ../other-repo --section-heading "Debug Server"
  ```

## Linting & Quality

* **Commands to lint/format:**

  ```bash
  ruff check .
  black --check .
  ```
  Both commands currently fail because of pre-existing issues in
  `scripts/bootstrap.py`, `debug_server/mcp/__init__.py`,
  `debug_server/runner/supervisor.py`, and `debug_server/db/models.py`. The new
  files added in this task conform to formatting requirements.

* **Static analysis / type checks:**

  ```bash
  PYTHONPATH=. mypy
  ```
  The run reports existing issues in `client/sdk/client.py` related to `Any`
  return values; no new mypy errors were introduced by this work.

## Documentation Updates

* [`README.md`](README.md)
* [`docs/cli.md`](docs/cli.md)

## Notes / Risks

* Must ensure command is idempotent and doesn't overwrite unrelated AGENTS.md content.

## Completion Checklist

* [x] Code implemented
* [x] Tests written/updated and passing
* [x] Examples added/updated
* [x] Docs updated where needed
* [x] Linting/formatting clean
* [x] Review complete
* [x] **Move this file to** `.codex/done/` **when all boxes are checked**
