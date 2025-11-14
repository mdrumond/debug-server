"""Dependency fingerprinting helpers used by the worktree pool."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

__all__ = [
    "DependencyState",
    "DependencyStateStore",
    "compute_dependency_hash",
]


@dataclass(slots=True)
class DependencyState:
    """Represents the cached fingerprint of dependency manifests."""

    fingerprint: str
    updated_at: datetime
    metadata: dict[str, str] | None = None


class DependencyStateStore:
    """Persist dependency fingerprints to disk so workers can skip syncs."""

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _state_path(self, key: str) -> Path:
        safe_key = key.replace("/", "_")
        return self.root / f"{safe_key}.json"

    def read(self, key: str) -> DependencyState | None:
        path = self._state_path(key)
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return DependencyState(
            fingerprint=data["fingerprint"],
            updated_at=datetime.fromisoformat(data["updated_at"]),
            metadata=data.get("metadata"),
        )

    def write(
        self,
        key: str,
        fingerprint: str,
        metadata: Mapping[str, str] | None = None,
        *,
        timestamp: datetime | None = None,
    ) -> DependencyState:
        state = DependencyState(
            fingerprint=fingerprint,
            updated_at=timestamp or datetime.now(UTC),
            metadata=dict(metadata or {}),
        )
        path = self._state_path(key)
        path.write_text(
            json.dumps(
                {
                    "fingerprint": state.fingerprint,
                    "updated_at": state.updated_at.isoformat(),
                    "metadata": state.metadata,
                },
                indent=2,
            )
        )
        return state

    def needs_sync(self, key: str, fingerprint: str) -> bool:
        state = self.read(key)
        if state is None:
            return True
        return state.fingerprint != fingerprint


def compute_dependency_hash(
    manifests: Iterable[Path],
    *,
    extra_inputs: Mapping[str, str] | None = None,
    chunk_size: int = 1024 * 1024,
) -> str:
    """Return a SHA256 hash across the provided manifests and metadata."""

    digest = sha256()
    for path in sorted(map(Path, manifests)):
        if not path.exists():
            raise FileNotFoundError(path)
        digest.update(path.name.encode("utf-8"))
        with path.open("rb") as handle:
            while chunk := handle.read(chunk_size):
                digest.update(chunk)
        digest.update(str(path.stat().st_mtime_ns).encode())
    if extra_inputs:
        for key in sorted(extra_inputs):
            digest.update(key.encode("utf-8"))
            digest.update(extra_inputs[key].encode("utf-8"))
    return digest.hexdigest()
