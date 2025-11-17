"""HTTP client powered by urllib for the Debug Server."""

from __future__ import annotations

import base64
import json
import ssl
from collections.abc import Iterable, Iterator
from http.client import HTTPResponse
from typing import Any, cast
from urllib import error, parse, request

from client import __version__
from client.sdk.models import (
    ArtifactMetadata,
    DebugActionRequest,
    DebugActionResponse,
    LogEntry,
    RepositoryInitRequest,
    RepositoryInitResponse,
    Session,
    SessionCreateRequest,
)


class DebugServerClient:
    """Minimal HTTP client that talks to the Debug Server REST API."""

    def __init__(
        self,
        *,
        base_url: str,
        token: str | None,
        verify_tls: bool = True,
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout
        self._ssl_context: ssl.SSLContext | None = None
        if not verify_tls:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            self._ssl_context = context

    def close(self) -> None:  # pragma: no cover - kept for API symmetry
        return None

    def initialize_repository(self, request_obj: RepositoryInitRequest) -> RepositoryInitResponse:
        payload = self._json_request("POST", "/repository/init", json_body=request_obj.to_payload())
        return RepositoryInitResponse.from_dict(payload)

    def create_session(self, request_obj: SessionCreateRequest) -> Session:
        payload = self._json_request("POST", "/sessions", json_body=request_obj.to_payload())
        return Session.from_dict(payload)

    def get_session(self, session_id: str) -> Session:
        payload = self._json_request("GET", f"/sessions/{session_id}")
        return Session.from_dict(payload)

    def stream_session_logs(self, session_id: str, *, follow: bool = False) -> Iterator[LogEntry]:
        params = {"follow": "true" if follow else "false"}
        with self._open("GET", f"/sessions/{session_id}/logs", params=params) as resp:
            for raw_line in resp:
                line = raw_line.decode().strip()
                if not line:
                    continue
                data = json.loads(line)
                yield LogEntry.from_dict(data)

    def send_debug_action(self, session_id: str, action: DebugActionRequest) -> DebugActionResponse:
        payload = self._json_request(
            "POST",
            f"/sessions/{session_id}/debug",
            json_body=action.to_payload(),
        )
        return DebugActionResponse.from_dict(payload)

    def download_artifact(
        self, session_id: str, artifact_id: str
    ) -> tuple[ArtifactMetadata, bytes]:
        payload = self._json_request("GET", f"/sessions/{session_id}/artifacts/{artifact_id}")
        artifact_raw = cast(dict[str, Any], payload["artifact"])
        metadata = ArtifactMetadata.from_dict(artifact_raw)
        content_raw = cast(str | bytes, payload["content"])
        content = base64.b64decode(content_raw, validate=True)
        return metadata, content

    def list_commands(self, session_id: str) -> Iterable[str]:
        payload = self._json_request("GET", f"/sessions/{session_id}/commands")
        raw_commands = payload.get("commands") or []
        if not isinstance(raw_commands, Iterable):
            return []
        return [str(cmd) for cmd in raw_commands]

    def _json_request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._open(method, path, params=params, json_body=json_body) as resp:
            data = resp.read()
            if not data:
                return {}
            return cast(dict[str, Any], json.loads(data.decode()))

    def _open(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> HTTPResponse:
        url = f"{self._base_url}{path}"
        if params:
            url = f"{url}?{parse.urlencode(params)}"
        headers = {
            "User-Agent": f"debug-server-client/{__version__}",
            "Accept": "application/json",
        }
        data = None
        if json_body is not None:
            data = json.dumps(json_body).encode()
            headers["Content-Type"] = "application/json"
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        req = request.Request(url, data=data, headers=headers, method=method)
        try:
            return cast(
                HTTPResponse, request.urlopen(req, timeout=self._timeout, context=self._ssl_context)
            )
        except error.HTTPError as exc:  # pragma: no cover - passthrough for integration
            message = exc.read().decode() or exc.reason
            raise RuntimeError(f"Server error {exc.code}: {message}") from exc
