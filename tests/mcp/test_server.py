from __future__ import annotations

import json
import sys
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from client.config import ClientConfig  # noqa: E402
from client.mcp import DebugServerMCPServer, ToolStream, load_mcp_config  # noqa: E402
from client.sdk.models import (  # noqa: E402
    DebugActionResponse,
    LogEntry,
    RepositoryInitRequest,
    RepositoryInitResponse,
    Session,
    SessionCreateRequest,
)


class DummyClient:
    def __init__(self) -> None:
        self.init_request: RepositoryInitRequest | None = None
        self.session_request: SessionCreateRequest | None = None
        self.requested_session: str | None = None
        self.streamed_session: tuple[str, bool] | None = None
        self.command_session: str | None = None
        self.debug_action: tuple[str, str] | None = None

    def close(self) -> None:  # pragma: no cover - lifecycle handled elsewhere
        pass

    def initialize_repository(self, request: RepositoryInitRequest) -> RepositoryInitResponse:
        self.init_request = request
        return RepositoryInitResponse(
            repository_id="repo-1", default_branch="main", worktree_count=2
        )

    def create_session(self, request: SessionCreateRequest) -> Session:
        self.session_request = request
        return Session(
            session_id="sess-1",
            status="running",
            commit=request.commit,
            commands=list(request.commands),
            created_at=datetime.now(UTC),
            metadata=request.metadata,
        )

    def get_session(self, session_id: str) -> Session:
        self.requested_session = session_id
        return Session(
            session_id=session_id,
            status="running",
            commit="main",
            commands=["pytest"],
            created_at=datetime(2024, 7, 30, tzinfo=UTC),
            metadata={"ticket": "123"},
        )

    def stream_session_logs(self, session_id: str, *, follow: bool = False) -> Iterator[LogEntry]:
        self.streamed_session = (session_id, follow)
        yield LogEntry(message="line", stream="stdout", timestamp=datetime.now(UTC))

    def list_commands(self, session_id: str) -> list[str]:
        self.command_session = session_id
        return ["pytest", "ruff check"]

    def send_debug_action(self, session_id: str, action) -> DebugActionResponse:
        self.debug_action = (session_id, action.action)
        return DebugActionResponse(status="ok", detail="continued")


@pytest.fixture()
def server_and_client() -> Iterator[tuple[DebugServerMCPServer, DummyClient]]:
    client = DummyClient()
    config = ClientConfig(base_url="https://example.com", token="abc", verify_tls=True)

    def _factory(config_in: ClientConfig) -> DummyClient:
        assert config_in.token == "abc"
        return client

    server = DebugServerMCPServer(config=config, client_factory=_factory)
    yield server, client
    server.close()


def test_manifest_lists_all_tools(server_and_client: tuple[DebugServerMCPServer, DummyClient]):
    server, _ = server_and_client
    manifest = server.manifest()
    tool_names = {tool["name"] for tool in manifest["tools"]}
    assert "debug-server.session.logs" in tool_names
    assert manifest["endpoints"]["sessions"].endswith("/sessions")


def test_repository_init_invokes_sdk(server_and_client: tuple[DebugServerMCPServer, DummyClient]):
    server, client = server_and_client
    result = server.call_tool(
        "debug-server.repository.init",
        {"remote_url": "https://example.com/repo.git", "dependency_manifests": ["conda", "npm"]},
    )
    assert client.init_request is not None
    assert client.init_request.dependency_manifests == ["conda", "npm"]
    assert result.content["repository_id"] == "repo-1"


def test_session_create_invokes_sdk(server_and_client: tuple[DebugServerMCPServer, DummyClient]):
    server, client = server_and_client
    result = server.call_tool(
        "debug-server.session.create",
        {
            "commit": "abc123",
            "commands": ["pytest"],
            "patch": "diff --git a b",
            "metadata": {"ticket": "42"},
        },
    )
    assert client.session_request is not None
    assert client.session_request.commit == "abc123"
    assert result.content["session_id"] == "sess-1"


def test_session_info_invokes_sdk(server_and_client: tuple[DebugServerMCPServer, DummyClient]):
    server, client = server_and_client
    result = server.call_tool("debug-server.session.info", {"session_id": "sess-2"})
    assert client.requested_session == "sess-2"
    assert result.content["session_id"] == "sess-2"


def test_session_logs_stream(server_and_client: tuple[DebugServerMCPServer, DummyClient]):
    server, client = server_and_client
    response = server.call_tool("debug-server.session.logs", {"session_id": "sess-3"})
    assert isinstance(response, ToolStream)
    chunks = list(response)
    assert chunks[0]["stream"] == "stdout"
    assert client.streamed_session == ("sess-3", False)


def test_debug_action_payload(server_and_client: tuple[DebugServerMCPServer, DummyClient]):
    server, client = server_and_client
    result = server.call_tool(
        "debug-server.session.debug",
        {"session_id": "sess-9", "action": "continue", "payload": {"thread": "1"}},
    )
    assert client.debug_action == ("sess-9", "continue")
    assert result.content["status"] == "ok"


def test_cli_manifest_command(monkeypatch, tmp_path, capsys):
    config_path = tmp_path / "mcp.toml"
    config_path.write_text(
        """
base_url = "https://example.com"
token = "abc"
verify_tls = true
""".strip()
    )
    monkeypatch.setenv("DEBUG_SERVER_HOME", str(tmp_path))
    from client.mcp.server import main

    rc = main(["--config", str(config_path), "--manifest"])
    assert rc == 0
    output = capsys.readouterr().out.strip()
    manifest = json.loads(output)
    assert manifest["name"] == "debug-server"


def test_load_mcp_config_overrides(monkeypatch, tmp_path):
    default = tmp_path / "config.toml"
    default.write_text(
        """
base_url = "https://example.com"
token = "saved"
verify_tls = false
""".strip()
    )
    monkeypatch.setenv("DEBUG_SERVER_HOME", str(tmp_path))
    config = load_mcp_config(default)
    assert config.base_url == "https://example.com"
    assert config.token == "saved"
    assert config.verify_tls is False


def test_session_commands_tool(server_and_client: tuple[DebugServerMCPServer, DummyClient]):
    server, client = server_and_client
    result = server.call_tool("debug-server.session.commands", {"session_id": "sess-4"})
    assert client.command_session == "sess-4"
    assert result.content["commands"] == ["pytest", "ruff check"]
