"""Compatibility package exposing the Debug Server client utilities."""

from client import __version__

__all__ = ["__version__"]
"""Debug server shared package."""

from .version import __version__  # noqa: F401
