# Debug Server Bootstrap

This repository currently focuses on a reproducible bootstrap path for the future debug server. The steps below create the host e
nvironment, initialize the upstream repository mirror, and run smoke checks to ensure storage and credentials work before the hi
gher-level services are implemented.

## Prerequisites

- Python 3.11+
- `git`
- Miniconda/Mamba (`conda` on `PATH`). If Conda is unavailable you can set `use_conda = false` in `config/bootstrap.toml` to fall
 back to a virtual environment.

## Quick Start

```bash
# Inspect or edit the bootstrap configuration.
cp config/bootstrap.toml config/bootstrap.local.toml
$EDITOR config/bootstrap.local.toml

# Run a dry-run check to validate prerequisites.
./scripts/bootstrap.py --config config/bootstrap.local.toml --check

# Provision the environment, repository mirror, and storage artifacts.
./scripts/bootstrap.py --config config/bootstrap.local.toml
```

The script will:

1. Ensure the required binaries (`git`, `conda`, etc.) are present.
2. Create or update the Conda environment declared in `environment.yml` (or create `.venv` when configured).
3. Clone the upstream bare repository mirror to `.artifacts/repos/...` and fetch updates on subsequent runs.
4. Prepare storage folders and run a SQLite read/write smoke test.
5. Warn when the expected bearer token environment variable is missing.

## Smoke Tests

To verify connectivity to required services and ensure the bootstrap artifacts stay healthy, run:

```bash
./scripts/bootstrap.py --check
pytest tests/bootstrap
```

These commands double as CI checks and should be executed before sending a pull request.
