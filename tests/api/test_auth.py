from __future__ import annotations

from fastapi.testclient import TestClient

from debug_server.db import MetadataStore


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_token_management(client: TestClient, metadata_store: MetadataStore) -> None:
    _, admin_token = metadata_store.create_token("admin", scopes=["admin"])
    response = client.post(
        "/auth/tokens",
        json={"name": "cli", "scopes": ["sessions:read"], "expires_in": 3600},
        headers=_auth_header(admin_token),
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["token"]

    listing = client.get("/auth/tokens", headers=_auth_header(admin_token))
    assert listing.status_code == 200
    tokens = listing.json()
    cli_entry = next(entry for entry in tokens if entry["name"] == "cli")
    token_id = cli_entry["id"]
    revoke = client.delete(f"/auth/tokens/{token_id}", headers=_auth_header(admin_token))
    assert revoke.status_code == 200


def test_token_management_requires_admin(client: TestClient) -> None:
    response = client.post(
        "/auth/tokens",
        json={"name": "cli"},
    )
    assert response.status_code == 401
