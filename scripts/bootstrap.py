#!/usr/bin/env python3
"""Environment and repository bootstrap helper."""
from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import subprocess
import sys
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
    venv_path: str = ".venv"
    allow_venv_fallback: bool = True


@dataclass
class RepositorySettings:
    upstream_url: str
    mirror_path: str
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
        if "upstream_url" not in repo:
            missing_fields.append("repository.upstream_url")
        if "mirror_path" not in repo:
            missing_fields.append("repository.mirror_path")
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
            venv_path=env.get("venv_path", ".venv"),
            allow_venv_fallback=env.get("allow_venv_fallback", True),
        )
        repository = RepositorySettings(
            upstream_url=repo["upstream_url"],
            mirror_path=repo["mirror_path"],
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
            conda_cmd = self.config.environment.conda_command or "conda"
            if shutil.which(conda_cmd) is None:
                if self.config.environment.allow_venv_fallback:
                    self._log(
                        "⚠️  Conda executable not found – falling back to virtualenv creation",
                    )
                    self.config.environment.use_conda = False
                else:
                    raise RuntimeError(
                        "Conda is required but not available. Install Miniconda or disable use_conda in the config.",
                    )

    def prepare_environment(self) -> None:
        env = self.config.environment
        if env.use_conda:
            self._prepare_conda_environment(env)
        else:
            self._prepare_virtualenv(Path(env.venv_path))

    def prepare_repository(self) -> None:
        repo = self.config.repository
        mirror_path = Path(repo.mirror_path)
        if mirror_path.exists() and (mirror_path / "HEAD").exists():
            if self.dry_run:
                self._log(f"[DRY-RUN] Would fetch updates for {mirror_path}")
                return
            self._git_fetch(mirror_path, prune=repo.fetch_prune)
            return

        if self.dry_run:
            self._log(
                f"[DRY-RUN] Would clone bare mirror from {repo.upstream_url} to {mirror_path}"
            )
            return

        mirror_path.parent.mkdir(parents=True, exist_ok=True)
        self._run(
            [
                "git",
                "clone",
                "--mirror",
                repo.upstream_url,
                str(mirror_path),
            ]
        )
        self._log(f"✓ Created bare mirror at {mirror_path}")

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
        if venv_path.exists():
            self._log(f"✓ Virtual environment already exists at {venv_path}")
            return
        if self.dry_run:
            self._log(f"[DRY-RUN] Would create virtual environment at {venv_path}")
            return
        venv_path.parent.mkdir(parents=True, exist_ok=True)
        self._run([sys.executable, "-m", "venv", str(venv_path)])
        self._log(f"✓ Created Python virtual environment at {venv_path}")

    def _git_fetch(self, mirror_path: Path, prune: bool) -> None:
        args = ["git", "-C", str(mirror_path), "fetch", "--all"]
        if prune:
            args.append("--prune")
        self._run(args)
        self._log(f"✓ Updated bare mirror at {mirror_path}")

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
