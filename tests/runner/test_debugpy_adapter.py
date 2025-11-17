from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from debug_server.db import MetadataStore
from debug_server.runner.debuggers import (
    DebuggerTunnelManager,
    DebugpyAdapter,
    DebugpyLaunchRequest,
)


@dataclass
class FakeLease:
    path: Path = Path(".")


class FakeSupervisor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object, object]] = []

    def run_command(self, session_id: str, spec, lease) -> None:  # pragma: no cover - trivial
        self.calls.append((session_id, spec, lease))


def test_debugpy_command_shape(metadata_store: MetadataStore) -> None:
    tunnel_manager = DebuggerTunnelManager(metadata_store, host="localhost")
    supervisor = FakeSupervisor()
    adapter = DebugpyAdapter(
        supervisor=supervisor,
        tunnel_manager=tunnel_manager,
        metadata_store=metadata_store,
    )
    request = DebugpyLaunchRequest(
        module="app.main",
        args=["--flag"],
        wait_for_client=False,
        env={"FOO": "bar"},
    )
    adapter.start("sess-1", FakeLease(), request)

    assert len(supervisor.calls) == 1
    session_id, command, _ = supervisor.calls[0]
    assert session_id == "sess-1"
    assert command.argv[:4] == [sys.executable, "-m", "debugpy", "--listen"]
    assert "--wait-for-client" not in command.argv
    assert "-m" in command.argv
    assert "app.main" in command.argv
    assert command.env["FOO"] == "bar"
    assert "DEBUG_SESSION_TOKEN" in command.env

    state = metadata_store.get_debugger_state("sess-1")
    assert state is not None
    assert state.last_event == "tunnel-ready"
    assert "tunnel" in state.payload


def test_debugpy_requires_module_or_script(metadata_store: MetadataStore) -> None:
    tunnel_manager = DebuggerTunnelManager(metadata_store, host="localhost")
    adapter = DebugpyAdapter(
        supervisor=FakeSupervisor(),
        tunnel_manager=tunnel_manager,
        metadata_store=metadata_store,
    )
    request = DebugpyLaunchRequest(wait_for_client=False)

    with pytest.raises(ValueError, match="Either module or script must be specified"):
        adapter.start("sess-2", FakeLease(), request)
