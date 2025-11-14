"""Model Context Protocol server for the Debug Server."""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from client import __version__
from client.config import ClientConfig, load_client_config
from client.sdk import DebugServerClient
from client.sdk.models import (
    DebugActionRequest,
    DebugActionResponse,
    LogEntry,
    RepositoryInitRequest,
    RepositoryInitResponse,
    Session,
    SessionCreateRequest,
)


@dataclass(frozen=True)
class ToolInfo:
    """Schema metadata for an MCP tool."""

    name: str
    description: str
    input_schema: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
        return payload


@dataclass(frozen=True)
class ToolResult:
    """Standard MCP tool response."""

    content: dict[str, Any]


class ToolStream(Iterator[dict[str, Any]]):
    """Streaming MCP response wrapper."""

    def __init__(self, iterator: Iterator[dict[str, Any]]) -> None:
        self._iterator = iterator

    def __iter__(self) -> ToolStream:
        return self

    def __next__(self) -> dict[str, Any]:
        return next(self._iterator)


ToolResponse = ToolResult | ToolStream


@dataclass(frozen=True)
class _ToolBinding:
    info: ToolInfo
    handler: Callable[[dict[str, Any]], ToolResponse]


class DebugServerMCPServer:
    """Registers the Debug Server tools for the Model Context Protocol."""

    def __init__(
        self,
        config: ClientConfig,
        *,
        client_factory: Callable[[ClientConfig], DebugServerClient] | None = None,
    ) -> None:
        self._config = config
        self._client_factory = client_factory or self._default_client_factory
        self._client: DebugServerClient | None = None
        self._tool_bindings = self._build_tool_bindings()

    @staticmethod
    def _default_client_factory(config: ClientConfig) -> DebugServerClient:
        if config.token is None:
            raise RuntimeError(
                "MCP server requires an API token. Set DEBUG_SERVER_TOKEN or "
                "provide one via the config file."
            )
        return DebugServerClient(
            base_url=config.base_url,
            token=config.token,
            verify_tls=config.verify_tls,
        )

    def _ensure_client(self) -> DebugServerClient:
        if self._client is None:
            self._client = self._client_factory(self._config)
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def tools(self) -> list[ToolInfo]:
        return [binding.info for binding in self._tool_bindings.values()]

    def manifest(self) -> dict[str, Any]:
        return {
            "name": "debug-server",
            "version": __version__,
            "tools": [info.to_payload() for info in self.tools()],
            "endpoints": {
                "repository": f"{self._config.base_url}/repository",
                "sessions": f"{self._config.base_url}/sessions",
            },
        }

    def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolResponse:
        if name not in self._tool_bindings:
            raise ValueError(f"Unknown MCP tool '{name}'.")
        binding = self._tool_bindings[name]
        return binding.handler(arguments)

    def _build_tool_bindings(self) -> dict[str, _ToolBinding]:
        return {
            "debug-server.repository.init": _ToolBinding(
                info=ToolInfo(
                    name="debug-server.repository.init",
                    description="Initialize the tracked repository and dependency manifests.",
                    input_schema={
                        "type": "object",
                        "required": ["remote_url"],
                        "properties": {
                            "remote_url": {"type": "string", "format": "uri"},
                            "default_branch": {"type": "string"},
                            "dependency_manifests": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": [],
                            },
                            "allow_self_signed": {"type": "boolean", "default": False},
                        },
                    },
                ),
                handler=self._handle_repository_init,
            ),
            "debug-server.session.create": _ToolBinding(
                info=ToolInfo(
                    name="debug-server.session.create",
                    description="Create a new debug session at a commit + optional patch.",
                    input_schema={
                        "type": "object",
                        "required": ["commit"],
                        "properties": {
                            "commit": {"type": "string"},
                            "commands": {"type": "array", "items": {"type": "string"}},
                            "patch": {"type": "string"},
                            "metadata": {
                                "type": "object",
                                "additionalProperties": {"type": "string"},
                            },
                        },
                    },
                ),
                handler=self._handle_session_create,
            ),
            "debug-server.session.info": _ToolBinding(
                info=ToolInfo(
                    name="debug-server.session.info",
                    description="Fetch metadata for an existing session.",
                    input_schema={
                        "type": "object",
                        "required": ["session_id"],
                        "properties": {"session_id": {"type": "string"}},
                    },
                ),
                handler=self._handle_session_info,
            ),
            "debug-server.session.logs": _ToolBinding(
                info=ToolInfo(
                    name="debug-server.session.logs",
                    description="Stream structured logs for a session.",
                    input_schema={
                        "type": "object",
                        "required": ["session_id"],
                        "properties": {
                            "session_id": {"type": "string"},
                            "follow": {"type": "boolean", "default": False},
                        },
                    },
                ),
                handler=self._handle_session_logs,
            ),
            "debug-server.session.commands": _ToolBinding(
                info=ToolInfo(
                    name="debug-server.session.commands",
                    description="List commands queued/executed by the session.",
                    input_schema={
                        "type": "object",
                        "required": ["session_id"],
                        "properties": {"session_id": {"type": "string"}},
                    },
                ),
                handler=self._handle_session_commands,
            ),
            "debug-server.session.debug": _ToolBinding(
                info=ToolInfo(
                    name="debug-server.session.debug",
                    description="Send a debugger control action to an existing session.",
                    input_schema={
                        "type": "object",
                        "required": ["session_id", "action"],
                        "properties": {
                            "session_id": {"type": "string"},
                            "action": {"type": "string"},
                            "payload": {
                                "type": "object",
                                "additionalProperties": {"type": "string"},
                                "default": {},
                            },
                        },
                    },
                ),
                handler=self._handle_debug_action,
            ),
        }

    def _handle_repository_init(self, arguments: dict[str, Any]) -> ToolResult:
        remote_url = _require_str(arguments, "remote_url")
        default_branch = _optional_str(arguments.get("default_branch"))
        manifests = _string_list(arguments.get("dependency_manifests", []))
        allow_self_signed = bool(arguments.get("allow_self_signed", False))
        request = RepositoryInitRequest(
            remote_url=remote_url,
            default_branch=default_branch,
            dependency_manifests=manifests,
            allow_self_signed=allow_self_signed,
        )
        response = self._ensure_client().initialize_repository(request)
        return ToolResult(content=_repository_init_to_dict(response))

    def _handle_session_create(self, arguments: dict[str, Any]) -> ToolResult:
        commit = _require_str(arguments, "commit")
        commands = _string_list(arguments.get("commands", []))
        patch = _optional_str(arguments.get("patch"))
        metadata = _string_dict(arguments.get("metadata", {}))
        request = SessionCreateRequest(
            commit=commit, commands=commands, patch=patch, metadata=metadata
        )
        session = self._ensure_client().create_session(request)
        return ToolResult(content=_session_to_dict(session))

    def _handle_session_info(self, arguments: dict[str, Any]) -> ToolResult:
        session_id = _require_str(arguments, "session_id")
        session = self._ensure_client().get_session(session_id)
        return ToolResult(content=_session_to_dict(session))

    def _handle_session_logs(self, arguments: dict[str, Any]) -> ToolStream:
        session_id = _require_str(arguments, "session_id")
        follow = bool(arguments.get("follow", False))
        iterator = self._ensure_client().stream_session_logs(session_id, follow=follow)
        return ToolStream(_log_iterator(iterator))

    def _handle_session_commands(self, arguments: dict[str, Any]) -> ToolResult:
        session_id = _require_str(arguments, "session_id")
        commands = list(self._ensure_client().list_commands(session_id))
        return ToolResult(content={"commands": commands, "session_id": session_id})

    def _handle_debug_action(self, arguments: dict[str, Any]) -> ToolResult:
        session_id = _require_str(arguments, "session_id")
        action = _require_str(arguments, "action")
        payload = _string_dict(arguments.get("payload", {}))
        request = DebugActionRequest(action=action, payload=payload)
        response = self._ensure_client().send_debug_action(session_id, request)
        return ToolResult(content=_debug_response_to_dict(response, session_id))


