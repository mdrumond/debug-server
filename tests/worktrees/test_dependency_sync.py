"""Tests for dependency fingerprint helpers."""

from __future__ import annotations

from pathlib import Path

from debug_server.worktrees.dependency_sync import (
    DependencyStateStore,
    compute_dependency_hash,
)


def test_compute_dependency_hash_changes_on_file(tmp_path: Path) -> None:
    file_a = tmp_path / "requirements.txt"
    file_a.write_text("pkg==1.0\n")
    fingerprint1 = compute_dependency_hash([file_a])
    file_a.write_text("pkg==2.0\n")
    fingerprint2 = compute_dependency_hash([file_a])
    assert fingerprint1 != fingerprint2


def test_state_store_round_trip(tmp_path: Path) -> None:
    store = DependencyStateStore(tmp_path)
    file_a = tmp_path / "lock.txt"
    file_a.write_text("deps")
    fingerprint = compute_dependency_hash([file_a])
    assert store.needs_sync("python", fingerprint) is True
    store.write("python", fingerprint, metadata={"manager": "pip"})
    assert store.needs_sync("python", fingerprint) is False
    new_fp = compute_dependency_hash([file_a])
    assert store.needs_sync("python", new_fp) is False
    file_a.write_text("deps2")
    changed_fp = compute_dependency_hash([file_a])
    assert store.needs_sync("python", changed_fp) is True
