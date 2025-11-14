from __future__ import annotations

import json
import os
import shutil
import sqlite3
import ssl
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


def test_prepare_repository_errors_on_invalid_git_dir(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    git_dir = repo_path / ".git"
    git_dir.mkdir(parents=True)
    config = _base_config(tmp_path, repo_path=repo_path)
    manager = BootstrapManager(config, dry_run=False)
    with pytest.raises(RuntimeError):
        manager.prepare_repository()


def test_run_smoke_tests_warns_when_env_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = _base_config(tmp_path, token_env="TEST_TOKEN_ENV")
    manager = BootstrapManager(config, dry_run=False)
    manager.prepare_storage()
    manager.run_smoke_tests()
    output = capsys.readouterr().out
    assert "TEST_TOKEN_ENV" in output
    assert "⚠️" in output


def test_dry_run_does_not_mutate_directories(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
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


def test_conda_env_exists_uses_json_listing(tmp_path: Path) -> None:
    config = _base_config(tmp_path)
    manager = BootstrapManager(config, dry_run=True)
    env_root = tmp_path / "miniconda" / "envs"
    listing = json.dumps(
        {
            "envs": [
                str(env_root / "test-env"),
                str(env_root / "other"),
            ]
        }
    )
    assert manager._conda_env_exists(listing, "test-env")
    assert not manager._conda_env_exists(listing, "missing")


def test_sets_conda_ssl_verify_from_requests_bundle(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = _base_config(tmp_path, use_conda=True)
    manager = BootstrapManager(config, dry_run=True)
    cert_path = tmp_path / "proxy-ca.crt"
    cert_path.write_text("dummy")
    monkeypatch.delenv("CONDA_SSL_VERIFY", raising=False)
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(cert_path))
    monkeypatch.setattr(manager, "_detect_system_certificate_bundle", lambda: None)

    manager._ensure_conda_ssl_verify()

    assert os.environ["CONDA_SSL_VERIFY"] == str(cert_path)
    assert os.environ["REQUESTS_CA_BUNDLE"] == str(cert_path)


def test_does_not_override_existing_conda_ssl_verify(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = _base_config(tmp_path, use_conda=True)
    manager = BootstrapManager(config, dry_run=True)
    cert_path = tmp_path / "proxy-ca.crt"
    cert_path.write_text("dummy")
    monkeypatch.setenv("CONDA_SSL_VERIFY", "false")
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(cert_path))

    manager._ensure_conda_ssl_verify()

    assert os.environ["CONDA_SSL_VERIFY"] == "false"


def test_combines_proxy_bundle_with_system_store(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = _base_config(tmp_path, use_conda=True)
    manager = BootstrapManager(config, dry_run=True)
    proxy_bundle = tmp_path / "proxy.crt"
    proxy_bundle.write_text("CUSTOM")
    system_bundle = tmp_path / "system.crt"
    system_bundle.write_text("SYSTEM")
    combined_path = tmp_path / "combined.pem"

    monkeypatch.delenv("CONDA_SSL_VERIFY", raising=False)
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(proxy_bundle))
    monkeypatch.setattr(manager, "_conda_certificate_bundle_path", lambda: combined_path)
    monkeypatch.setattr(manager, "_detect_system_certificate_bundle", lambda: str(system_bundle))

    manager._ensure_conda_ssl_verify()

    assert os.environ["CONDA_SSL_VERIFY"] == str(combined_path)
    assert combined_path.read_text() == "CUSTOM\nSYSTEM\n"
    assert os.environ["REQUESTS_CA_BUNDLE"] == str(combined_path)


def test_combines_proxy_bundle_with_system_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = _base_config(tmp_path, use_conda=True)
    manager = BootstrapManager(config, dry_run=True)
    proxy_bundle = tmp_path / "proxy.crt"
    proxy_bundle.write_text("CUSTOM")
    system_dir = tmp_path / "system-certs"
    system_dir.mkdir()
    (system_dir / "001.pem").write_text("FIRST")
    (system_dir / "002.pem").write_text("SECOND")
    combined_path = tmp_path / "combined.pem"

    monkeypatch.delenv("CONDA_SSL_VERIFY", raising=False)
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(proxy_bundle))
    monkeypatch.setattr(manager, "_conda_certificate_bundle_path", lambda: combined_path)
    monkeypatch.setattr(manager, "_detect_system_certificate_bundle", lambda: str(system_dir))

    manager._ensure_conda_ssl_verify()

    assert os.environ["CONDA_SSL_VERIFY"] == str(combined_path)
    assert combined_path.read_text() == "CUSTOM\nFIRST\nSECOND\n"


def test_populates_missing_certificate_environment_variables(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = _base_config(tmp_path, use_conda=True)
    manager = BootstrapManager(config, dry_run=True)
    proxy_bundle = tmp_path / "proxy.crt"
    proxy_bundle.write_text("CUSTOM")

    monkeypatch.delenv("CONDA_SSL_VERIFY", raising=False)
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("PIP_CERT", raising=False)
    monkeypatch.setenv("CODEX_PROXY_CERT", str(proxy_bundle))
    monkeypatch.setattr(manager, "_detect_system_certificate_bundle", lambda: None)

    manager._ensure_conda_ssl_verify()

    expected = str(proxy_bundle)
    assert os.environ["CONDA_SSL_VERIFY"] == expected
    assert os.environ["REQUESTS_CA_BUNDLE"] == expected
    assert os.environ["SSL_CERT_FILE"] == expected


def test_preserves_non_source_certificate_environment_variables(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = _base_config(tmp_path, use_conda=True)
    manager = BootstrapManager(config, dry_run=True)
    proxy_bundle = tmp_path / "proxy.crt"
    proxy_bundle.write_text("CUSTOM")
    locked_cert = tmp_path / "locked.crt"
    locked_cert.write_text("LOCKED")

    monkeypatch.delenv("CONDA_SSL_VERIFY", raising=False)
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(locked_cert))
    monkeypatch.setenv("SSL_CERT_FILE", str(locked_cert))
    monkeypatch.setenv("PIP_CERT", str(proxy_bundle))
    monkeypatch.setattr(manager, "_detect_system_certificate_bundle", lambda: None)

    manager._ensure_conda_ssl_verify()

    assert os.environ["PIP_CERT"] == str(proxy_bundle)
    assert os.environ["REQUESTS_CA_BUNDLE"] == str(locked_cert)
    assert os.environ["SSL_CERT_FILE"] == str(locked_cert)


def test_detects_system_certificate_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cert_dir = tmp_path / "certs"
    cert_dir.mkdir()

    class _Paths:
        openssl_cafile = None
        openssl_capath = str(cert_dir)

    monkeypatch.setattr(ssl, "get_default_verify_paths", lambda: _Paths)

    assert BootstrapManager._detect_system_certificate_bundle() == str(cert_dir)
