"""Adapter for launching Python programs under debugpy."""

from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from debug_server.db import MetadataStore
from debug_server.runner import CommandSpec, WorkerSupervisor

from .tunnel import DebuggerTunnel, DebuggerTunnelManager


@dataclass(slots=True)
class DebugpyLaunchRequest:
    """Configuration for a debugpy session."""

    module: str | None = None
    script: str | None = None
    args: Sequence[str] = ()
    cwd: Path | None = None
    env: Mapping[str, str] | None = None
    wait_for_client: bool = True


@dataclass(slots=True)
class DebuggerLaunch:
    """Details about a debugger run."""

    tunnel: DebuggerTunnel
    command: CommandSpec


class DebugpyAdapter:
    """Prepare debugpy command invocations for the runner."""

    def __init__(
        self,
        supervisor: WorkerSupervisor,
        tunnel_manager: DebuggerTunnelManager,
        metadata_store: MetadataStore,
    ) -> None:
        self.supervisor = supervisor
        self.tunnel_manager = tunnel_manager
        self.metadata_store = metadata_store

    def start(self, session_id: str, lease: Any, request: DebugpyLaunchRequest) -> DebuggerLaunch:
        tunnel = self.tunnel_manager.open_tunnel(session_id, "debugpy")
        self.metadata_store.update_debugger_state(
            session_id,
            last_event="tunnel-ready",
            payload={"tunnel": tunnel.to_payload()},
        )
        argv = self._build_argv(request, tunnel)
        env = dict(request.env or {})
        env.setdefault("DEBUG_SESSION_TOKEN", tunnel.token)
        env.setdefault("DEBUG_SESSION_URI", tunnel.uri)
        command = CommandSpec(argv=argv, env=env, cwd=request.cwd, log_name="debugger")
        self.supervisor.run_command(session_id=session_id, spec=command, lease=lease)
        return DebuggerLaunch(tunnel=tunnel, command=command)

    @staticmethod
    def _build_argv(request: DebugpyLaunchRequest, tunnel: DebuggerTunnel) -> list[str]:
        if not request.module and not request.script:
            msg = "Either module or script must be specified"
            raise ValueError(msg)
        argv = [
            sys.executable,
            "-m",
            "debugpy",
            "--listen",
            f"{tunnel.host}:{tunnel.port}",
        ]
        if request.wait_for_client:
            argv.append("--wait-for-client")
        if request.module:
            argv.extend(["-m", request.module])
        elif request.script:
            argv.append(request.script)
        argv.extend(request.args)
        return argv


__all__ = ["DebugpyAdapter", "DebugpyLaunchRequest", "DebuggerLaunch"]
