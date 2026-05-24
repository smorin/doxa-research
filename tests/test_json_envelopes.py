"""Category E — `--json` envelope contract per command (spec §8.3).

The JSON_COMMANDS list grows as each subcommand T06–T13 adds `--json`.
Category H meta-test in test_ci_lint_rules.py uses an AST walker against
src/doxa_research/cli_subcommands/ to assert this list stays complete.
"""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path

import pytest
from click.testing import CliRunner

_SHIPPED_TEMPLATE = str(files("doxa_research.data") / "starter.config.toml")

JSON_COMMANDS: list[tuple[str, list[str], int]] = [
    # (label, argv-after-cli, expected_exit_code)
    ("init_non_interactive", ["init", "--json", "--non-interactive"], 0),
    ("status_missing_op", ["status", "research-MISSING", "--json"], 6),
    ("list_empty", ["list", "--json"], 0),
    ("list_all_empty", ["list", "--all", "--json"], 0),
    ("providers_list", ["providers", "list", "--json"], 0),
    ("providers_models", ["providers", "models", "--json"], 0),
    ("providers_check", ["providers", "check", "--json"], 0),
    # NOTE: `providers check` exits 0 with `data.complete=False` even when
    # keys missing — the JSON envelope decouples machine state from process
    # exit code.
    ("config_get", ["config", "get", "paths.base_output_dir", "--json"], 0),
    ("config_get_missing", ["config", "get", "nonexistent.key", "--json"], 1),
    ("config_list", ["config", "list", "--json"], 0),
    ("config_path", ["config", "path", "--json"], 0),
    ("config_set", ["config", "set", "test.key", "value", "--json"], 0),
    ("config_unset", ["config", "unset", "test.key", "--json"], 0),
    ("modes_list", ["modes", "list", "--json"], 0),
    ("modes_list_by_name", ["modes", "list", "--json", "--name", "default"], 0),
    ("modes_set_default", ["modes", "set-default", "deep_research", "--json"], 0),
    ("modes_unset_default", ["modes", "unset-default", "--json"], 0),
    # T13: ask + resume rows. ask rows live in test_json_non_blocking.py
    # (Category G timing tests). The smoke-row below covers the resume
    # OPERATION_NOT_FOUND envelope.
    ("resume_missing_op", ["resume", "research-MISSING", "--json"], 6),
    # P18 Phase G: cancel subcommand. Missing-op exits 6 with OPERATION_NOT_FOUND envelope.
    ("cancel_missing_op", ["cancel", "research-MISSING", "--json"], 6),
    # T15: lint-meta coverage rows for `completion` (UNSUPPORTED_SHELL error
    # envelope) and `config edit` (success envelope; EDITOR=true monkeypatched
    # in the parametrize body).
    ("completion_unsupported_shell", ["completion", "powershell", "--json"], 2),
    ("config_edit_with_editor_true", ["config", "edit", "--json"], 0),
    # P21b: config profiles subgroup. Rows that need an existing profile are
    # seeded inside test_json_envelope_contract by pre-invoking
    # `config profiles add fast` (and friends) before the target argv.
    ("config_profiles_list", ["config", "profiles", "list", "--json"], 0),
    (
        "config_profiles_list_show_shadowed",
        ["config", "profiles", "list", "--show-shadowed", "--json"],
        0,
    ),
    ("config_profiles_show", ["config", "profiles", "show", "fast", "--json"], 0),
    ("config_profiles_current", ["config", "profiles", "current", "--json"], 0),
    (
        "config_profiles_set_default",
        ["config", "profiles", "set-default", "fast", "--json"],
        0,
    ),
    ("config_profiles_unset_default", ["config", "profiles", "unset-default", "--json"], 0),
    ("config_profiles_add", ["config", "profiles", "add", "fast", "--json"], 0),
    (
        "config_profiles_set",
        ["config", "profiles", "set", "fast", "general.default_mode", "thinking", "--json"],
        0,
    ),
    (
        "config_profiles_unset",
        ["config", "profiles", "unset", "fast", "general.default_mode", "--json"],
        0,
    ),
    ("config_profiles_remove", ["config", "profiles", "remove", "fast", "--json"], 0),
    # P40: config validate
    ("config_validate_template", ["config", "validate", _SHIPPED_TEMPLATE, "--json"], 0),
    (
        "config_validate_missing_file",
        ["config", "validate", "/nonexistent/p40-test.toml", "--json"],
        1,
    ),
]

AMBIGUOUS_CONFIG_JSON_COMMANDS: list[tuple[str, list[str]]] = [
    ("config_get", ["config", "get", "paths.base_output_dir", "--json"]),
    ("config_list", ["config", "list", "--json"]),
    ("providers_list", ["providers", "list", "--json"]),
    ("providers_models", ["providers", "models", "--json"]),
    ("providers_check", ["providers", "check", "--json"]),
    ("modes_list", ["modes", "list", "--json"]),
    ("list", ["list", "--json"]),
    ("status", ["status", "research-MISSING", "--json"]),
    ("cancel", ["cancel", "research-MISSING", "--json"]),
    ("ask", ["ask", "--json", "--provider", "mock", "--api-key-mock", "test", "hello"]),
]


