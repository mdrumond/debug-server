# Document Docker restart policy in module

- **ID**: T-XXX
- **Created**: 2024-08-03
- **Owner**: gpt-5.1-codex
- **Status**: Completed

## Goal
Document and, if needed, make the Docker restart policy configurable in the Terraform `docker_node` module so operators understand the default behavior and can override it when necessary.

## Plan
1. Inspect `infra/terraform/modules/docker_node` to locate the hardcoded restart policy.
2. Add configuration or documentation that explains the default restart policy and allows overrides.
3. Update module documentation or variable descriptions to reflect the new option.

## Deliverables
- Terraform module updates under `infra/terraform/modules/docker_node`.
- Documentation describing the restart policy and configuration path.
- Tests or lint checks verifying module consistency if applicable.

## Tests & Examples
- **Test strategy:** Verify Terraform module definition passes formatting/linting checks and any relevant unit tests.
- **Commands to run tests:**
  ```bash
  python -m ruff check .
  python -m pytest tests/infra/test_terraform_templates.py
  ```
* **Examples (how to run/use the feature):**
  ```bash
  terraform apply -var restart_policy=always
  ```

## Linting & Quality
* **Commands to lint/format:**
  ```bash
  python -m ruff check .
  ```
* **Static analysis / type checks:**
  ```bash
  mypy
  ```

## Documentation Updates
* [`infra/terraform/modules/docker_node/main.tf`](../terraform/modules/docker_node/main.tf)

## Notes / Risks
* Ruff currently reports pre-existing lint issues outside this change scope (see `client/cli/cloud.py`, `scripts/bootstrap.py`, `tests/bootstrap/test_bootstrap.py`, `tests/mcp/test_server.py`).

## Completion Checklist
* [x] Code implemented
* [x] Tests written/updated and passing (`tests/infra/test_terraform_templates.py`)
* [x] Examples added/updated (Terraform variable example above)
* [x] Docs updated where needed (module variable description)
* [x] Linting/formatting clean (module uses terraform style; repo-wide ruff still reports unrelated issues)
* [x] Review complete
* [x] **Move this file to** `.codex/done/` **when all boxes are checked**

## Completion Notes
- Added a `restart_policy` variable to `infra/terraform/modules/docker_node/main.tf` with validation and a default of `unless-stopped`, documenting the rationale so operators understand the behavior and can override it.
- Wired the Docker container resource to honor the configurable restart policy instead of using a hardcoded value.
- Verified the Terraform template tests pass; ruff currently reports unrelated lint findings in existing Python files.
