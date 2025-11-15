# cli: cloud vm launcher and terraform docker_node module

- **ID**: T-011
- **Created**: 2024-08-01
- **Owner**: gpt-5-codex
- **Status**: Open

## Goal
Provide an optional CLI feature (e.g., `debug-cli cloud up`) that provisions a VM via Terraform, bootstraps Docker, and starts the debug server container remotely using a provider-agnostic `docker_node` module. The CLI flow must remain compatible with the API/runner plans in [`.codex/tasks/server-api-lifecycle-and-auth.md`](server-api-lifecycle-and-auth.md), [`.codex/tasks/server-api-debug-streams.md`](server-api-debug-streams.md), and [`.codex/tasks/server-runner-worker-engine.md`](server-runner-worker-engine.md) so that once the VM is online, it registers with the same lifecycle and debugger orchestration endpoints.

## Plan
1. Create `infra/terraform/modules/docker_node` that uses the Terraform Docker provider to pull/run an `app_image` container given a `docker_host`, TLS material, env, and port mappings. Ensure outputs expose container metadata and effective host info for the CLI/API layers.
2. Author provider-specific example stacks (`infra/terraform/hetzner_docker_node`, `infra/terraform/contabo_docker_node`) that provision x86 hosts, install Docker via `cloud-init` user data, expose a secure TCP Docker endpoint (or SSH tunnel), and invoke the shared module. Document how to pass `app_ports` so the FastAPI surface from API tasks is reachable.
3. Extend the CLI (`client/cli/cloud.py`) with commands to render `terraform.tfvars`, call `terraform init/plan/apply/destroy`, and surface connection info/token injection for the API/auth flows described in the server API tasks. Provide dry-run + noninteractive flags that align with existing CLI session commands.
4. Add docs in [`docs/deployment.md`](../../docs/deployment.md) and [`.codex/spec.md`](../spec.md) explaining how this Terraform-driven bootstrap complements the runner + observability tasks.

## Deliverables
- Terraform module + examples under `infra/terraform/`.
- CLI additions under `client/cli/` plus supporting config schema entries.
- Documentation updates and usage examples referencing API + runner tasks.
- Tests validating CLI command parsing/execution stubs and Terraform template rendering.

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
* [`docs/deployment.md`](../../docs/deployment.md)
* [`docs/cli.md`](../../docs/cli.md)
* [`.codex/spec.md`](../spec.md)

## Notes / Risks
* Need to keep the Terraform module provider-agnostic; provider-specific stacks should only compose additional resources.
* Secure handling of TLS certs/SSH keys is critical; ensure secrets never end up committed.
* Long-running Terraform applies must stream progress so the CLI UX aligns with the lifecycle expectations from the API tasks.

## Completion Checklist
* [ ] Code implemented
* [ ] Tests written/updated and passing
* [ ] Examples added/updated
* [ ] Docs updated where needed
* [ ] Linting/formatting clean
* [ ] Review complete
* [ ] **Move this file to** `.codex/done/` **when all boxes are checked**