@pytest.fixture
def cli():
    from doxa_research.cli import cli as _cli

    return _cli


@pytest.mark.parametrize("label,argv,exit_code", JSON_COMMANDS, ids=[c[0] for c in JSON_COMMANDS])
def test_json_envelope_contract(label, argv, exit_code, cli, isolated_doxa_home, monkeypatch):
    # `config edit` opens $EDITOR; force a no-op editor for the parametrize row.
    if "edit" in argv:
        monkeypatch.setenv("EDITOR", "true")
    runner = CliRunner()  # NOTE: drop mix_stderr=False — Click 8.3 removed it (PR2 precedent)
    # P21b profile-row seeding: rows that exercise a profile target need the
    # `fast` profile (and sometimes a key/value or persisted default) in place
    # before the target argv runs. Seed via the same runner so the isolated
    # XDG_CONFIG_HOME from `isolated_doxa_home` stays consistent.
    _PROFILE_SEED_ADD = {
        "config_profiles_show",
        "config_profiles_set",
        "config_profiles_remove",
        "config_profiles_set_default",
        "config_profiles_unset",
        "config_profiles_unset_default",
    }
    if label in _PROFILE_SEED_ADD:
        seed = runner.invoke(cli, ["config", "profiles", "add", "fast"], catch_exceptions=False)
        assert seed.exit_code == 0, f"{label} seed (add fast) failed: {seed.output}"
    if label == "config_profiles_unset":
        seed = runner.invoke(
            cli,
            ["config", "profiles", "set", "fast", "general.default_mode", "thinking"],
            catch_exceptions=False,
        )
        assert seed.exit_code == 0, f"{label} seed (set) failed: {seed.output}"
    if label == "config_profiles_unset_default":
        seed = runner.invoke(
            cli,
            ["config", "profiles", "set-default", "fast"],
            catch_exceptions=False,
        )
        assert seed.exit_code == 0, f"{label} seed (set-default) failed: {seed.output}"

    if label == "init_non_interactive":
        # `doxa init` defaults to writing ./doxa.config.toml, so keep this
        # success-contract row independent of the repository cwd.
        with runner.isolated_filesystem(temp_dir=isolated_doxa_home):
            result = runner.invoke(cli, argv, catch_exceptions=False)
    else:
        result = runner.invoke(cli, argv, catch_exceptions=False)

    assert result.exit_code == exit_code, f"{label}: output={result.output}"
    payload = json.loads(result.output)
    assert isinstance(payload, dict), f"{label}: not a dict"
    assert payload.get("status") in ("ok", "error"), f"{label}: bad status field"
    if payload["status"] == "ok":
        assert isinstance(payload.get("data"), dict), f"{label}: ok-envelope missing data dict"
    else:
        err = payload.get("error")
        assert isinstance(err, dict), f"{label}: error-envelope missing error dict"
        assert isinstance(err.get("code"), str)
        assert isinstance(err.get("message"), str)


def test_init_json_without_non_interactive_emits_JSON_REQUIRES_NONINTERACTIVE(
    cli, isolated_doxa_home
):
    runner = CliRunner()
    result = runner.invoke(cli, ["init", "--json"], catch_exceptions=False)

    assert result.exit_code == 2
    payload = json.loads(result.output)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "JSON_REQUIRES_NONINTERACTIVE"


def test_status_json_missing_op_emits_OPERATION_NOT_FOUND(cli, isolated_doxa_home):
    runner = CliRunner()
    result = runner.invoke(cli, ["status", "research-MISSING", "--json"], catch_exceptions=False)

    assert result.exit_code == 6
    payload = json.loads(result.output)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "OPERATION_NOT_FOUND"


def test_config_edit_json_with_editor_true_emits_success_envelope(
    cli, isolated_doxa_home, monkeypatch
):
    monkeypatch.setenv("EDITOR", "true")
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "edit", "--json"], catch_exceptions=False)
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["status"] == "ok"


@pytest.mark.parametrize(
    "label,argv",
    AMBIGUOUS_CONFIG_JSON_COMMANDS,
    ids=[c[0] for c in AMBIGUOUS_CONFIG_JSON_COMMANDS],
)
def test_json_commands_emit_config_ambiguous_envelope(label, argv, cli, isolated_doxa_home):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=isolated_doxa_home) as cwd:
        Path(cwd, "doxa.config.toml").write_text('version = "2.0"\n')
        Path(cwd, ".doxa.config.toml").write_text('version = "2.0"\n')

        result = runner.invoke(cli, argv, catch_exceptions=False)

    assert result.exit_code == 1, f"{label}: output={result.output}"
    payload = json.loads(result.output)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "CONFIG_AMBIGUOUS"
    assert "Traceback" not in result.output
