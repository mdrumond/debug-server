from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.bootstrap import BootstrapConfig, BootstrapManager, EnvironmentSettings


def _base_config(tmp_path: Path, **overrides: object) -> BootstrapConfig:
    data = {
        "environment": {
            "name": "test-env",
            "use_conda": overrides.get("use_conda", False),
            "venv_path": str(tmp_path / ".venv"),
        },
        "repository": {
            "path": str(overrides.get("repo_path", tmp_path / "repo")),
        },
        "storage": {
            "data_dir": str(tmp_path / "data"),
            "sqlite_path": str(tmp_path / "data" / "metadata.db"),
        },
        "auth": {
            "token_environment_variable": overrides.get("token_env", "DEBUG_SERVER_TOKEN"),
        },
        "required_binaries": ["git"],
    }
    return BootstrapConfig.from_mapping(data)


def test_from_mapping_requires_repository_and_storage_sections() -> None:
    with pytest.raises(ValueError):
        BootstrapConfig.from_mapping({})


def test_prepare_storage_creates_sqlite_file(tmp_path: Path) -> None:
    config = _base_config(tmp_path)
    manager = BootstrapManager(config, dry_run=False)
    manager.prepare_storage()
    sqlite_path = Path(config.storage.sqlite_path)
    assert sqlite_path.exists()
    with sqlite3.connect(sqlite_path) as connection:
        assert connection.execute("select 1").fetchone() == (1,)


def test_prepare_repository_clones_local_mirror(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    subprocess.run(["git", "init"], cwd=repo_path, check=True)
    config = _base_config(tmp_path, repo_path=repo_path)
    manager = BootstrapManager(config, dry_run=False)
    manager.prepare_repository()
    assert (repo_path / ".git").exists()


def test_run_smoke_tests_warns_when_env_missing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config = _base_config(tmp_path, token_env="TEST_TOKEN_ENV")
    manager = BootstrapManager(config, dry_run=False)
    manager.prepare_storage()
    manager.run_smoke_tests()
    output = capsys.readouterr().out
    assert "TEST_TOKEN_ENV" in output
    assert "⚠️" in output


def test_dry_run_does_not_mutate_directories(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config = _base_config(tmp_path)
    manager = BootstrapManager(config, dry_run=True)
    manager.prepare_storage()
    assert not Path(config.storage.sqlite_path).exists()
    output = capsys.readouterr().out
    assert "[DRY-RUN]" in output


def test_installs_conda_when_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = _base_config(tmp_path, use_conda=True)
    config.required_binaries = []
    manager = BootstrapManager(config, dry_run=False)

    def fake_which(binary: str) -> str | None:
        if binary == "conda":
            return None
        return str(Path("/usr/bin") / binary)

    monkeypatch.setattr(shutil, "which", fake_which)

    installed_path = tmp_path / "miniconda" / "bin" / "conda"

    def fake_install(env: EnvironmentSettings) -> Path:
        installed_path.parent.mkdir(parents=True, exist_ok=True)
        installed_path.touch()
        return installed_path

    monkeypatch.setattr(manager, "_install_conda", fake_install)
    manager.ensure_required_binaries()
    assert config.environment.conda_command == str(installed_path)


def test_virtualenv_installs_pip_packages(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = _base_config(tmp_path, use_conda=False)
    env_file = tmp_path / "environment.yml"
    env_file.write_text(
        "\n".join(
            [
                "name: test-env",
                "dependencies:",
                "  - python=3.11",
                "  - pip",
                "  - pip:",
                "      - tomli-w",
                "      - debugpy",
            ]
        )
    )
    config.environment.conda_environment_file = str(env_file)
    manager = BootstrapManager(config, dry_run=False)
    commands: list[list[str]] = []

    def fake_run(args: list[str], capture_output: bool = False) -> str:
        commands.append(args)
        if args[:3] == [sys.executable, "-m", "venv"]:
            venv_dir = Path(args[-1])
            bin_dir = venv_dir / ("Scripts" if os.name == "nt" else "bin")
            bin_dir.mkdir(parents=True, exist_ok=True)
            python_name = "python.exe" if os.name == "nt" else "python"
            (bin_dir / python_name).write_text("#!/usr/bin/env python3")
        return ""

    monkeypatch.setattr(manager, "_run", fake_run)
    manager._prepare_virtualenv(Path(config.environment.venv_path))
    pip_commands = [cmd for cmd in commands if "pip" in cmd]
    assert pip_commands
    assert pip_commands[-1][-2:] == ["tomli-w", "debugpy"]
