from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from debug_server.db import MetadataStore
from debug_server.runner.debuggers import (
    DebuggerTunnelManager,
    GDBAdapter,
    LLDBAdapter,
    NativeDebuggerLaunchRequest,
)


@dataclass
class FakeLease:
    path: Path = Path(".")


class FakeSupervisor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object, object]] = []

    def run_command(self, session_id: str, spec, lease) -> None:  # pragma: no cover - trivial
        self.calls.append((session_id, spec, lease))


def test_gdb_command_shape(metadata_store: MetadataStore) -> None:
    tunnel_manager = DebuggerTunnelManager(metadata_store, host="localhost")
    supervisor = FakeSupervisor()
    adapter = GDBAdapter(supervisor, tunnel_manager, metadata_store)

    request = NativeDebuggerLaunchRequest(
        binary="/bin/ls", args=["-l", "/usr"], env={"FOO": "bar"}
    )
    adapter.start("sess-gdb", FakeLease(), request)

    assert len(supervisor.calls) == 1
    session_id, command, _ = supervisor.calls[0]
    assert session_id == "sess-gdb"
    assert command.argv[0] == "gdbserver"
    assert command.argv[1].startswith("localhost:")
    assert command.argv[2] == "/bin/ls"
    assert command.env["FOO"] == "bar"
    assert "DEBUG_SESSION_TOKEN" in command.env

    state = metadata_store.get_debugger_state("sess-gdb")
    assert state is not None
    assert state.last_event == "tunnel-ready"
    assert "tunnel" in state.payload


def test_lldb_command_shape(metadata_store: MetadataStore) -> None:
    tunnel_manager = DebuggerTunnelManager(metadata_store, host="localhost")
    supervisor = FakeSupervisor()
    adapter = LLDBAdapter(supervisor, tunnel_manager, metadata_store)

    request = NativeDebuggerLaunchRequest(
        binary="/bin/bash",
        args=["-c", "echo hi"],
        env={"FOO": "bar"},
    )
    adapter.start("sess-lldb", FakeLease(), request)

    assert len(supervisor.calls) == 1
    session_id, command, _ = supervisor.calls[0]
    assert session_id == "sess-lldb"
    assert command.argv[:2] == ["lldb-server", "gdbserver"]
    assert command.argv[2].startswith("localhost:")
    assert command.argv[3] == "/bin/bash"
    assert command.env["FOO"] == "bar"
    assert "DEBUG_SESSION_TOKEN" in command.env

    state = metadata_store.get_debugger_state("sess-lldb")
    assert state is not None
    assert state.last_event == "tunnel-ready"
    assert "tunnel" in state.payload
