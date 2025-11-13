#!/usr/bin/env python3
"""Environment and repository bootstrap helper."""
from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import subprocess
import sys
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError as exc:  # pragma: no cover - guard for very old interpreters
    raise RuntimeError("Python 3.11+ is required to run the bootstrap script") from exc


@dataclass
class EnvironmentSettings:
    name: str
    python_version: str
    use_conda: bool = True
    conda_command: str = "conda"
    conda_environment_file: str = "environment.yml"
    conda_install_path: str = ".artifacts/miniconda3"
    conda_installer_url: str = (
        "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
    )
    venv_path: str = ".venv"
    allow_venv_fallback: bool = True


@dataclass
class RepositorySettings:
    path: str
    default_branch: str = "main"
    fetch_prune: bool = True


@dataclass
class StorageSettings:
    data_dir: str
    sqlite_path: str


@dataclass
class AuthSettings:
    token_environment_variable: str = "DEBUG_SERVER_TOKEN"


@dataclass
class BootstrapConfig:
    environment: EnvironmentSettings
    repository: RepositorySettings
    storage: StorageSettings
    auth: AuthSettings = field(default_factory=AuthSettings)
    required_binaries: List[str] = field(default_factory=lambda: ["git"])

    @classmethod
    def from_mapping(cls, data: dict) -> "BootstrapConfig":
        env = data.get("environment", {})
        repo = data.get("repository", {})
        storage = data.get("storage", {})
        auth = data.get("auth", {})
        required = data.get("required_binaries", ["git"])

        missing_fields = []
        repo_path = repo.get("path") or repo.get("mirror_path")
        if not repo_path:
            missing_fields.append("repository.path")
        if "data_dir" not in storage:
            missing_fields.append("storage.data_dir")
        if "sqlite_path" not in storage:
            missing_fields.append("storage.sqlite_path")
        if missing_fields:
            raise ValueError(
                f"Missing required configuration keys: {', '.join(missing_fields)}"
            )

        environment = EnvironmentSettings(
            name=env.get("name", "debug-server"),
            python_version=env.get(
                "python_version", f"{sys.version_info.major}.{sys.version_info.minor}"
            ),
            use_conda=env.get("use_conda", True),
            conda_command=env.get("conda_command", "conda"),
            conda_environment_file=env.get("conda_environment_file", "environment.yml"),
            conda_install_path=env.get("conda_install_path", ".artifacts/miniconda3"),
            conda_installer_url=env.get(
                "conda_installer_url",
                "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh",
            ),
            venv_path=env.get("venv_path", ".venv"),
            allow_venv_fallback=env.get("allow_venv_fallback", True),
        )
        repository = RepositorySettings(
            path=repo_path,
            default_branch=repo.get("default_branch", "main"),
            fetch_prune=repo.get("fetch_prune", True),
        )
        storage_settings = StorageSettings(
            data_dir=storage["data_dir"],
            sqlite_path=storage["sqlite_path"],
        )
        auth_settings = AuthSettings(
            token_environment_variable=auth.get(
                "token_environment_variable", "DEBUG_SERVER_TOKEN"
            ),
        )
        return cls(
            environment=environment,
            repository=repository,
            storage=storage_settings,
            auth=auth_settings,
            required_binaries=list(required),
        )

    @classmethod
    def load(cls, path: Path) -> "BootstrapConfig":
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        with path.open("rb") as handle:
            data = tomllib.load(handle)
        return cls.from_mapping(data)


