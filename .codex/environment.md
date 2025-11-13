# Environment

This project boots via a Conda-first workflow with a virtualenv fallback. Operators only need stock Python 3.11+, `git`, and Con
da (Miniconda/Mamba). All bootstrap logic lives in `scripts/bootstrap.py`.

## Provisioning Steps

```bash
# 1. Inspect or customize the configuration (optional).
cp config/bootstrap.toml config/bootstrap.local.toml
$EDITOR config/bootstrap.local.toml

# 2. Validate prerequisites without mutating the filesystem.
./scripts/bootstrap.py --config config/bootstrap.local.toml --check

# 3. Create/update the Conda environment, clone the bare repo mirror, and prepare storage.
./scripts/bootstrap.py --config config/bootstrap.local.toml
```

The bootstrap script will:

- Run `conda env create|update -n <name> -f environment.yml` when `use_conda = true`.
- Create `.venv` via `python -m venv .venv` when `use_conda = false` or Conda is missing and `allow_venv_fallback = true`.
- Clone or fetch the bare repository mirror at `.artifacts/repos/...` using `git clone --mirror` and `git fetch --prune`.
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
```

If a host cannot install Conda, set `use_conda = false` in `config/bootstrap.toml` to rely on the built-in virtualenv flow.
