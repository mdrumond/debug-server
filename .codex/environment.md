# Environment

Default bootstrap path: create a Conda environment (or Miniconda/Mamba equivalent) that installs the Python server plus any shared worker prerequisites described in `.codex/spec.md`. When Docker is available we may also publish an image, but the service must be installable on hosts where only user-level package managers (Conda, pip, pipx, uv, npm/pnpm/yarn, cargo, etc.) are allowed.

Document exact commands here (e.g., `conda env create -f env.yaml && pip install -r requirements.txt`) as soon as implementation work begins.
