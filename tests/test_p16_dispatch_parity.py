"""P16-TS01..17: post-refactor invocations match pre-refactor baselines.

Parity policy (decided in T15):
- 8 byte-stable invocations whose stdout/stderr we trust line-set-equal across
  the refactor (PARITY_LABELS below).
- 7 structural tests for invocations whose pre-refactor stdout was a pre-refactor
  bug (e.g. Click leaking parent help) or whose layout intentionally changed
  (e.g. two-section --help layout per T11). Structural tests assert behavioral
  contracts (exit code, key substrings) without freezing the exact byte
  rendering.

Skipped before parity is in scope (e.g. if DOXA_PARITY_SKIP=1 env is set
during early refactor scaffolding).
"""

from __future__ import annotations

import os
import re

import pytest

PARITY_LABELS = [
    # `version_short` / `version_long` removed: byte-stable baselines can't
    # track the live `__version__` that release-please bumps each release.
    # Covered structurally by `test_version_flags_structural` below.
    "status_no_args",
    "providers_list",
    "config_list",
    "modes_no_args",
    # "help_auth" removed in P16 PR2 T8 — `doxa help auth` virtual topic
    # was dropped per Q5-A row 13.ii.
    "unknown_command",
]


@pytest.mark.parametrize("label", PARITY_LABELS)
def test_dispatch_parity(label: str, baseline, run_doxa):
    """P16-TS01: post-refactor exit_code, stdout, AND stderr match baseline (line-set equality)."""
    if os.getenv("DOXA_PARITY_SKIP") == "1":
        pytest.skip("parity gate temporarily disabled during scaffolding")

    expected = baseline(label)
    exit_code, stdout, stderr = run_doxa(expected["argv"])

    assert exit_code == expected["exit_code"], (
        f"exit_code mismatch for {label}: got {exit_code}, baseline {expected['exit_code']}"
    )
    # Both stdout and stderr: line-set equality (sorted set of lines).
    # Tolerates Click's terminal-width-dependent re-formatting; catches
    # added/removed lines and exit-code changes. Strict line-order checks
    # for the --help layout live in tests/test_p16_doxagroup.py (added in T11).
    assert sorted(stdout.splitlines()) == sorted(expected["stdout"].splitlines()), (
        f"stdout drift for {label}"
    )
    assert sorted(stderr.splitlines()) == sorted(expected["stderr"].splitlines()), (
        f"stderr drift for {label}"
    )


def test_version_flags_structural(run_doxa):
    """`-V` and `--version` exit 0 with `Doxa Research vX.Y.Z` on stdout, no stderr.

    Structural rather than byte-stable so release-please version bumps don't
    have to update test baselines on every release.
    """
    for flag in ("-V", "--version"):
        exit_code, stdout, stderr = run_doxa([flag])
        assert exit_code == 0, f"{flag}: exit_code={exit_code}, stderr={stderr!r}"
        assert stderr == "", f"{flag}: unexpected stderr {stderr!r}"
        assert re.fullmatch(r"Doxa Research v\d+\.\d+\.\d+\s*", stdout), (
            f"{flag}: stdout {stdout!r} does not match Doxa Research vX.Y.Z"
        )


def test_help_unknown_topic_errors_structural(run_doxa):
    """P16-TS12: doxa help <unknown-topic> exits non-zero with a clear error."""
    exit_code, stdout, stderr = run_doxa(["help", "nosuchtopic"])
    assert exit_code != 0
    combined = stdout + stderr
    assert "nosuchtopic" in combined.lower() or "unknown" in combined.lower()


def test_init_help_structural(run_doxa):
    """P16-TS13: doxa init --help shows the init subcommand's help (not parent)."""
    exit_code, stdout, stderr = run_doxa(["init", "--help"])
    assert exit_code == 0
    assert "init" in stdout.lower()
    assert "Initialize" in stdout or "initialize" in stdout


def test_list_help_structural(run_doxa):
    """P16-TS14: doxa list --help shows the list subcommand's help (not parent)."""
    exit_code, stdout, stderr = run_doxa(["list", "--help"])
    assert exit_code == 0
    assert "list" in stdout.lower()
    assert "--all" in stdout or "operations" in stdout.lower()


def test_providers_no_args_lists_subcommands(run_doxa):
    """P16-TS15: doxa providers (no args) lists list/models/check subcommands.

    Click's natural behavior for a subgroup invoked without a subcommand is
    to print the usage/command listing and exit 2. We accept either 0 or 2
    here — the contract is that the subcommand list is reachable.
    """
    exit_code, stdout, stderr = run_doxa(["providers"])
    assert exit_code in (0, 2)
    combined = stdout + stderr
    # Click lists the subcommands somewhere
    assert "list" in combined
    assert "models" in combined
    assert "check" in combined


def test_config_no_args_errors_with_op_hint(run_doxa):
    """P16-TS16: doxa config (no op) exits 2 with hint about required op."""
    exit_code, stdout, stderr = run_doxa(["config"])
    assert exit_code == 2
    combined = stdout + stderr
    assert "op" in combined.lower() or "required" in combined.lower() or "(get|set" in combined


def test_help_init_forwards_to_subcommand(run_doxa):
    """P16-TS17: doxa help init forwards to init's --help."""
    exit_code, stdout, stderr = run_doxa(["help", "init"])
    assert exit_code == 0
    assert "init" in stdout.lower()


def test_fallback_timeout_options_are_coerced_to_float():
    """Post-prompt global options should match Click's option typing."""
    from doxa_research.cli import _extract_fallback_options

    positional, parsed = _extract_fallback_options(["prompt", "--timeout", "30.0"], {})

    assert positional == ["prompt"]
    assert parsed["timeout"] == 30.0
    assert isinstance(parsed["timeout"], float)

    positional, parsed = _extract_fallback_options(["prompt", "--timeout=0.001"], {})

    assert positional == ["prompt"]
    assert parsed["timeout"] == 0.001
    assert isinstance(parsed["timeout"], float)