def _require_str(arguments: dict[str, Any], key: str) -> str:
    if key not in arguments:
        raise ValueError(f"'{key}' is required")
    value = arguments[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{key}' must be a non-empty string")
    return value


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        raise ValueError("Expected a list of strings")
    return [str(item) for item in value]


def _string_dict(value: Any) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("Expected an object with string values")
    return {str(k): str(v) for k, v in value.items()}


def _session_to_dict(session: Session) -> dict[str, Any]:
    return {
        "session_id": session.session_id,
        "status": session.status,
        "commit": session.commit,
        "commands": list(session.commands),
        "metadata": dict(session.metadata),
        "created_at": session.created_at.isoformat(),
    }


def _repository_init_to_dict(response: RepositoryInitResponse) -> dict[str, Any]:
    return {
        "repository_id": response.repository_id,
        "default_branch": response.default_branch,
        "worktree_count": response.worktree_count,
    }


def _log_iterator(entries: Iterator[LogEntry]) -> Iterator[dict[str, Any]]:
    for entry in entries:
        yield {
            "message": entry.message,
            "stream": entry.stream,
            "timestamp": entry.timestamp.isoformat(),
            "text": entry.to_text(),
        }


def _debug_response_to_dict(response: DebugActionResponse, session_id: str) -> dict[str, Any]:
    payload = {
        "session_id": session_id,
        "status": response.status,
    }
    if response.detail is not None:
        payload["detail"] = response.detail
    return payload


def load_mcp_config(path: Path | None) -> ClientConfig:
    base = load_client_config()
    if path is None:
        return base
    resolved = Path(path).expanduser()
    if not resolved.exists():  # pragma: no cover - defensive guard for operators
        raise FileNotFoundError(f"MCP config {resolved} does not exist")
    data = tomllib.loads(resolved.read_text())
    overrides: dict[str, Any] = {}
    if "base_url" in data:
        overrides["base_url"] = str(data["base_url"])
    if "token" in data:
        overrides["token"] = str(data["token"])
    if "verify_tls" in data:
        overrides["verify_tls"] = bool(data["verify_tls"])
    return base.merged(**overrides)


def run_stdio_event_loop(server: DebugServerMCPServer) -> None:
    """Run a lightweight stdio loop for manual MCP testing."""

    def _write(payload: dict[str, Any]) -> None:
        sys.stdout.write(json.dumps(payload) + "\n")
        sys.stdout.flush()

    try:
        for raw_line in sys.stdin:
            line = raw_line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError as exc:  # pragma: no cover - defensive
                _write({"id": None, "status": "error", "error": str(exc)})
                continue
            req_id = request.get("id")
            tool_name = request.get("tool")
            if not isinstance(tool_name, str):
                _write({"id": req_id, "status": "error", "error": "Missing tool name"})
                continue
            arguments = request.get("arguments") or {}
            if not isinstance(arguments, dict):
                _write({"id": req_id, "status": "error", "error": "Arguments must be an object"})
                continue
            try:
                response = server.call_tool(tool_name, arguments)
            except Exception as exc:  # pragma: no cover - surfaced to MCP client
                _write({"id": req_id, "status": "error", "error": str(exc)})
                continue
            if isinstance(response, ToolStream):
                for chunk in response:
                    _write({"id": req_id, "status": "stream", "chunk": chunk})
                _write({"id": req_id, "status": "done"})
            else:
                _write({"id": req_id, "status": "ok", "result": response.content})
    finally:
        server.close()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Debug Server MCP entry point")
    parser.add_argument("--config", type=Path, help="Path to MCP config (toml)")
    parser.add_argument("--manifest", action="store_true", help="Print manifest JSON and exit")
    parser.add_argument("--tool", help="Invoke a tool once (debugging only)")
    parser.add_argument("--args", help="JSON encoded arguments for --tool", default="{}")
    parser.add_argument(
        "--stdio", action="store_true", help="Start the stdio loop for MCP integrations"
    )
    parsed = parser.parse_args(argv)

    config = load_mcp_config(parsed.config)
    server = DebugServerMCPServer(config=config)

    if parsed.manifest:
        print(json.dumps(server.manifest(), indent=2))
        return 0

    if parsed.tool:
        arguments = json.loads(parsed.args or "{}")
        response = server.call_tool(parsed.tool, arguments)
        if isinstance(response, ToolStream):
            for chunk in response:
                print(json.dumps(chunk))
        else:
            print(json.dumps(response.content, indent=2))
        return 0

    if parsed.stdio:
        run_stdio_event_loop(server)
        return 0

    parser.error("Select --manifest, --tool, or --stdio to interact with the MCP server.")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
