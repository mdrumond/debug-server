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
2. Download, verify, and install Miniconda when `conda` is not already on `PATH`, then create or update the Conda environment declared in `environment.yml`.
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

## Python CLI

The repository now ships a Click-based CLI bundled with the shared `debug-server-client` package. Install it in editable mode and configure your token once per machine:

```bash
pip install -e .
debug-server configure --base-url https://debug.example.com --token sk-xxx
```

Run `debug-server --help` or see [`docs/cli.md`](docs/cli.md) for command walkthroughs covering repository initialization, session creation, log streaming, debugger control, and artifact downloads.
