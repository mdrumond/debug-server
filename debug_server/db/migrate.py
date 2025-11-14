"""Migration CLI that wraps Alembic."""

from __future__ import annotations

from pathlib import Path

import typer
from alembic import command
from alembic.config import Config

from .session import get_default_database_url

app = typer.Typer(help="Database migration utilities")

PACKAGE_ROOT = Path(__file__).resolve().parent


def _alembic_config(db_url: str | None) -> Config:
    config = Config(str(PACKAGE_ROOT / "alembic.ini"))
    script_location = PACKAGE_ROOT / "migrations"
    config.set_main_option("script_location", str(script_location))
    resolved_url = db_url or get_default_database_url()
    config.set_main_option("sqlalchemy.url", resolved_url)
    return config


@app.command()
def upgrade(
    revision: str = typer.Argument("head", help="Revision to upgrade to"),
    db_url: str | None = typer.Option(None, envvar="DEBUG_SERVER_DB_URL"),
) -> None:
    """Apply migrations up to the given revision."""

    config = _alembic_config(db_url)
    command.upgrade(config, revision)


@app.command()
def downgrade(
    revision: str = typer.Argument("base", help="Revision to downgrade to"),
    db_url: str | None = typer.Option(None, envvar="DEBUG_SERVER_DB_URL"),
) -> None:
    """Downgrade to a previous revision."""

    config = _alembic_config(db_url)
    command.downgrade(config, revision)


@app.command()
def history(db_url: str | None = typer.Option(None, envvar="DEBUG_SERVER_DB_URL")) -> None:
    """Show migration history."""

    config = _alembic_config(db_url)
    command.history(config)


@app.command()
def current(db_url: str | None = typer.Option(None, envvar="DEBUG_SERVER_DB_URL")) -> None:
    """Display the current revision."""

    config = _alembic_config(db_url)
    command.current(config)


if __name__ == "__main__":
    app()
