from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
import click
from click.testing import CliRunner

from client.cli import cloud
from client.cli.cloud import EncryptedStateStore, TerraformInvoker, require_human_operator


def test_require_human_operator_blocks_ci(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CI", "1")
    with pytest.raises(click.UsageError):
        require_human_operator()


def test_require_human_operator_allows_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setenv("DEBUG_SERVER_OPERATOR_ALLOW", "1")
    require_human_operator()


@pytest.fixture()
def operator_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    monkeypatch.setenv("DEBUG_SERVER_OPERATOR_ALLOW", "1")
    monkeypatch.setenv("DEBUG_SERVER_OPERATOR_KEY", "super-secret")
    monkeypatch.setenv("DEBUG_SERVER_HOME", str(tmp_path))
    return dict(os.environ)


def test_tfvars_written_and_state_persisted(operator_env: dict[str, str]) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cloud.cloud,
        [
            "up",
            "--provider",
            "hetzner",
            "--docker-host",
            "tcp://10.0.0.5:2376",
            "--image",
            "ghcr.io/example/debug-server:latest",
            "--env",
            "ENV=prod",
            "--port",
            "8000:8000",
        ],
        env=operator_env,
    )
    assert result.exit_code == 0, result.output

    tfvars = Path("infra/terraform/hetzner_docker_node/terraform.tfvars.json")
    assert tfvars.exists()
    payload = tfvars.read_text()
    assert "hetzner" in payload
    assert "ghcr.io/example" in payload

    state_dir = Path(operator_env["DEBUG_SERVER_HOME"]) / "cloud"
    files = list(state_dir.glob("*.json.enc"))
    assert files, "Encrypted state should be persisted"


def test_encrypted_store_round_trip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = EncryptedStateStore(base_dir=tmp_path)
    monkeypatch.setenv("DEBUG_SERVER_OPERATOR_KEY", "roundtrip")
    path = store.save("stack", {"example": True})
    loaded = store.load("stack")
    assert loaded == {"example": True}
    assert path.exists()


def test_terraform_invoker_runs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: "terraform")
    calls: list[tuple[list[str], Path, bool, bool]] = []

    def fake_run(
        cmd: list[str], cwd: Path, check: bool, capture_output: bool
    ) -> subprocess.CompletedProcess[list[str]]:
        calls.append((cmd, cwd, check, capture_output))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    invoker = TerraformInvoker(working_dir=tmp_path)
    invoker.run("plan")

    assert calls == [(["terraform", "plan"], tmp_path, True, False)]


def test_terraform_invoker_surfaces_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: "terraform")

    def fake_run(
        cmd: list[str], cwd: Path, check: bool, capture_output: bool
    ) -> subprocess.CompletedProcess[list[str]]:
        raise subprocess.CalledProcessError(returncode=2, cmd=cmd)

    monkeypatch.setattr(subprocess, "run", fake_run)

    invoker = TerraformInvoker(working_dir=tmp_path)
    with pytest.raises(click.ClickException):
        invoker.run("apply")
