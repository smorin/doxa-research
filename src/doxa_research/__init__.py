"""Doxa Research - AI-Powered Research Assistant."""

from importlib import metadata

try:
    __version__ = metadata.version("doxa-research")
except metadata.PackageNotFoundError:
    # Fallback for non-installed development trees. The `./doxa` launcher
    # uses `uv run --script` with src/ on sys.path but does NOT install the
    # doxa-research package, so metadata lookup fails there. Read the SSOT
    # (pyproject.toml [project].version) directly. Production wheels never
    # hit this branch — their .dist-info/METADATA is populated by uv_build.
    import tomllib
    from pathlib import Path

    _pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    __version__ = tomllib.loads(_pyproject.read_text())["project"]["version"]

__copyright__ = "Copyright (C) 2025-2026 Steve Morin"
__license__ = "AGPL-3.0-or-later"
