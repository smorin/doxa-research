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
from importlib import metadata
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


def test_installed_metadata_matches_pyproject() -> None:
    """The distribution-metadata path (the canonical install-time source) matches.

    Uses ``importlib.metadata`` DIRECTLY — not the ``__version__`` import —
    because ``__init__.py`` has a ``pyproject.toml`` fallback for the
    ``./doxa`` dev launcher. That fallback would mask a broken install
    (a missing ``.dist-info/METADATA``, a rename gone wrong, a uv_build
    regression) by silently substituting the pyproject value. Bypassing
    the fallback here means a real metadata mismatch is caught loudly.
    Requires a synced env (``uv sync``).
    """
    assert metadata.version("doxa-research") == _pyproject_version()


def test_dunder_version_matches_pyproject() -> None:
    """``doxa_research.__version__`` (consumed by docs/CLI) matches.

    Exercises the fully-resolved value users see — either via
    ``importlib.metadata`` (installed wheels, uv-managed envs) or via the
    ``pyproject.toml`` fallback (``./doxa`` launcher). Both branches read
    the same SSOT, so this test passes regardless of install state; pair
    it with ``test_installed_metadata_matches_pyproject`` for full coverage.
    """
    assert __version__ == _pyproject_version()
