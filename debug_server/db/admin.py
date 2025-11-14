"""Admin CLI helpers for tokens and bootstrap data."""

from __future__ import annotations

from datetime import datetime, timedelta

import typer

from .service import MetadataStore
from .session import create_engine_from_url

app = typer.Typer(help="Admin helpers for the metadata store.")


def _store(db_url: str | None) -> MetadataStore:
    engine = create_engine_from_url(db_url)
    return MetadataStore(engine)


@app.command("create-token")
def create_token(
    name: str = typer.Argument(..., help="Human-friendly token name"),
    scopes: str = typer.Option("admin", help="Comma separated scope list"),
    expires_in_days: int = typer.Option(0, help="Optional expiry in days"),
    db_url: str | None = typer.Option(None, envvar="DEBUG_SERVER_DB_URL"),
) -> None:
    """Create a new auth token and print it to stdout."""

    store = _store(db_url)
    expires_at = None
    if expires_in_days > 0:
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
    record, raw_token = store.create_token(
        name=name,
        scopes=scopes.split(","),
        expires_at=expires_at,
    )
    typer.echo(f"Created token {record.name} (id={record.id})")
    typer.echo(f"Bearer token: {raw_token}")


if __name__ == "__main__":
    app()
