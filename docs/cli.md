# Debug Server CLI

The Click-based CLI ships from the shared `debug-server-client` package found under [`client/`](../client/). It exposes a user-friendly surface for initializing the server, creating sessions, streaming logs, controlling debugger sessions, and downloading artifacts.

## Installation

```bash
pip install -e .
```

This registers the `debug-server` command via the entry point defined in `pyproject.toml`.

## Authentication

1. Create a token via the Debug Server operator.
2. Persist the token and base URL locally:

   ```bash
   debug-server configure --base-url https://debug.example.com --token sk-xxx
   ```

   Credentials live at `~/.debug-server/config.toml`. Set `DEBUG_SERVER_HOME` to override the location in CI.

## Common Commands

### Initialize the server repository

```bash
debug-server server init https://github.com/org/repo.git --default-branch main --manifest requirements.txt
```

### Create a session and follow logs

```bash
debug-server session create --commit main --patch /tmp/changes.patch --command "pytest -m smoke" --metadata ticket=ABC-123 --follow
```

### Tail an existing session

```bash
debug-server session logs 01H..XYZ --follow --format text
```

### Send debugger actions

```bash
debug-server session debug 01H..XYZ --action step --payload frame=top
```

### Download artifacts

```bash
debug-server artifact download 01H..XYZ coverage-xml --output ~/Downloads/coverage.xml
```

Use `debug-server --help` or `debug-server <group> --help` for option details.

### Seed another repository with Debug Server instructions

Once your CLI is configured, you can share the Debug Server workflow with
additional repositories:

```bash
debug-server agent install ../partner-repo --section-heading "Debug Server Workflow"
```

The command locates (or creates) `AGENTS.md`, inserts an idempotent block that
links back to this repository's documentation, and scaffolds `.codex/` metadata
folders so the downstream project can start capturing tasks immediately. It uses
your configured base URL and TLS preferences; set them with `debug-server
configure` or environment variables before running the installer.

## Cloud launcher (human operators only)

The CLI can render Terraform variables and, when Terraform is available, launch
the debug server container on a remote Docker host.

```bash
# mark the session as interactive and provide a state-encryption key
export DEBUG_SERVER_OPERATOR_ALLOW=1
export DEBUG_SERVER_OPERATOR_KEY="workstation-secret"

debug-server cloud up \
  --provider hetzner \
  --docker-host tcp://10.0.0.5:2376 \
  --image ghcr.io/org/debug-server:latest \
  --env ENV=prod \
  --port 8000:8000

# tear everything down once finished
debug-server cloud destroy --stack-name debug-cloud --apply

# inspect inventory and sessions
debug-server cloud list
debug-server cloud status --stack-name debug-cloud
debug-server cloud sessions --stack-name debug-cloud
```

Automation markers such as `CI` or `DEBUG_SERVER_AGENT` block the command by
default to prevent unintended infrastructure launches. State for each stack is
encrypted and written to `~/.debug-server/cloud/` using
`DEBUG_SERVER_OPERATOR_KEY`.

The CLI also maintains an **inventory** file in the same directory that
summarizes every tracked stack and its active sessions. `cloud list` and
`cloud status` surface the servers you have launched, while `cloud sessions`
lets operators record or drain per-session ownership before destroying a stack.
Set `--session-id` with `--stack-name` to register or update a session,
`--drain` to mark it for teardown, and `--delete` to remove it from the
inventory once it is closed.
