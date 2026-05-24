"""P40 TS05: structural assertion that lefthook.yml has the
validate-starter-template pre-commit entry wired correctly.

A temp-repo smoke test is intentionally avoided because `uv run doxa`
requires an importable project environment that a temp repo cannot offer.
See docs/superpowers/specs/2026-05-21-p40-on-disk-starter-template-design.md.
"""

from __future__ import annotations

from pathlib import Path

import yaml


def test_ts05_validate_starter_template_hook_is_configured() -> None:
    config = yaml.safe_load(Path("lefthook.yml").read_text(encoding="utf-8"))

    commands = (config.get("pre-commit") or {}).get("commands") or {}
    entry = commands.get("validate-starter-template")
    assert entry is not None, (
        "lefthook.yml: pre-commit.commands.validate-starter-template entry is missing"
    )

    assert entry.get("glob") == "src/doxa_research/data/starter.config.toml", (
        f"lefthook.yml: validate-starter-template glob should be the shipped template path, "
        f"got {entry.get('glob')!r}"
    )

    run = (entry.get("run") or "").strip()
    assert "doxa config validate" in run, (
        f"lefthook.yml: validate-starter-template should run `doxa config validate`, got {run!r}"
    )
    assert "src/doxa_research/data/starter.config.toml" in run, (
        f"lefthook.yml: validate-starter-template should target the shipped template path, "
        f"got {run!r}"
    )
