# Environment

This project boots via a Conda-first workflow. Operators only need stock Python 3.11+, `git`, and Conda (Miniconda/Mamba). All bootstrap logic lives in `scripts/bootstrap.py`.

## Provisioning Steps

```bash
# 1. Inspect or customize the configuration (optional).
cp config/bootstrap.toml config/bootstrap.local.toml
$EDITOR config/bootstrap.local.toml

# 2. Validate prerequisites without mutating the filesystem.
./scripts/bootstrap.py --config config/bootstrap.local.toml --check

# 3. Install Conda when needed, update the environment, refresh the repo checkout, and prepare storage.
./scripts/bootstrap.py --config config/bootstrap.local.toml
```

The bootstrap script will:

- Download and verify Miniconda to `.artifacts/miniconda3` when `conda` is missing, accepting the license via the installer `-b` flag to keep hosts non-interactive.
- Run `conda env create|update -n <name> -f environment.yml` when `use_conda = true`, then `pip install -e .[dev]` so SQLModel,
  Alembic, Typer, pytest, Ruff, Black, and mypy are available for local development.
- Fetch the already cloned repository checkout via `git fetch --all --prune`.
- Initialize `.artifacts/data/metadata.db` and run a SQLite smoke test.

## Verification Commands

```bash
# Ensure the Conda environment exists.
conda env list | grep debug-server

# Activate and inspect python version.
conda activate debug-server && python --version

# Run repo+storage smoke tests.
./scripts/bootstrap.py --check
pytest tests/bootstrap

# Apply database migrations and run unit tests for the metadata store.
python -m debug_server.db.migrate upgrade head
pytest tests/db tests/integration/test_db_transactions.py
```

Automatic Miniconda installation currently supports Linux x86_64 hosts only. Update `conda_installer_url` and `conda_installer_sha256` in `config/bootstrap.toml` when provisioning macOS or Windows machines.
