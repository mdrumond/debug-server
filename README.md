# Debug Server Bootstrap

This repository currently focuses on a reproducible bootstrap path for the future debug server. The steps below create the host environment, verify the already-cloned repository, and run smoke checks to ensure storage and credentials work before the higher-level services are implemented.

## Prerequisites

- Python 3.11+
- `git`
- Miniconda/Mamba (`conda` on `PATH`). If Conda is unavailable the bootstrap script now downloads Miniconda automatically (accepting the license with `-b`) and installs it to `.artifacts/miniconda3`. You can still set `use_conda = false` in `config/bootstrap.toml` to fall back to a virtual environment.

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
2. Download and install Miniconda when `conda` is not already on `PATH`, then create or update the Conda environment declared in `environment.yml` (or create `.venv` and install the pip dependencies declared there when configured).
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
