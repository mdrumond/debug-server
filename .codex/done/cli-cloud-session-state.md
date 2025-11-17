# cli: cloud session state and multi-server inventory

- **ID**: T-012
- **Created**: 2024-08-02
- **Owner**: gpt-5-codex
- **Status**: Done

## Goal
Design and implement the CLI-side persistence layer that records cloud launcher outputs (provider endpoints, authentication tokens, running sessions) so human operators can safely manage multiple remote debug-server instances. The state store must integrate with the Terraform workflow in [`.codex/tasks/cli-cloud-vm-launcher.md`](cli-cloud-vm-launcher.md) while remaining inaccessible to agents/automation.

## Plan
1. Define a secure local state format (e.g., encrypted JSON/YAML) that stores per-operator data: provider name, stack identifier, VM/Docker addresses, issued runner/API tokens, and timestamps.
2. Extend `client/cli/cloud.py` helpers so that `cloud up` registers a new server entry, `cloud destroy` removes it, and new commands (e.g., `cloud list`, `cloud status`, `cloud sessions`) read the state file.
3. Track debug sessions: associate session IDs (from API lifecycle tasks) with the server on which they run, including current status, owner, and active tokens. Provide CLI UX for reassigning or draining sessions before tearing down infrastructure.
4. Harden the storage mechanism: encrypt sensitive values, provide redact-on-export utilities, version the schema, and ensure state is never uploaded to remote stores without explicit opt-in. Enforce human-only access checks shared with the launcher task.
5. Document the state lifecycle, backup guidance, and troubleshooting steps in [`docs/cli.md`](../../docs/cli.md) and [`.codex/spec.md`](../spec.md).

## Deliverables
- Secure state storage module under `client/cli/` (or `client/state/`) with read/write helpers and schema definitions.
- CLI subcommands for inspecting servers and sessions, plus guardrails preventing agents from invoking them.
- Integration tests verifying CRUD operations on the state store and how session entries synchronize with launcher commands.
- Documentation updates detailing operator workflows for multi-server management and state hygiene.

## Tests & Examples
- **Test strategy:** Unit tests for the state serializer/encryptor and CLI command flows; integration-style tests mocking API lifecycle calls to ensure session mappings update correctly.
- **Commands to run tests:**
  ```bash
  pytest tests/cli/test_cloud_state.py
  pytest tests/cli/test_cloud_sessions.py
  ```
* **Examples (how to run/use the feature):**
  ```bash
  debug-cli cloud list
  debug-cli cloud sessions --server hetzner-prod
  debug-cli cloud status --session 123e4567
  ```

## Linting & Quality
* **Commands to lint/format:**
  ```bash
  ruff check client/cli client/state
  black client/cli client/state
  ```
* **Static analysis / type checks:**
  ```bash
  mypy client/cli client/state
  ```

## Documentation Updates
* [`docs/cli.md`](../../docs/cli.md)
* [`docs/deployment.md`](../../docs/deployment.md)
* [`.codex/spec.md`](../spec.md)

## Notes / Risks
* State must never be readable by agents/CI. Build in feature-flag checks plus audit logging for attempted access.
* Consider secure storage backends (OS keyring, encrypted files) and portability across macOS/Linux workstations.
* Coordinate schema versions with Terraform backend outputs to avoid drift between launcher and session-tracking commands.

## Completion Checklist
* [x] Code implemented
* [x] Tests written/updated and passing (`pytest tests/cli`)
* [x] Examples added/updated
* [x] Docs updated where needed
* [x] Linting/formatting clean (`ruff check client/cli tests/cli`, `black client/cli tests/cli`, `mypy client/cli`)
* [x] Review complete
* [x] **Move this file to** `.codex/done/` **when all boxes are checked**
