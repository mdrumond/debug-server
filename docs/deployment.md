# Cloud bootstrap with Terraform

The CLI ships with a provider-agnostic Terraform module that can start the debug
server container on a remote VM. The workflow is intended for human operators
only; CI and automated agents are blocked unless a workstation override is
explicitly set.

## Components

- `infra/terraform/modules/docker_node`: wraps the Terraform Docker provider and
  runs the configured `app_image` on a remote Docker daemon.
- `infra/terraform/hetzner_docker_node` and `infra/terraform/contabo_docker_node`:
  provider-specific entrypoints that pass addresses, ports, and optional runner
  tokens into the shared module.
- `client/cli/cloud.py`: Click commands for rendering `terraform.tfvars.json`,
  invoking `terraform`, and persisting encrypted state per operator.

## Usage

1. Export a workstation key used to encrypt state:

   ```bash
   export DEBUG_SERVER_OPERATOR_KEY="random-but-memorable"
   export DEBUG_SERVER_OPERATOR_ALLOW=1  # only for interactive sessions
   ```

2. Generate Terraform variables (dry run by default):

   ```bash
   debug-server cloud up \
     --provider hetzner \
     --docker-host tcp://10.0.0.5:2376 \
     --image ghcr.io/org/debug-server:latest \
     --env ENV=prod \
     --port 8000:8000
   ```

3. If Terraform is installed locally, re-run with `--apply` to run `init`,
   `plan`, and `apply`.

4. Destroy the stack when finished:

   ```bash
   debug-server cloud destroy --stack-name debug-cloud --apply
   ```

The CLI writes `terraform.tfvars.json` into the provider-specific stack
directory and stores encrypted state under `~/.debug-server/cloud/`. The state
records Docker hosts, ports, and token metadata so follow-up commands can re-use
existing stacks.

> **⚠️ Important: Key Management**
>
> The `DEBUG_SERVER_OPERATOR_KEY` is used to encrypt and decrypt your local state cache. If
> you lose or change this key, any previously stored state under `~/.debug-server/cloud/`
> will become inaccessible and cannot be recovered. This may result in loss of stack
> metadata and require manual recreation of stacks. Always keep your operator key safe and
> consistent across sessions. Each state file carries a unique salt for PBKDF2 key
> derivation, but the passphrase must stay the same. Key rotation is not currently
> supported; to change your key, you must manually migrate or re-create your state.

## Human-only guardrails

- Commands abort when common automation markers (`CI`, `DEBUG_SERVER_AGENT`,
  `DEBUG_SERVER_AUTOMATION`) are set.
- Operators must provide `DEBUG_SERVER_OPERATOR_KEY` to unlock the local state
  cache.
- The override `DEBUG_SERVER_OPERATOR_ALLOW=1` exists to acknowledge an
  interactive session; do not set this in autonomous or multi-tenant contexts.
