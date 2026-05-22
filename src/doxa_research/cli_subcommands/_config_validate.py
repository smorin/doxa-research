"""Pure validation logic for `doxa config validate`.

Framework-free: no Click imports. The CLI wrapper in `config.py` calls
`validate_config_file` and renders the `ValidationResult` to stdout/stderr or
the shared `json_output.py` envelope. The TS01 drift test imports the same
function so CLI behavior and test behavior cannot diverge.

See docs/superpowers/specs/2026-05-21-p40-on-disk-starter-template-design.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of `validate_config_file`.

    Attributes:
        ok: True when every applicable phase (parse + schema + optional drift)
            passed.
        path: Resolved path of the file that was validated. None if the file
            could not be opened.
        error: Stable error code (matches the JSON envelope's `error.code`).
            None on success. Codes: ``FILE_NOT_FOUND``, ``TOML_PARSE_ERROR``,
            ``SCHEMA_VALIDATION``, ``DRIFT_MISSING_KEY``, ``DRIFT_VALUE_MISMATCH``,
            ``PACKAGE_DATA_MISSING``.
        message: Human-readable description of the failure. Empty on success.
        details: Phase-specific context (e.g. ``{"path": "general.default_mode",
            "expected": "default", "actual": "bogus"}``).
        checks: Which phases ran (``["schema"]`` or ``["schema", "drift"]``).
    """

    ok: bool
    path: Path | None = None
    error: str | None = None
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    checks: tuple[str, ...] = ()


def validate_config_file(
    path: Path,
    *,
    drift_check: bool,
) -> ValidationResult:
    """Validate a TOML config file against ``UserConfigFile``.

    When ``drift_check=True``, additionally assert that every ``StarterField``
    in ``DoxaConfig`` appears in the file at its expected TOML path with the
    value an instantiated ``DoxaConfig()`` would emit at that path.
    """
    raise NotImplementedError("validate_config_file body lands in Task 6")