class BootstrapManager:
    def __init__(self, config: BootstrapConfig, dry_run: bool = False):
        self.config = config
        self.dry_run = dry_run

    # Public API -----------------------------------------------------------
    def run(self) -> None:
        self._log("Starting bootstrap")
        self.ensure_required_binaries()
        self.prepare_environment()
        self.prepare_repository()
        self.prepare_storage()
        self.run_smoke_tests()
        self._log("Bootstrap complete")

    def ensure_required_binaries(self) -> None:
        for binary in self.config.required_binaries:
            if shutil.which(binary) is None:
                raise RuntimeError(
                    f"Required binary '{binary}' is not available on PATH"
                )
            self._log(f"✓ Found binary: {binary}")
        if self.config.environment.use_conda:
            self._ensure_conda_available()

    def prepare_environment(self) -> None:
        env = self.config.environment
        if env.use_conda:
            self._prepare_conda_environment(env)
        else:
            self._prepare_virtualenv(Path(env.venv_path))

    def prepare_repository(self) -> None:
        repo = self.config.repository
        repo_path = Path(repo.path)
        git_dir = repo_path / ".git"
        if not git_dir.exists():
            raise RuntimeError(
                f"Repository path '{repo_path}' is missing a .git directory. The bootstrap script expects the repo to be cloned already.",
            )
        if self.dry_run:
            self._log(f"[DRY-RUN] Would fetch updates for {repo_path}")
            return
        self._git_fetch(repo_path, prune=repo.fetch_prune)

    def prepare_storage(self) -> None:
        storage = self.config.storage
        data_dir = Path(storage.data_dir)
        sqlite_path = Path(storage.sqlite_path)
        if not self.dry_run:
            data_dir.mkdir(parents=True, exist_ok=True)
            sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            if not sqlite_path.exists():
                with sqlite3.connect(sqlite_path) as connection:
                    connection.execute("pragma journal_mode=WAL;")
                self._log(f"✓ Initialized SQLite metadata file at {sqlite_path}")
            else:
                self._log(f"✓ SQLite metadata file already present at {sqlite_path}")
        else:
            self._log(f"[DRY-RUN] Would ensure storage directories exist at {data_dir}")
            self._log(f"[DRY-RUN] Would ensure SQLite database exists at {sqlite_path}")

    def run_smoke_tests(self) -> None:
        storage = self.config.storage
        sqlite_path = Path(storage.sqlite_path)
        if not self.dry_run and sqlite_path.exists():
            with sqlite3.connect(sqlite_path) as connection:
                connection.execute("select 1")
            self._log("✓ SQLite read/write smoke test passed")
        token_env = self.config.auth.token_environment_variable
        if token_env and not os.environ.get(token_env):
            self._log(f"⚠️  Auth token environment variable '{token_env}' is not set")
        else:
            self._log(f"✓ Auth token environment variable '{token_env}' detected")

    # Internal helpers -----------------------------------------------------
    def _prepare_conda_environment(self, env: EnvironmentSettings) -> None:
        conda_cmd = env.conda_command or "conda"
        if self.dry_run:
            self._log(
                f"[DRY-RUN] Would create or update Conda env '{env.name}' via {conda_cmd} using {env.conda_environment_file}",
            )
            return
        env_file = Path(env.conda_environment_file)
        if not env_file.exists():
            raise FileNotFoundError(
                f"Conda environment file '{env.conda_environment_file}' not found. Update config or add the file.",
            )
        list_output = self._run([conda_cmd, "env", "list"], capture_output=True)
        if env.name not in list_output:
            self._run([conda_cmd, "env", "create", "-n", env.name, "-f", str(env_file)])
            self._log(f"✓ Created Conda environment '{env.name}'")
        else:
            self._run([conda_cmd, "env", "update", "-n", env.name, "-f", str(env_file)])
            self._log(f"✓ Updated Conda environment '{env.name}'")

    def _prepare_virtualenv(self, venv_path: Path) -> None:
        env_file = Path(self.config.environment.conda_environment_file)
        if self.dry_run:
            self._log(f"[DRY-RUN] Would create virtual environment at {venv_path}")
            self._log(
                f"[DRY-RUN] Would install pip dependencies declared in {env_file}"
            )
            return
        if not venv_path.exists():
            venv_path.parent.mkdir(parents=True, exist_ok=True)
            self._run([sys.executable, "-m", "venv", str(venv_path)])
            self._log(f"✓ Created Python virtual environment at {venv_path}")
        else:
            self._log(f"✓ Virtual environment already exists at {venv_path}")
        self._install_virtualenv_dependencies(venv_path, env_file)

    def _install_virtualenv_dependencies(self, venv_path: Path, env_file: Path) -> None:
        if not env_file.exists():
            raise FileNotFoundError(
                "Conda environment file not found; required to install pip dependencies"
            )
        pip_dependencies = self._extract_pip_dependencies(env_file)
        if not pip_dependencies:
            self._log(
                f"⚠️  No pip dependencies declared in {env_file}; skipping virtualenv install"
            )
            return
        python_binary = self._virtualenv_python_path(venv_path)
        self._run(
            [
                str(python_binary),
                "-m",
                "pip",
                "install",
                *pip_dependencies,
            ]
        )
        package_word = "package" if len(pip_dependencies) == 1 else "packages"
        self._log(
            f"✓ Installed {len(pip_dependencies)} pip {package_word} into virtualenv from {env_file}"
        )

    def _virtualenv_python_path(self, venv_path: Path) -> Path:
        if os.name == "nt":
            candidate = venv_path / "Scripts" / "python.exe"
        else:
            candidate = venv_path / "bin" / "python"
        if not candidate.exists():
            raise FileNotFoundError(
                f"Python interpreter not found inside virtual environment at {candidate}"
            )
        return candidate

    def _extract_pip_dependencies(self, env_file: Path) -> list[str]:
        pip_deps: list[str] = []
        pip_indent: int | None = None
        for raw_line in env_file.read_text().splitlines():
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(raw_line) - len(raw_line.lstrip(" "))
            if pip_indent is not None:
                if indent <= pip_indent:
                    pip_indent = None
                elif stripped.startswith("- "):
                    pip_deps.append(stripped[2:].strip())
                    continue
            if stripped.startswith("- pip:"):
                pip_indent = indent
        return pip_deps

    def _git_fetch(self, repo_path: Path, prune: bool) -> None:
        args = ["git", "-C", str(repo_path), "fetch", "--all"]
        if prune:
            args.append("--prune")
        self._run(args)
        self._log(f"✓ Updated repository at {repo_path}")

    def _ensure_conda_available(self) -> None:
        env = self.config.environment
        conda_cmd = env.conda_command or "conda"
        resolved = shutil.which(conda_cmd)
        if resolved:
            env.conda_command = resolved
            self._log(f"✓ Found Conda executable: {resolved}")
            return
        self._log(
            "Conda executable not found on PATH – attempting to download and install Miniconda with license acceptance",
        )
        installed = self._install_conda(env)
        if installed:
            env.conda_command = str(installed)
            self._log(f"✓ Installed Conda at {installed}")
            return
        if self.dry_run:
            self._log(
                "[DRY-RUN] Conda installation skipped; run without --check to perform the installation",
            )
            return
        if env.allow_venv_fallback:
            self._log(
                "⚠️  Conda installation failed – falling back to Python virtualenv",
            )
            env.use_conda = False
            return
        raise RuntimeError(
            "Conda is required but could not be installed automatically. Install it manually or disable use_conda.",
        )

    def _install_conda(self, env: EnvironmentSettings) -> Path | None:
        install_dir = Path(env.conda_install_path).expanduser()
        conda_binary = install_dir / "bin" / "conda"
        if conda_binary.exists():
            return conda_binary
        installer_url = env.conda_installer_url
        if self.dry_run:
            self._log(
                f"[DRY-RUN] Would download Conda installer from {installer_url} and install to {install_dir} with --batch license acceptance",
            )
            return None
        install_dir.parent.mkdir(parents=True, exist_ok=True)
        installer_path = install_dir.parent / "miniconda-installer.sh"
        self._log(f"→ Downloading Miniconda from {installer_url}")
        with urllib.request.urlopen(installer_url) as response, installer_path.open(
            "wb"
        ) as handle:
            shutil.copyfileobj(response, handle)
        os.chmod(installer_path, 0o755)
        self._log(
            f"→ Installing Miniconda to {install_dir} (accepting license via --batch)",
        )
        self._run(["bash", str(installer_path), "-b", "-p", str(install_dir), "-f"])
        return conda_binary

    def _run(self, args: Iterable[str], capture_output: bool = False) -> str:
        self._log(f"→ Executing: {' '.join(args)}")
        result = subprocess.run(
            list(args),
            check=True,
            capture_output=capture_output,
            text=True,
        )
        if capture_output:
            assert result.stdout is not None
            return result.stdout
        return ""

    @staticmethod
    def _log(message: str) -> None:
        print(message)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Provision the debug-server bootstrap environment"
    )
    parser.add_argument(
        "--config",
        default="config/bootstrap.toml",
        help="Path to the bootstrap configuration file",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run in dry-run mode (no filesystem mutations)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    config = BootstrapConfig.load(Path(args.config))
    manager = BootstrapManager(config=config, dry_run=args.check)
    manager.run()


if __name__ == "__main__":
    main()
