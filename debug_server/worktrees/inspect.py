"""Administrative helpers for inspecting worktree pools."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Annotated

import typer

from debug_server.db import (
    MetadataStore,
    Repository,
    create_engine_from_url,
    get_default_database_url,
)

from .pool import WorktreePool, WorktreePoolSettings

app = typer.Typer(help="Inspect and reclaim git worktree pools.")


def _load_store(database_url: str | None) -> MetadataStore:
    engine = create_engine_from_url(database_url or get_default_database_url())
    return MetadataStore(engine)


def _select_repository(store: MetadataStore, name: str) -> Repository:
    repository = store.get_repository_by_name(name)
    if repository is None:
        raise typer.BadParameter(f"Repository '{name}' not found")
    return repository


def _default_paths(repo_name: str) -> tuple[Path, Path]:
    artifacts_root = Path(".artifacts")
    bare = artifacts_root / "repos" / f"{repo_name}.bare"
    worktrees = artifacts_root / "worktrees" / repo_name
    return bare, worktrees


def _make_pool(
    store: MetadataStore,
    repository: Repository,
    *,
    bare_path: Path | None,
    worktree_root: Path | None,
) -> WorktreePool:
    default_bare, default_root = _default_paths(repository.name)
    if repository.id is None:
        raise typer.BadParameter("Repository is missing a database identifier")
    settings = WorktreePoolSettings(
        repository_id=repository.id,
        remote_url=repository.remote_url,
        bare_path=bare_path or default_bare,
        worktree_root=worktree_root or default_root,
    )
    return WorktreePool(store, settings)


RepositoryOption = Annotated[
    str,
    typer.Option(..., "--repository", help="Repository name", show_default=False),
]
DatabaseOption = Annotated[
    str | None,
    typer.Option(
        None,
        "--database-url",
        envvar="DEBUG_SERVER_DATABASE_URL",
        help="SQLAlchemy database URL",
        show_default=False,
    ),
]
BarePathOption = Annotated[
    Path | None,
    typer.Option(None, "--bare-path", help="Override the bare repo location", show_default=False),
]
WorktreeRootOption = Annotated[
    Path | None,
    typer.Option(
        None,
        "--worktree-root",
        help="Override the worktree root",
        show_default=False,
    ),
]


@app.command("show-active")
def show_active(
    repository: RepositoryOption,
    database_url: DatabaseOption = None,
) -> None:
    """Print a summary of every worktree tracked for the repository."""

    store = _load_store(database_url)
    repo = _select_repository(store, repository)
    for worktree in store.list_worktrees(repo.id):
        typer.echo(
            f"{worktree.id}: {worktree.path} | {worktree.status.value} | "
            f"commit={worktree.commit_sha or '-'} | env={worktree.environment_hash or '-'}"
        )


def _parse_duration(value: str) -> timedelta:
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    try:
        amount = int(value[:-1])
        unit = value[-1].lower()
        multiplier = units[unit]
        return timedelta(seconds=amount * multiplier)
    except (KeyError, ValueError):
        raise typer.BadParameter("Use values such as '30m', '2h', or '1d'.") from None


@app.command()
def reclaim(
    repository: RepositoryOption,
    older_than: Annotated[
        str,
        typer.Option(help="Only reclaim worktrees idle for longer than this"),
    ] = "1h",
    database_url: DatabaseOption = None,
    bare_path: BarePathOption = None,
    worktree_root: WorktreeRootOption = None,
) -> None:
    """Delete idle worktrees and log what was reclaimed."""

    store = _load_store(database_url)
    repo = _select_repository(store, repository)
    pool = _make_pool(store, repo, bare_path=bare_path, worktree_root=worktree_root)
    reclaimed = pool.reclaim_stale_worktrees(max_idle_age=_parse_duration(older_than))
    typer.echo(f"Reclaimed {len(reclaimed)} worktrees")
    for path in reclaimed:
        typer.echo(f" - {path}")


if __name__ == "__main__":  # pragma: no cover - module executed as a script
    app()
