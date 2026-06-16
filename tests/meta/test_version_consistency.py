"""Guard that the project version stays single-sourced.

``pyproject.toml`` ``[project] version`` is the single source of truth.
release-please bumps it together with ``.release-please-manifest.json``, and
``doxa_research.__version__`` is derived from the installed package metadata
(populated by ``uv_build`` at build time). These tests fail if any of those
copies drift apart.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from doxa_research import __version__

ROOT = Path(__file__).resolve().parents[2]


def _pyproject_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())
    return data["project"]["version"]


def _manifest_version() -> str:
    data = json.loads((ROOT / ".release-please-manifest.json").read_text())
    return data["."]


def test_manifest_matches_pyproject() -> None:
    """release-please bumps both; they must never diverge."""
    assert _manifest_version() == _pyproject_version()


def test_installed_version_matches_pyproject() -> None:
    """``__version__`` is derived from installed package metadata.

    Requires a synced environment (``uv sync``); the version baked into the
    installed distribution must match the source-of-truth in pyproject.toml.
    """
    assert __version__ == _pyproject_version()
