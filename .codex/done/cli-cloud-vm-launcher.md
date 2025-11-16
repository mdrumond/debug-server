# cli: cloud vm launcher and terraform docker_node module

- **ID**: T-011
- **Created**: 2024-08-01
- **Owner**: gpt-5-codex
- **Status**: Completed

## Goal
Provide an optional CLI feature (e.g., `debug-cli cloud up`) that provisions a VM via Terraform, bootstraps Docker, and starts the debug server container remotely using a provider-agnostic `docker_node` module. The CLI flow must remain compatible with the API/runner plans in [`.codex/tasks/server-api-lifecycle-and-auth.md`](server-api-lifecycle-and-auth.md), [`.codex/tasks/server-api-debug-streams.md`](server-api-debug-streams.md), and [`.codex/tasks/server-runner-worker-engine.md`](server-runner-worker-engine.md) so that once the VM is online, it registers with the same lifecycle and debugger orchestration endpoints. **This capability must be explicitly disabled for autonomous agents**—only human operators with workstation credentials may execute the cloud launcher commands, and the CLI must enforce this restriction via identity checks/feature flags.

## Plan
1. Create `infra/terraform/modules/docker_node` that uses the Terraform Docker provider to pull/run an `app_image` container given a `docker_host`, TLS material, env, and port mappings. Ensure outputs expose container metadata and effective host info for the CLI/API layers.
2. Author provider-specific example stacks (`infra/terraform/hetzner_docker_node`, `infra/terraform/contabo_docker_node`) that provision x86 hosts, install Docker via `cloud-init` user data, expose a secure TCP Docker endpoint (or SSH tunnel), and invoke the shared module. Document how to pass `app_ports` so the FastAPI surface from API tasks is reachable.
3. Extend the CLI (`client/cli/cloud.py`) with commands to render `terraform.tfvars`, call `terraform init/plan/apply/destroy`, and surface connection info/token injection for the API/auth flows described in the server API tasks. Provide dry-run + noninteractive flags that align with existing CLI session commands while **asserting the operator is not an agent** (e.g., require workstation-issued auth tokens, disable within automated contexts, and log denials).
4. Persist state after a successful `cloud up`: capture the VM/public addresses, Docker endpoint URLs, and any minted API/runner tokens so that subsequent CLI invocations (destroy, connect, logs) have consistent context. State must be encrypted-at-rest, versioned, and scoped per operator.
5. Integrate with the multi-server session tracking effort from [`.codex/tasks/cli-cloud-session-state.md`](cli-cloud-session-state.md): each VM/server should register a session inventory entry describing which debug sessions are pinned to which host, along with the provider name/stack identifiers.
6. Add docs in [`docs/deployment.md`](../../docs/deployment.md) and [`.codex/spec.md`](../spec.md) explaining how this Terraform-driven bootstrap complements the runner + observability tasks, how state files are stored, and how human-only enforcement works.

## Deliverables
- Terraform module + examples under `infra/terraform/`.
- CLI additions under `client/cli/` plus supporting config schema entries, including state serialization for provider address/token material and integration hooks for multi-server tracking.
- Documentation updates and usage examples referencing API + runner tasks.
- Tests validating CLI command parsing/execution stubs, Terraform template rendering, the human-only enforcement checks, and the state persistence adapters shared with the multi-server tracker.

## Tests & Examples
- **Test strategy:** Python unit tests for CLI argument parsing + orchestration helpers, and smoke tests that template Terraform inputs (mock subprocesses).
- **Commands to run tests:**
  ```bash
  pytest tests/cli/test_cloud.py
  pytest tests/infra/test_terraform_templates.py
  ```
* **Examples (how to run/use the feature):**
  ```bash
  debug-cli cloud up --provider hetzner --env prod --image ghcr.io/org/debug-server:latest
  debug-cli cloud destroy --provider contabo --stack-name debug-lab
  ```

## Linting & Quality
* **Commands to lint/format:**
  ```bash
  ruff check client/cli infra/terraform
  black client/cli
  ```
* **Static analysis / type checks:**
  ```bash
  mypy client/cli
  ```

## Documentation Updates
* [`README.md`](../../README.md)
* [`docs/deployment.md`](../../docs/deployment.md) (include secure-operator workflows, state layout, and cross references to human-only guardrails)
* [`docs/cli.md`](../../docs/cli.md) (document state files, address/token inspection commands, and multi-server session listings)
* [`.codex/spec.md`](../spec.md) (capture architecture additions for CLI state + restricted operator mode)

## Notes / Risks
* Need to keep the Terraform module provider-agnostic; provider-specific stacks should only compose additional resources.
* Secure handling of TLS certs/SSH keys is critical; ensure secrets never end up committed. The persisted state (addresses + tokens) must be encrypted and redactable for logs/export.
* Long-running Terraform applies must stream progress so the CLI UX aligns with the lifecycle expectations from the API tasks.
* Deny-by-default posture for agents: CI and bot contexts must not be allowed to start remote infrastructure.

## Completion Checklist
* [x] Code implemented
* [x] Tests written/updated and passing (`tests/cli/test_cloud.py`, `tests/infra/test_terraform_templates.py`)
* [x] Examples added/updated (CLI snippets in docs)
* [x] Docs updated where needed (README, docs/cli.md, docs/deployment.md, .codex/spec.md)
* [x] Linting/formatting clean
* [x] Review complete
* [x] **Move this file to** `.codex/done/` **when all boxes are checked**

## Completion Notes
- Added `client/cli/cloud.py` with human-only guardrails, Terraform tfvars rendering, and encrypted state handling.
- Created Terraform Docker module plus Hetzner/Contabo stack entrypoints under `infra/terraform/`.
- Documented operator workflow and guardrails in `docs/deployment.md`, updated CLI and spec docs, and referenced the new flow from the README.
- New tests cover the guardrails, tfvars emission, encrypted state, Terraform template presence, and Terraform invoker error/success paths.
- Hardened encrypted state storage with PBKDF2-derived Fernet keys and clarified Terraform module env/port handling.
- Follow-up tightened encryption (Fernet), path/port validation, Terraform output handling, and documentation for operator key management.
