"""Adapter for launching binaries under gdbserver."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from debug_server.db import MetadataStore
from debug_server.runner import CommandSpec, WorkerSupervisor

from .debugpy_adapter import DebuggerLaunch
from .tunnel import DebuggerTunnelManager


@dataclass(slots=True)
class NativeDebuggerLaunchRequest:
    """Launch configuration for native debuggers."""

    binary: str
    args: Sequence[str] = ()
    cwd: Path | None = None
    env: Mapping[str, str] | None = None


class GDBAdapter:
    """Prepare gdbserver command invocations for the runner."""

    def __init__(
        self,
        supervisor: WorkerSupervisor,
        tunnel_manager: DebuggerTunnelManager,
        metadata_store: MetadataStore,
    ) -> None:
        self.supervisor = supervisor
        self.tunnel_manager = tunnel_manager
        self.metadata_store = metadata_store

    def start(
        self, session_id: str, lease: Any, request: NativeDebuggerLaunchRequest
    ) -> DebuggerLaunch:
        tunnel = self.tunnel_manager.open_tunnel(session_id, "gdb")
        self.metadata_store.update_debugger_state(
            session_id,
            last_event="tunnel-ready",
            payload={"tunnel": tunnel.to_payload()},
        )
        env = dict(request.env or {})
        env.setdefault("DEBUG_SESSION_TOKEN", tunnel.token)
        env.setdefault("DEBUG_SESSION_URI", tunnel.uri)
        argv = [
            "gdbserver",
            f"{tunnel.host}:{tunnel.port}",
            request.binary,
            *request.args,
        ]
        command = CommandSpec(argv=argv, env=env, cwd=request.cwd, log_name="debugger")
        self.supervisor.run_command(session_id=session_id, spec=command, lease=lease)
        return DebuggerLaunch(tunnel=tunnel, command=command)


__all__ = ["GDBAdapter", "NativeDebuggerLaunchRequest"]
