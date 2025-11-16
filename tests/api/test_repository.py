from __future__ import annotations

from fastapi.testclient import TestClient

from debug_server.db import MetadataStore


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_repository_init_and_listing(client: TestClient, metadata_store: MetadataStore) -> None:
    _, admin_token = metadata_store.create_token("admin", scopes=["admin"])
    payload = {
        "name": "demo",
        "remote_url": "https://example.com/demo.git",
        "default_branch": "main",
        "settings": {"worktrees": 4},
    }
    response = client.post("/repository/init", json=payload, headers=_auth_header(admin_token))
    assert response.status_code == 201
    listing = client.get("/repository", headers=_auth_header(admin_token))
    assert listing.status_code == 200
    data = listing.json()
    assert len(data) == 1
    assert data[0]["name"] == "demo"


def test_repository_requires_auth(client: TestClient) -> None:
    response = client.post(
        "/repository/init",
        json={
            "name": "demo",
            "remote_url": "https://example.com/demo.git",
            "default_branch": "main",
        },
    )
    assert response.status_code == 401
