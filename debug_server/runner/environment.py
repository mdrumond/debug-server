"""Manage virtual environments for runner workers."""

from __future__ import annotations

import os
import shutil
import sys
import venv
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from debug_server.worktrees.dependency_sync import (
    DependencyStateStore,
    compute_dependency_hash,
)

__all__ = [
    "EnvironmentHandle",
    "EnvironmentManager",
    "EnvironmentRequest",
]


@dataclass(slots=True)
class EnvironmentRequest:
    """Describe the desired environment fingerprint."""

    name: str
    manifests: Sequence[Path] | None = None
    metadata: Mapping[str, str] | None = None


@dataclass(slots=True)
class EnvironmentHandle:
    """Represents a provisioned interpreter environment."""

    path: Path
    python_path: Path
    fingerprint: str | None

    @property
    def bin_path(self) -> Path:
        if os.name == "nt":  # pragma: no cover - Windows fallback
            return self.path / "Scripts"
        return self.path / "bin"


class EnvironmentManager:
    """Create and reuse lightweight venv-based worker environments."""

    def __init__(
        self,
        root: Path,
        *,
        state_store: DependencyStateStore | None = None,
    ) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        state_root = self.root / ".state"
        state_root.mkdir(parents=True, exist_ok=True)
        self.state_store = state_store or DependencyStateStore(state_root)

    def ensure(self, request: EnvironmentRequest, *, force: bool = False) -> EnvironmentHandle:
        """Return a ready-to-use environment for the provided request."""

        name = request.name.strip() or "default"
        safe_name = name.replace("/", "-")
        env_path = self.root / safe_name
        manifests = tuple(Path(p) for p in request.manifests or ())
        metadata = dict(request.metadata or {})
        fingerprint = None
        if manifests or metadata:
            fingerprint = compute_dependency_hash(manifests, extra_inputs=metadata)
        needs_rebuild = force or self._needs_rebuild(env_path, request.name, fingerprint)
        if needs_rebuild:
            if env_path.exists():
                shutil.rmtree(env_path)
            builder = venv.EnvBuilder(with_pip=True, clear=True)
            builder.create(env_path)
            if fingerprint is not None:
                self.state_store.write(request.name, fingerprint, metadata={"python": sys.version})
        elif fingerprint is not None:
            state = self.state_store.read(request.name)
            if state is None:
                self.state_store.write(request.name, fingerprint, metadata={"python": sys.version})
        python_path = self._python_path(env_path)
        return EnvironmentHandle(path=env_path, python_path=python_path, fingerprint=fingerprint)

    def _needs_rebuild(self, env_path: Path, key: str, fingerprint: str | None) -> bool:
        if not env_path.exists():
            return True
        if fingerprint is None:
            return False
        state = self.state_store.read(key)
        if state is None:
            return True
        return state.fingerprint != fingerprint

    @staticmethod
    def _python_path(env_path: Path) -> Path:
        if os.name == "nt":  # pragma: no cover - Windows fallback
            return env_path / "Scripts" / "python.exe"
        return env_path / "bin" / "python"
