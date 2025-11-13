from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.bootstrap import BootstrapConfig, BootstrapManager


def _base_config(tmp_path: Path, **overrides: object) -> BootstrapConfig:
    data = {
        "environment": {
            "name": "test-env",
            "use_conda": overrides.get("use_conda", False),
            "venv_path": str(tmp_path / ".venv"),
        },
        "repository": {
            "upstream_url": overrides.get("upstream_url", "https://example.invalid/repo.git"),
            "mirror_path": str(tmp_path / "mirror.git"),
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
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True)
    config = _base_config(
        tmp_path,
        upstream_url=str(remote),
    )
    manager = BootstrapManager(config, dry_run=False)
    manager.prepare_repository()
    mirror_path = Path(config.repository.mirror_path)
    assert (mirror_path / "HEAD").exists()


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
