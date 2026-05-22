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
    import tomllib

    from pydantic import ValidationError

    from doxa_research.config_schema import (
        ConfigSchema,
        UserConfigFile,
        default_config_dict,
    )

    resolved = path.resolve() if path.exists() else path
    if not path.exists():
        return ValidationResult(
            ok=False,
            path=resolved,
            error="FILE_NOT_FOUND",
            message=f"no such file: {path}",
            details={"path": str(path)},
            checks=(),
        )

    # ---- parse phase ----
    try:
        text = resolved.read_text(encoding="utf-8")
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        return ValidationResult(
            ok=False,
            path=resolved,
            error="TOML_PARSE_ERROR",
            message=f"TOML parse error: {exc}",
            details={"path": str(resolved)},
            checks=(),
        )

    # ---- schema phase ----
    try:
        UserConfigFile.model_validate(doc)
    except ValidationError as exc:
        errors = exc.errors()
        first = errors[0]
        loc = ".".join(str(p) for p in first.get("loc", ()))
        return ValidationResult(
            ok=False,
            path=resolved,
            error="SCHEMA_VALIDATION",
            message=f"{loc}: {first.get('msg', 'validation error')}"
            if loc
            else first.get("msg", "validation error"),
            details={"errors": errors},
            checks=("schema",),
        )

    if not drift_check:
        return ValidationResult(ok=True, path=resolved, checks=("schema",))

    # ---- drift phase ----
    expected_doc = default_config_dict()
    for starter_path in ConfigSchema.starter_keys():
        expected = _lookup(expected_doc, starter_path)
        actual = _lookup(doc, starter_path)
        if actual is _MISSING:
            dotted = ".".join(starter_path)
            return ValidationResult(
                ok=False,
                path=resolved,
                error="DRIFT_MISSING_KEY",
                message=f"starter template missing required key: {dotted} (expected default: {expected!r})",
                details={"path": dotted, "expected": expected},
                checks=("schema", "drift"),
            )
        if actual != expected:
            dotted = ".".join(starter_path)
            return ValidationResult(
                ok=False,
                path=resolved,
                error="DRIFT_VALUE_MISMATCH",
                message=f"starter template value mismatch at {dotted}: expected {expected!r}, got {actual!r}",
                details={"path": dotted, "expected": expected, "actual": actual},
                checks=("schema", "drift"),
            )

    return ValidationResult(ok=True, path=resolved, checks=("schema", "drift"))


_MISSING = object()


def _lookup(doc: dict[str, Any], path: tuple[str, ...]) -> Any:
    cur: Any = doc
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return _MISSING
        cur = cur[key]
    return cur
