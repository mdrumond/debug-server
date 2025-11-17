import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from client.cli import cloud


@pytest.fixture()
def operator_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    monkeypatch.setenv("DEBUG_SERVER_OPERATOR_ALLOW", "1")
    monkeypatch.setenv("DEBUG_SERVER_OPERATOR_KEY", "session-secret")
    monkeypatch.setenv("DEBUG_SERVER_HOME", str(tmp_path))
    return dict(os.environ)


def _launch_stack(runner: CliRunner, operator_env: dict[str, str], stack_dir: Path) -> None:
    stack_dir.mkdir()
    result = runner.invoke(
        cloud.cloud,
        [
            "up",
            "--provider",
            "hetzner",
            "--stack-name",
            "stack-a",
            "--docker-host",
            "tcp://10.0.0.5:2376",
            "--image",
            "ghcr.io/example/debug-server:latest",
            "--env",
            "ENV=prod",
            "--port",
            "8000:8000",
            "--stack-dir",
            str(stack_dir),
        ],
        env=operator_env,
    )
    assert result.exit_code == 0, result.output


def test_cloud_list_and_status(operator_env: dict[str, str], tmp_path: Path) -> None:
    runner = CliRunner()
    stack_dir = tmp_path / "stack-a"
    _launch_stack(runner, operator_env, stack_dir)

    list_result = runner.invoke(cloud.cloud, ["list"], env=operator_env)
    assert "stack-a" in list_result.output

    status_result = runner.invoke(
        cloud.cloud, ["status", "--stack-name", "stack-a"], env=operator_env
    )
    assert status_result.exit_code == 0
    assert "Docker host: tcp://10.0.0.5:2376" in status_result.output


def test_cloud_sessions_round_trip(operator_env: dict[str, str], tmp_path: Path) -> None:
    runner = CliRunner()
    stack_dir = tmp_path / "stack-a"
    _launch_stack(runner, operator_env, stack_dir)

    add_result = runner.invoke(
        cloud.cloud,
        [
            "sessions",
            "--stack-name",
            "stack-a",
            "--session-id",
            "abc123",
            "--status",
            "active",
            "--owner",
            "operator",
        ],
        env=operator_env,
    )
    assert add_result.exit_code == 0, add_result.output

    list_result = runner.invoke(
        cloud.cloud, ["sessions", "--stack-name", "stack-a"], env=operator_env
    )
    assert "abc123" in list_result.output
    assert "operator" in list_result.output

    drain_result = runner.invoke(
        cloud.cloud,
        [
            "sessions",
            "--stack-name",
            "stack-a",
            "--session-id",
            "abc123",
            "--drain",
        ],
        env=operator_env,
    )
    assert drain_result.exit_code == 0

    delete_result = runner.invoke(
        cloud.cloud,
        [
            "sessions",
            "--stack-name",
            "stack-a",
            "--session-id",
            "abc123",
            "--delete",
        ],
        env=operator_env,
    )
    assert delete_result.exit_code == 0

    final_list = runner.invoke(
        cloud.cloud, ["sessions", "--stack-name", "stack-a"], env=operator_env
    )
    assert "no sessions recorded" in final_list.output
