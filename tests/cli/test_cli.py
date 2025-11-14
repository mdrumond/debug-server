from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

from click.testing import CliRunner

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import importlib

cli_main = importlib.import_module("client.cli.main")
from client.sdk.models import (
    ArtifactMetadata,
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
        self.logs_follow: bool | None = None
        self.artifact_requested: tuple[str, str] | None = None
        self.debug_actions: list[str] = []

    def close(self) -> None:  # pragma: no cover - click handles lifecycle
        pass

    def initialize_repository(self, request):
        self.init_request = request
        return RepositoryInitResponse(
            repository_id="repo-1",
            default_branch=request.default_branch or "main",
            worktree_count=3,
        )

    def create_session(self, request: SessionCreateRequest) -> Session:
        self.session_request = request
        return Session(
            session_id="sess-123",
            status="running",
            commit=request.commit,
            commands=list(request.commands),
            created_at=datetime.now(timezone.utc),
            metadata=request.metadata,
        )

    def stream_session_logs(self, session_id: str, *, follow: bool = False):
        self.logs_follow = follow
        yield LogEntry(message="log-line", stream="stdout", timestamp=datetime.now(timezone.utc))

    def send_debug_action(self, session_id: str, action):
        self.debug_actions.append(action.action)
        return DebugActionResponse(status=action.action, detail=None)

    def download_artifact(self, session_id: str, artifact_id: str):
        self.artifact_requested = (session_id, artifact_id)
        metadata = ArtifactMetadata(
            artifact_id=artifact_id,
            filename="artifact.txt",
            content_type="text/plain",
            size=12,
        )
        return metadata, b"hello-world!"


def _runner(monkeypatch, dummy: DummyClient):
    monkeypatch.setattr(cli_main, "DebugServerClient", lambda **_: dummy)
    return CliRunner()


def test_verify_flag_overrides_insecure_config(monkeypatch, tmp_path):
    dummy = DummyClient()
    captured: dict[str, object] = {}

    def _client(**kwargs):
        captured.update(kwargs)
        return dummy

    monkeypatch.setattr(cli_main, "DebugServerClient", _client)
    runner = CliRunner()
    env = {"DEBUG_SERVER_HOME": str(tmp_path)}
    (tmp_path / "config.toml").write_text(
        """
base_url = "http://example.com"
token = "stored"
verify_tls = false
""".strip()
    )

    result = runner.invoke(
        cli_main.app,
        ["--verify", "--token", "override", "server", "init", "https://example.com/repo.git"],
        env=env,
    )

    assert result.exit_code == 0, result.stdout
    assert captured["verify_tls"] is True


def test_server_init_invokes_client(monkeypatch, tmp_path):
    dummy = DummyClient()
    runner = _runner(monkeypatch, dummy)
    env = {"DEBUG_SERVER_HOME": str(tmp_path)}

    result = runner.invoke(
        cli_main.app,
        ["--token", "abc", "server", "init", "https://example.com/repo.git"],
        env=env,
    )

    assert result.exit_code == 0, result.stdout
    assert dummy.init_request is not None
    assert "repo-1" in result.stdout


def test_session_create_reads_patch_and_streams_logs(monkeypatch, tmp_path):
    dummy = DummyClient()
    runner = _runner(monkeypatch, dummy)
    env = {"DEBUG_SERVER_HOME": str(tmp_path)}
    patch_file = tmp_path / "change.patch"
    patch_file.write_text("diff --git a b")

    result = runner.invoke(
        cli_main.app,
        [
            "--token",
            "abc",
            "session",
            "create",
            "--commit",
            "main",
            "--patch",
            str(patch_file),
            "--command",
            "pytest",
            "--metadata",
            "ticket=123",
            "--follow",
        ],
        env=env,
    )

    assert result.exit_code == 0, result.stdout
    assert dummy.session_request is not None
    assert dummy.session_request.patch == patch_file.read_text()
    assert dummy.logs_follow is True
    assert "sess-123" in result.stdout


def test_artifact_download_writes_file(monkeypatch, tmp_path):
    dummy = DummyClient()
    runner = _runner(monkeypatch, dummy)
    env = {"DEBUG_SERVER_HOME": str(tmp_path)}
    output = tmp_path / "artifact.bin"

    result = runner.invoke(
        cli_main.app,
        [
            "--token",
            "abc",
            "artifact",
            "download",
            "sess-123",
            "art-7",
            "--output",
            str(output),
        ],
        env=env,
    )

    assert result.exit_code == 0, result.stdout
    assert output.read_bytes() == b"hello-world!"
    assert dummy.artifact_requested == ("sess-123", "art-7")
