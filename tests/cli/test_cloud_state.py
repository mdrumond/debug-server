import os
from pathlib import Path

import click
import pytest

from client.cli.cloud import EncryptedStateStore
from client.cli.cloud_state import CloudInventory, ServerRecord, SessionRecord


@pytest.fixture()
def operator_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    monkeypatch.setenv("DEBUG_SERVER_OPERATOR_ALLOW", "1")
    monkeypatch.setenv("DEBUG_SERVER_OPERATOR_KEY", "inventory-secret")
    monkeypatch.setenv("DEBUG_SERVER_HOME", str(tmp_path))
    return dict(os.environ)


def test_inventory_records_and_lists_servers(operator_env: dict[str, str], tmp_path: Path) -> None:
    store = EncryptedStateStore()
    inventory = CloudInventory(store)

    working_dir = tmp_path / "stack"
    tfvars = working_dir / "terraform.tfvars.json"

    record = ServerRecord(
        stack_name="hetzner-prod",
        provider="hetzner",
        docker_host="tcp://10.0.0.10:2376",
        app_image="ghcr.io/example/debug-server:latest",
        app_ports=["8000:8000"],
        app_env={"ENV": "prod"},
        token="runner-token",  # noqa: S106 - test fixture token
        working_dir=str(working_dir),
        tfvars=str(tfvars),
    )
    inventory.record_server(record)

    listed = inventory.list_servers()
    assert len(listed) == 1
    assert listed[0].stack_name == "hetzner-prod"
    assert listed[0].provider == "hetzner"

    inventory.remove_server("hetzner-prod")
    assert not inventory.list_servers()


def test_inventory_session_round_trip(operator_env: dict[str, str], tmp_path: Path) -> None:
    store = EncryptedStateStore()
    inventory = CloudInventory(store)
    working_dir = tmp_path / "sandbox"
    tfvars = working_dir / "terraform.tfvars.json"
    inventory.record_server(
        ServerRecord(
            stack_name="sandbox",
            provider="hetzner",
            docker_host="tcp://10.0.0.11:2376",
            app_image="ghcr.io/example/debug-server:latest",
            app_ports=[],
            app_env={},
            token=None,
            working_dir=str(working_dir),
            tfvars=str(tfvars),
        )
    )

    session = SessionRecord(
        session_id="abc123",
        status="active",
        owner="operator",
        token="token-xyz",  # noqa: S106 - test fixture token
    )
    inventory.upsert_session("sandbox", session)

    refreshed = inventory.get_server("sandbox")
    assert refreshed is not None
    assert refreshed.sessions["abc123"].status == "active"

    inventory.remove_session("sandbox", "abc123")
    refreshed = inventory.get_server("sandbox")
    assert refreshed is not None
    assert refreshed.sessions == {}


def test_inventory_decryption_failure_is_surfaced(
    operator_env: dict[str, str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    store = EncryptedStateStore()
    inventory = CloudInventory(store)

    working_dir = tmp_path / "broken"
    tfvars = working_dir / "terraform.tfvars.json"

    inventory.record_server(
        ServerRecord(
            stack_name="broken",  # will be unreadable after the key change
            provider="hetzner",
            docker_host="tcp://10.0.0.12:2376",
            app_image="ghcr.io/example/debug-server:latest",
            app_ports=[],
            app_env={},
            token=None,
            working_dir=str(working_dir),
            tfvars=str(tfvars),
        )
    )

    monkeypatch.setenv("DEBUG_SERVER_OPERATOR_KEY", "wrong-key")

    with pytest.raises(click.UsageError, match="Failed to decrypt cloud inventory"):
        inventory.list_servers()
