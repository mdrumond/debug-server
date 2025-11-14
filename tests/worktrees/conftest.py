"""Shared fixtures for worktree tests."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

_GIT = shutil.which("git") or "git"


def _run_git(*args: str, cwd: Path, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603
        [_GIT, *args],
        cwd=cwd,
        check=True,
        capture_output=capture,
        text=capture,
    )


def init_git_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _run_git("init", "--initial-branch", "main", cwd=path)
    _run_git("config", "user.name", "Worktree Tests", cwd=path)
    _run_git("config", "user.email", "worktrees@example.com", cwd=path)


def commit_file(path: Path, filename: str, content: str) -> str:
    file_path = path / filename
    file_path.write_text(content)
    _run_git("add", filename, cwd=path)
    _run_git("commit", "-m", f"update {filename}", cwd=path)
    result = _run_git("rev-parse", "HEAD", cwd=path, capture=True)
    return result.stdout.strip()
