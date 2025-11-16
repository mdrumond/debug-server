from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from debug_server.db import ArtifactKind, MetadataStore


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_repo(store: MetadataStore) -> None:
    store.upsert_repository(
        name="demo",
        remote_url="https://example.com/demo.git",
        default_branch="main",
    )


def test_session_lifecycle_and_artifacts(
    client: TestClient,
    metadata_store: MetadataStore,
    tmp_path: Path,
) -> None:
    _create_repo(metadata_store)
    _, token_value = metadata_store.create_token(
        "runner",
        scopes=["sessions:read", "sessions:write", "commands:write", "artifacts:read"],
    )
    create_response = client.post(
        "/sessions",
        json={"repository": "demo", "commit_sha": "abc1234", "metadata": {"ci": True}},
        headers=_auth_header(token_value),
    )
    assert create_response.status_code == 201, create_response.text
    session_id = create_response.json()["id"]

    cmd_response = client.post(
        f"/sessions/{session_id}/commands",
        json={"argv": ["pytest", "-k", "unit"]},
        headers=_auth_header(token_value),
    )
    assert cmd_response.status_code == 201
    commands = client.get(
        f"/sessions/{session_id}/commands",
        headers=_auth_header(token_value),
    )
    assert commands.status_code == 200
    assert commands.json()[0]["command"].startswith("pytest")

    artifact_path = tmp_path / "logs.txt"
    artifact_path.write_text("hello", encoding="utf-8")
    metadata_store.record_artifact(
        session_id=session_id,
        kind=ArtifactKind.LOG,
        path=str(artifact_path),
    )
    artifact_listing = client.get(
        f"/sessions/{session_id}/artifacts",
        headers=_auth_header(token_value),
    )
    assert artifact_listing.status_code == 200
    artifact_id = artifact_listing.json()[0]["id"]
    download = client.get(
        f"/sessions/{session_id}/artifacts/{artifact_id}",
        headers=_auth_header(token_value),
    )
    assert download.status_code == 200
    assert download.text == "hello"

    cancel = client.delete(f"/sessions/{session_id}", headers=_auth_header(token_value))
    assert cancel.status_code == 200


def test_session_missing_repository(client: TestClient, metadata_store: MetadataStore) -> None:
    _, token_value = metadata_store.create_token("runner", scopes=["sessions:write"])
    response = client.post(
        "/sessions",
        json={"repository": "unknown", "commit_sha": "abc1234"},
        headers=_auth_header(token_value),
    )
    assert response.status_code == 404
