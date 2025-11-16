# Debug Server Bootstrap

This repository currently focuses on a reproducible bootstrap path for the future debug server. The steps below create the host environment, verify the already-cloned repository, and run smoke checks to ensure storage and credentials work before the higher-level services are implemented.

## Prerequisites

- Python 3.11+
- `git`
- Miniconda/Mamba (`conda` on `PATH`). If Conda is unavailable the bootstrap script downloads and verifies the Linux x86_64 Miniconda installer (accepting the license with `-b`) and installs it to `.artifacts/miniconda3`. Non-Linux hosts must update `conda_installer_url` and `conda_installer_sha256` in `config/bootstrap.toml` before running the script.

## Quick Start

```bash
# Inspect or edit the bootstrap configuration.
cp config/bootstrap.toml config/bootstrap.local.toml
$EDITOR config/bootstrap.local.toml

# Run a dry-run check to validate prerequisites.
./scripts/bootstrap.py --config config/bootstrap.local.toml --check

# Provision the environment, verify the repository checkout, and prepare storage artifacts.
./scripts/bootstrap.py --config config/bootstrap.local.toml
```

The script will:

1. Ensure the required binaries (`git`, `conda`, etc.) are present.
2. Download, verify, and install Miniconda when `conda` is not already on `PATH`, then create or update the Conda environment declared in `environment.yml`. When corporate proxies inject custom certificate bundles the script automatically exports `CONDA_SSL_VERIFY` using the existing `REQUESTS_CA_BUNDLE`/`SSL_CERT_FILE`/`PIP_CERT`/`CODEX_PROXY_CERT` values so Conda can trust the intercepted HTTPS traffic.
3. Confirm the repository in `repository.path` already exists (Codex checks out the repo for you) and run `git fetch --all --prune` to refresh it.
4. Prepare storage folders and run a SQLite read/write smoke test.
5. Warn when the expected bearer token environment variable is missing.

## Smoke Tests

To verify connectivity to required services and ensure the bootstrap artifacts stay healthy, run:

```bash
./scripts/bootstrap.py --check
pytest tests/bootstrap
```

These commands double as CI checks and should be executed before sending a pull request.

## Metadata Store & Tooling

The execution service now ships a SQLite metadata store defined with SQLModel and Alembic
migrations under `debug_server/db/`. Use the following commands to work with the database:

```bash
# Create the default database and apply all migrations.
python -m debug_server.db.migrate upgrade head

# Inspect the migration history.
python -m debug_server.db.migrate history

# Generate a personal access token for API access.
python -m debug_server.db.admin create-token ops --scopes admin,cli
```

All commands honor `DEBUG_SERVER_DB_URL`; when unset they default to the bootstrap-managed
SQLite file `.artifacts/data/metadata.db`. See [`docs/architecture.md`](docs/architecture.md)
for a breakdown of the schema and persistence workflow.
## Python CLI

The repository now ships a Click-based CLI bundled with the shared `debug-server-client` package. Install it in editable mode and configure your token once per machine:

```bash
pip install -e .
debug-server configure --base-url https://debug.example.com --token sk-xxx
```

Run `debug-server --help` or see [`docs/cli.md`](docs/cli.md) for command walkthroughs covering repository initialization, session creation, log streaming, debugger control, and artifact downloads.
Cloud launchers for human operators are documented in [`docs/deployment.md`](docs/deployment.md), including the Terraform stacks and encryption guardrails used to protect remote hosts.

## FastAPI Service

The server API ships inside this repository under `debug_server/api`. Launch it locally with Uvicorn once the metadata database has been bootstrapped:

```bash
pip install -e .[dev]
uvicorn debug_server.api.main:app --reload
```

Authenticate every HTTP and WebSocket request with a bearer token created via `python -m debug_server.db.admin create-token <name>`. The FastAPI app enforces scopes such as `sessions:write`, `commands:write`, and `artifacts:read` so you can mint limited tokens for automation. The `/docs` and `/redoc` routes expose the OpenAPI schema, while [`docs/api.md`](docs/api.md) documents the high-level workflow for repository initialization, session management, command queueing, and artifact downloads.
To seed another repository with the Debug Server workflow, run:

```bash
debug-server agent install ../other-repo --section-heading "Debug Server"
```

The installer reuses your configured `debug-server configure` settings (base URL,
token, TLS verification) to embed environment-specific guidance and to scaffold
`.codex/` metadata so the downstream repo can start using the workflow instantly.
