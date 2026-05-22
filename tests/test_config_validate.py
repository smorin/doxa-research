"""P40 TS04a-f: behavioral tests for `doxa config validate`.

See docs/superpowers/specs/2026-05-21-p40-on-disk-starter-template-design.md.
"""

from __future__ import annotations

import json
import shutil
from importlib.resources import files
from pathlib import Path

import pytest
from click.testing import CliRunner

from doxa_research.cli_subcommands._config_validate import validate_config_file


@pytest.fixture
def cli():
    from doxa_research.cli import cli as _cli

    return _cli


@pytest.fixture
def shipped_template() -> Path:
    return Path(str(files("doxa_research.data") / "starter.config.toml"))


def test_ts04a_valid_template_exits_zero(cli, shipped_template) -> None:
    """TS04a: validating the shipped template exits 0 with the (schema + drift) tag."""
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "validate", str(shipped_template)])
    assert result.exit_code == 0, result.output
    assert "OK" in result.output
    assert "schema + drift" in result.output


def test_ts04b_drift_value_mismatch_pure(tmp_path, shipped_template) -> None:
    """TS04b: pure-function drift mismatch surfaces the offending path.

    Note: we test at the pure-function layer because the CLI's path-equality
    gate intentionally drops drift for tempfile copies (covered by TS04e).
    """
    corrupt = tmp_path / "starter.config.toml"
    corrupt.write_text(
        shipped_template.read_text(encoding="utf-8").replace(
            'default_mode = "default"',
            'default_mode = "BOGUS-VALUE-FOR-TEST"',
        ),
        encoding="utf-8",
    )
    result = validate_config_file(corrupt, drift_check=True)
    assert not result.ok
    assert result.error == "DRIFT_VALUE_MISMATCH"
    assert "general.default_mode" in result.details["path"]
    assert result.details["actual"] == "BOGUS-VALUE-FOR-TEST"


def test_ts04c_drift_missing_key_pure(tmp_path, shipped_template) -> None:
    """TS04c: pure-function drift missing-key surfaces the missing path."""
    import tomllib

    doc = tomllib.loads(shipped_template.read_text(encoding="utf-8"))
    del doc["clarification"]["interactive"]["max_input_height"]
    # Re-serialize via tomli_w if available, else write a stripped TOML.
    # tomllib is read-only, so we hand-write the minimal mutation:
    # easier path: edit the line directly.
    corrupt = tmp_path / "starter.config.toml"
    text = shipped_template.read_text(encoding="utf-8")
    # Drop the `max_input_height = 15` line; matches the literal in Task 9's template.
    corrupt.write_text(text.replace("max_input_height = 15\n", ""), encoding="utf-8")
    result = validate_config_file(corrupt, drift_check=True)
    assert not result.ok
    assert result.error == "DRIFT_MISSING_KEY"
    assert "max_input_height" in result.details["path"]


def test_ts04d_json_envelope_success(cli, shipped_template) -> None:
    """TS04d (success path): --json emits the shared {"status":"ok","data":...} envelope."""
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "validate", str(shipped_template), "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert "data" in payload
    assert payload["data"]["checks"] == ["schema", "drift"]


def test_ts04d_json_envelope_error(cli) -> None:
    """TS04d (error path): --json emits the shared {"status":"error","error":{...}} envelope."""
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "validate", "/definitely/not/here.toml", "--json"])
    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "FILE_NOT_FOUND"
    assert isinstance(payload["error"]["message"], str)


def test_ts04e_user_config_skips_drift(cli, tmp_path, shipped_template) -> None:
    """TS04e: validating a non-shipped path runs schema only, not drift."""
    user_config = tmp_path / "doxa.config.toml"
    shutil.copy(shipped_template, user_config)
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "validate", str(user_config)])
    assert result.exit_code == 0, result.output
    assert "OK" in result.output
    assert "(schema)" in result.output
    assert "drift" not in result.output


def test_ts04f_no_path_defaults_to_user_tier(cli, tmp_path, shipped_template, monkeypatch) -> None:
    """TS04f: with no PATH arg, validates the user-tier config file."""
    fake_home = tmp_path / "home"
    config_dir = fake_home / ".config" / "doxa"
    config_dir.mkdir(parents=True)
    user_config = config_dir / "doxa.config.toml"
    shutil.copy(shipped_template, user_config)
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(fake_home / ".config"))

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "validate"])
    assert result.exit_code == 0, result.output
    assert "OK" in result.output


def test_ts04f_no_path_no_user_config_errors(cli, tmp_path, monkeypatch) -> None:
    """TS04f (negative): no PATH and no user-tier file → exits 1 with FILE_NOT_FOUND."""
    fake_home = tmp_path / "empty-home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(fake_home / ".config"))

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "validate", "--json"])
    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "FILE_NOT_FOUND"
