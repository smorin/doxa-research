"""P40 TS01-TS03: starter template drift, profile parse, structural-superset.

See docs/superpowers/specs/2026-05-21-p40-on-disk-starter-template-design.md.
"""

from __future__ import annotations

import tomllib
from importlib.resources import files
from pathlib import Path

import pytest

from doxa_research.cli_subcommands._config_validate import (
    ValidationResult,
    validate_config_file,
)
from doxa_research.config_schema import ProfileConfig

PROFILE_NAMES = (
    "daily",
    "quick",
    "openai_deep",
    "all_deep",
    "interactive",
    "deep_research",
)


def _template_path() -> Path:
    return Path(str(files("doxa_research.data") / "starter.config.toml"))


def _template_doc() -> dict:
    return tomllib.loads(_template_path().read_text(encoding="utf-8"))


def test_ts01_starter_template_round_trips() -> None:
    """TS01: bidirectional drift — `validate_config_file` with drift_check=True passes."""
    result = validate_config_file(_template_path(), drift_check=True)
    assert isinstance(result, ValidationResult)
    assert result.ok, f"{result.error}: {result.message} (details={result.details})"
    assert result.checks == ("schema", "drift")


@pytest.mark.parametrize("name", PROFILE_NAMES)
def test_ts02_profiles_validate(name: str) -> None:
    """TS02: every shipped profile parses against ProfileConfig."""
    profiles = _template_doc().get("profiles") or {}
    assert name in profiles, f"profile [{name}] missing from template"
    ProfileConfig.model_validate(profiles[name])


def test_ts03_structural_superset_with_pre_p40_fixture() -> None:
    """TS03: every pre-P40 top-level table/key is present unchanged in the new
    template; the only added top-level table is `[clarification]`.
    """
    fixture = tomllib.loads(
        (Path(__file__).parent / "fixtures" / "starter.pre-p40.toml").read_text(encoding="utf-8")
    )
    template = _template_doc()

    fixture_keys = set(fixture.keys())
    template_keys = set(template.keys())
    new_keys = template_keys - fixture_keys
    assert new_keys <= {"clarification"}, (
        f"unexpected new top-level table(s): {new_keys - {'clarification'}}"
    )

    for k in fixture_keys:
        assert template.get(k) == fixture[k], f"top-level table [{k}] diverged from pre-P40 fixture"
