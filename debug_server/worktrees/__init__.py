"""Worktree management utilities for the debug server backend."""

from .dependency_sync import (
    DependencyState,
    DependencyStateStore,
    compute_dependency_hash,
)
from .pool import (
    WorktreeLease,
    WorktreePool,
    WorktreePoolError,
    WorktreePoolSettings,
)

__all__ = [
    "DependencyState",
    "DependencyStateStore",
    "WorktreeLease",
    "WorktreePool",
    "WorktreePoolError",
    "WorktreePoolSettings",
    "compute_dependency_hash",
]
