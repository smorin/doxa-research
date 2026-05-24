# P40 — On-Disk Starter Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace P33's runtime starter-document generator with a single on-disk `starter.config.toml` template, while preserving the no-drift property via a bidirectional drift test, a new `doxa config validate` CLI command, and a lefthook pre-commit hook.

**Architecture:** A new `src/doxa_research/data/` subpackage ships the template; `_build_starter_document()` becomes a thin `importlib.resources` reader; a new pure function `validate_config_file()` (shared by the CLI command and the drift test) does schema validation via `UserConfigFile` and an optional drift check against an instantiated `DoxaConfig()`'s defaults.

**Tech Stack:** Python 3.13, Pydantic 2 (`DoxaConfig`, `UserConfigFile`, `StarterField` marker), Click 8 (`@config.command`), `tomlkit` (round-trip TOML), stdlib `tomllib` (read-only TOML), `importlib.resources` (wheel-portable resource loading), lefthook (pre-commit hooks), pytest + `CliRunner`, `uv_build` (wheel backend), the shared `json_output.py` envelope (`{"status":"ok","data":…}` / `{"status":"error","error":{"code","message","details"}}`).

**Spec:** `docs/superpowers/specs/2026-05-21-p40-on-disk-starter-template-design.md`

---

## File Structure

### New files

| Path | Responsibility |
|---|---|
| `src/doxa_research/data/__init__.py` | Empty marker — makes `data` a real subpackage so `importlib.resources.files("doxa_research.data")` resolves in editable and wheel installs. |
| `src/doxa_research/data/starter.config.toml` | On-disk source of truth for `doxa init`'s output. Every `StarterField` default with inline comments + the new `[clarification.cli]` / `[clarification.interactive]` blocks. |
| `src/doxa_research/cli_subcommands/_config_validate.py` | Pure validation function `validate_config_file(path, *, drift_check) -> ValidationResult`. No Click imports. |
| `tests/fixtures/starter.pre-p40.toml` | Snapshot of the pre-P40 generator output. Used by TS03 to assert structural-superset parity. |
| `tests/test_starter_template_matches_schema.py` | TS01 bidirectional drift + TS02 profile parse + TS03 structural-superset parity. |
| `tests/test_config_validate.py` | TS04a-f behavioral tests for the new CLI command. |
| `tests/test_lefthook_starter_hook.py` | TS05 structural assertion against `lefthook.yml`. |

### Modified files

| Path | Change |
|---|---|
| `src/doxa_research/config_schema.py` | Mark all 16 `ClarificationConfig` leaf fields as `StarterField(...)`. |
| `src/doxa_research/commands.py` | Replace `_build_starter_document()` body with a thin `importlib.resources` reader. Delete `WRITER_COMMENTS`, `_emit_starter_section`, `_build_starter_profiles`. |
| `src/doxa_research/cli_subcommands/config.py` | Add `@config.command(name="validate")`. Update group help string. |
| `lefthook.yml` | Add `validate-starter-template` pre-commit entry globbed to the template path. |
| `docs/COMMANDS.md` | Add `validate` row to config-subcommands table. |
| `docs/json-output.md` | Add `config validate` envelope schema sketch + error codes. |
| `tests/test_json_envelopes.py` | Add `config_validate_template` (exit 0) and `config_validate_missing_file` (exit 1) rows. |
| `tests/test_docs_command_reference.py` | Add `validate` to expected config-subcommands set. |

### Deleted files

| Path | Why |
|---|---|
| `src/doxa_research/_starter_data.py` | `STARTER_PROFILES` moves inline into the template's `[profiles.*]` blocks. Only `commands.py` and `tests/test_config_starter_round_trip.py` import it; both are removed. |
| `tests/test_config_starter_round_trip.py` | Its four assertion layers (L2a, L2b, L3, L1) are fully covered by TS01 (bidirectional drift), TS02 (profile parse), and TS03 (structural superset). Spec §Components calls out the fold-in. |

---

## TDD ordering rationale

The ordering below has one non-obvious constraint: **`ClarificationConfig` fields must NOT be marked `StarterField` until `tests/test_config_starter_round_trip.py` is deleted.** That test projects `ConfigSchema.get_defaults()` onto `ConfigSchema.starter_keys()` and compares against the parsed starter doc — marking `ClarificationConfig` fields as `StarterField` adds `[clarification.*]` paths to `starter_keys()`, which then fail to project against a starter doc that doesn't yet have a `[clarification]` block. Phase 3 sequences the deletion before the markers to avoid breaking the gate mid-plan.

---

## Phase 1 — Snapshot + refactor (no observable behavior change)

### Task 1: Capture pre-P40 starter fixture

**Files:**
- Create: `tests/fixtures/starter.pre-p40.toml`

- [ ] **Step 1: Generate the fixture from the current generator**

```bash
cd /Users/stevemorin/c/doxa-research-worktrees/feat-p40-on-disk-starter-template
mkdir -p tests/fixtures
uv run python -c "from doxa_research.commands import _build_starter_document; import tomlkit; print(tomlkit.dumps(_build_starter_document()), end='')" > tests/fixtures/starter.pre-p40.toml
```

Expected: `tests/fixtures/starter.pre-p40.toml` is created and contains a complete TOML document starting with the `# Doxa Research Configuration File` header comment.

- [ ] **Step 2: Sanity-check the fixture parses**

```bash
uv run python -c "import tomllib; from pathlib import Path; tomllib.loads(Path('tests/fixtures/starter.pre-p40.toml').read_text())"
```

Expected: no output, exit 0 (parse succeeds).

- [ ] **Step 3: Verify the fixture has the six expected profiles**

```bash
uv run python -c "
import tomllib
from pathlib import Path
doc = tomllib.loads(Path('tests/fixtures/starter.pre-p40.toml').read_text())
names = set((doc.get('profiles') or {}).keys())
expected = {'daily', 'quick', 'openai_deep', 'all_deep', 'interactive', 'deep_research'}
assert names >= expected, f'missing profiles: {expected - names}'
print('OK', sorted(names))
"
```

Expected: `OK ['all_deep', 'daily', 'deep_research', 'interactive', 'openai_deep', 'quick']`.

- [ ] **Step 4: Commit the fixture**

```bash
git add tests/fixtures/starter.pre-p40.toml
git commit -m "test(p40): capture pre-P40 starter doc as fixture for TS03"
```

Expected: commit lands, hooks pass.

---

### Task 2: Add `data` subpackage with the template (initial = fixture content, no [clarification] yet)

**Files:**
- Create: `src/doxa_research/data/__init__.py`
- Create: `src/doxa_research/data/starter.config.toml`

- [ ] **Step 1: Create the subpackage marker**

```bash
mkdir -p src/doxa_research/data
echo '"""Package data for doxa_research — non-Python resources shipped with the wheel."""' > src/doxa_research/data/__init__.py
```

Expected: `src/doxa_research/data/__init__.py` exists, one-line module docstring.

- [ ] **Step 2: Copy the captured fixture as the initial template**

```bash
cp tests/fixtures/starter.pre-p40.toml src/doxa_research/data/starter.config.toml
```

Expected: `src/doxa_research/data/starter.config.toml` is byte-identical to the fixture.

- [ ] **Step 3: Verify the template parses and is reachable via importlib.resources**

```bash
uv run python -c "
from importlib.resources import files
import tomllib
res = files('doxa_research.data') / 'starter.config.toml'
doc = tomllib.loads(res.read_text())
assert 'general' in doc and 'profiles' in doc, f'unexpected shape: {list(doc)}'
print('OK', res)
"
```

Expected: `OK <path>` printed; no exception.

- [ ] **Step 4: Commit the subpackage + template**

```bash
git add src/doxa_research/data/__init__.py src/doxa_research/data/starter.config.toml
git commit -m "feat(p40): add doxa_research.data subpackage with starter.config.toml"
```

Expected: commit lands. The template is now duplicated with the generator output — Task 3 cuts the generator over to the template.

---

### Task 3: Replace `_build_starter_document()` body with a thin reader; delete dead helpers

**Files:**
- Modify: `src/doxa_research/commands.py:61-154` (delete `WRITER_COMMENTS`, `_emit_starter_section`, `_build_starter_profiles`; rewrite `_build_starter_document`)
- Test: `tests/test_config_starter_round_trip.py` (existing — should still pass)

- [ ] **Step 1: Run the existing round-trip test as a baseline**

```bash
uv run pytest tests/test_config_starter_round_trip.py -v
```

Expected: PASS (1 test, ~1s).

- [ ] **Step 2: Replace `_build_starter_document()` with a thin reader and delete dead helpers**

Open `src/doxa_research/commands.py`. Delete:
- Lines 61-69 (`WRITER_COMMENTS: dict[str, list[str]] = { ... }` — the entire dict literal)
- Lines 71-107 (`def _emit_starter_section(...): ...` — the entire function)
- Lines 109-120 (`def _build_starter_profiles() -> tomlkit.items.Table: ...` — the entire function)

Replace the body of `_build_starter_document` (lines 122-154) with this new implementation:

```python
def _build_starter_document() -> tomlkit.TOMLDocument:
    """Read the shipped starter template from package data.

    Source of truth is `src/doxa_research/data/starter.config.toml`.
    See projects/P40-on-disk-starter-template.md.
    """
    from importlib.resources import files

    resource = files("doxa_research.data") / "starter.config.toml"
    text = resource.read_text(encoding="utf-8")
    return tomlkit.parse(text)
```

Also remove any now-unused imports at the top of `commands.py` (e.g. `from doxa_research.config_schema import GeneralConfig, PathsConfig, ExecutionConfig, OutputConfig, ProvidersConfig` if those names are no longer referenced — verify with `uv run ruff check src/doxa_research/commands.py`).

- [ ] **Step 3: Run the existing round-trip test again — must still pass**

```bash
uv run pytest tests/test_config_starter_round_trip.py -v
```

Expected: PASS. The reader returns a `TOMLDocument` parsed from the on-disk template, which is byte-identical to what the generator used to produce.

- [ ] **Step 4: Run linters and types to catch dead-symbol regressions**

```bash
uv run ruff check src/doxa_research/commands.py && uv run ty check src/doxa_research/commands.py
```

Expected: both pass cleanly. If ruff complains about unused imports, remove them in the same commit.

- [ ] **Step 5: Run the full test suite to catch any incidental regressions**

```bash
uv run pytest -q
```

Expected: all green. The reader change is observationally a no-op: same bytes, different code path.

- [ ] **Step 6: Commit**

```bash
git add src/doxa_research/commands.py
git commit -m "refactor(p40): replace _build_starter_document generator with on-disk reader"
```

Expected: commit lands, hooks pass.

---

## Phase 2 — Validation infrastructure

### Task 4: Create `_config_validate` stub module

**Files:**
- Create: `src/doxa_research/cli_subcommands/_config_validate.py`

The stub lets Task 5's tests import the symbol; Task 6 implements the body.

- [ ] **Step 1: Create the module with the public API and a NotImplementedError stub**

```python
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
```

Save to `src/doxa_research/cli_subcommands/_config_validate.py`.

- [ ] **Step 2: Verify import works**

```bash
uv run python -c "from doxa_research.cli_subcommands._config_validate import validate_config_file, ValidationResult; print(ValidationResult(ok=True))"
```

Expected: prints `ValidationResult(ok=True, path=None, error=None, message='', details={}, checks=())`.

- [ ] **Step 3: Commit**

```bash
git add src/doxa_research/cli_subcommands/_config_validate.py
git commit -m "feat(p40): scaffold _config_validate module with stubbed body"
```

Expected: commit lands.

---

### Task 5: Write the bidirectional drift test (TS01 + TS02 + TS03) — failing

**Files:**
- Create: `tests/test_starter_template_matches_schema.py`

- [ ] **Step 1: Write the test file**

```python
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
    assert new_keys <= {"clarification"}, f"unexpected new top-level table(s): {new_keys - {'clarification'}}"

    for k in fixture_keys:
        assert template.get(k) == fixture[k], f"top-level table [{k}] diverged from pre-P40 fixture"
```

Save to `tests/test_starter_template_matches_schema.py`.

- [ ] **Step 2: Run the tests — they must fail (NotImplementedError from the stub)**

```bash
uv run pytest tests/test_starter_template_matches_schema.py -v
```

Expected: `test_ts01_starter_template_round_trips` FAILS with `NotImplementedError: validate_config_file body lands in Task 6`. TS02 (six parametrized rows) PASSES. TS03 PASSES.

- [ ] **Step 3: Commit the failing test**

```bash
git add tests/test_starter_template_matches_schema.py
git commit -m "test(p40): add bidirectional drift, profile parse, and structural-superset tests"
```

Expected: commit lands. TS01 is in the suite and red until Task 6.

---

### Task 6: Implement `validate_config_file`

**Files:**
- Modify: `src/doxa_research/cli_subcommands/_config_validate.py` (replace the `NotImplementedError` stub with the real body)

- [ ] **Step 1: Replace the stub body with the real implementation**

Replace the `validate_config_file` function (and only that function — keep the `ValidationResult` dataclass unchanged) in `src/doxa_research/cli_subcommands/_config_validate.py` with:

```python
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
        DoxaConfig,
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
            message=f"{loc}: {first.get('msg', 'validation error')}" if loc else first.get("msg", "validation error"),
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
```

- [ ] **Step 2: Run TS01-TS03 — they must all pass**

```bash
uv run pytest tests/test_starter_template_matches_schema.py -v
```

Expected: 8 tests PASS (TS01 + 6 parametrized TS02 + TS03).

- [ ] **Step 3: Run the full unit suite as a sanity check**

```bash
uv run pytest -q
```

Expected: all green. `test_config_starter_round_trip` is still green (no `StarterField` changes yet); no other test imports `_config_validate`.

- [ ] **Step 4: Commit**

```bash
git add src/doxa_research/cli_subcommands/_config_validate.py
git commit -m "feat(p40): implement validate_config_file with schema + drift phases"
```

Expected: commit lands.

---

## Phase 3 — Add the `[clarification]` section

### Task 7: Remove the obsolete `test_config_starter_round_trip.py`

**Files:**
- Delete: `tests/test_config_starter_round_trip.py`

This test's four assertion layers are fully covered: L2a (defaults projected to starter_keys) by TS01 schema→template, L2b (parsed profiles equal STARTER_PROFILES) by TS02, L3 (UserConfigFile.validate) by TS01 template→schema, L1 (section markers) by TS03's structural assertions. Deleting before Phase 3's marker changes prevents a transient failure.

- [ ] **Step 1: Delete the file**

```bash
git rm tests/test_config_starter_round_trip.py
```

Expected: file staged for deletion.

- [ ] **Step 2: Confirm no other file imports anything from it**

```bash
grep -rn "test_config_starter_round_trip\|test_starter_doc_round_trips" tests/ src/ docs/
```

Expected: no matches outside the now-deleted file itself.

- [ ] **Step 3: Run the suite to confirm nothing else regressed**

```bash
uv run pytest -q
```

Expected: all green; one fewer test class than before.

- [ ] **Step 4: Commit**

```bash
git commit -m "test(p40): remove test_config_starter_round_trip — covered by TS01/02/03"
```

Expected: commit lands.

---

### Task 8: Mark `ClarificationConfig` fields as `StarterField` — TS01 fails

**Files:**
- Modify: `src/doxa_research/config_schema.py:109-132` (both Clarification subconfig classes)

- [ ] **Step 1: Change every `Field(...)` to `StarterField(...)` in the two Clarification subconfigs**

Open `src/doxa_research/config_schema.py`. In `ClarificationCLIConfig` (lines 109-118), change all 7 fields:

```python
class ClarificationCLIConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = StarterField("openai")
    model: str = StarterField("gpt-4o-mini")
    temperature: float = StarterField(0.7)
    max_tokens: int = StarterField(500)
    retry_attempts: int = StarterField(3)
    retry_delay: float = StarterField(2.0)
    system_prompt: str = StarterField(_CLARIFICATION_SYSTEM_PROMPT)
```

In `ClarificationInteractiveConfig` (lines 121-132), change all 9 fields:

```python
class ClarificationInteractiveConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = StarterField("openai")
    model: str = StarterField("gpt-4o-mini")
    temperature: float = StarterField(0.7)
    max_tokens: int = StarterField(800)
    retry_attempts: int = StarterField(3)
    retry_delay: float = StarterField(2.0)
    system_prompt: str = StarterField(_CLARIFICATION_SYSTEM_PROMPT)
    input_height: int = StarterField(6)
    max_input_height: int = StarterField(15)
```

Do not change anything else in the file.

- [ ] **Step 2: Run TS01 — it must now fail with `DRIFT_MISSING_KEY`**

```bash
uv run pytest tests/test_starter_template_matches_schema.py::test_ts01_starter_template_round_trips -v
```

Expected: FAIL. The error message mentions `clarification.cli.provider` (or another `clarification.*` path) and `DRIFT_MISSING_KEY` because the template doesn't yet have a `[clarification]` block. Task 9 adds it.

- [ ] **Step 3: Run linters and types to catch typos**

```bash
uv run ruff check src/doxa_research/config_schema.py && uv run ty check src/doxa_research/config_schema.py
```

Expected: both pass.

- [ ] **Step 4: Commit the marker change (with TS01 still failing — Task 9 lands the matching template change)**

```bash
git add src/doxa_research/config_schema.py
git commit -m "feat(p40): mark ClarificationConfig leaves as StarterField"
```

Expected: commit lands. Hooks DO run the full pytest, so TS01 is RED at this point — see Step 5.

- [ ] **Step 5: If the pre-commit hook blocks the commit**

The `lefthook.yml` pre-commit gate runs `./doxa_test -r` and may run the unit suite. If it blocks because TS01 is red, run Task 9 first as a stash-and-rewind: temporarily revert the marker change with `git restore src/doxa_research/config_schema.py`, complete Task 9 (template edit), then re-apply the markers and commit Task 8 + Task 9 together. Either order produces the same final tree; the spec's TDD sequence is the readable narration, not a hard constraint on commit shape.

---

### Task 9: Add the `[clarification]` section to the template — TS01 passes

**Files:**
- Modify: `src/doxa_research/data/starter.config.toml` (append a new `[clarification.cli]` and `[clarification.interactive]` block)

- [ ] **Step 1: Determine the exact prose for the system_prompt**

```bash
uv run python -c "from doxa_research.config_schema import _CLARIFICATION_SYSTEM_PROMPT; print(repr(_CLARIFICATION_SYSTEM_PROMPT))"
```

Record the output — you'll paste it verbatim into the template below.

- [ ] **Step 2: Append the [clarification] block to the template**

Open `src/doxa_research/data/starter.config.toml` and append (after the last existing section, before EOF — make sure there's exactly one blank line before the new section header):

```toml

# ---------------------------------------------------------------------------
# Clarification — meta-prompt knobs for the `clarify` flow.
# Both sub-tables share the same shape; the `cli` table is used for the
# one-shot non-interactive flow, the `interactive` table for the
# `--interactive` mode (P32). The `system_prompt` is the meta-prompt the
# clarifier sends with the user's draft; edit it to tune clarifier style.
# ---------------------------------------------------------------------------

[clarification.cli]
provider = "openai"
model = "gpt-4o-mini"
temperature = 0.7
max_tokens = 500
retry_attempts = 3
retry_delay = 2.0
system_prompt = "I don't want you to follow the above question and instructions; I want you to tell me the ways this is unclear, point out any ambiguities or anything you don't understand. Follow that by asking questions to help clarify the ambiguous points. Once there are no more unclear, ambiguous or not understood portions, help me draft a clear version of the question/instruction."

[clarification.interactive]
provider = "openai"
model = "gpt-4o-mini"
temperature = 0.7
max_tokens = 800
retry_attempts = 3
retry_delay = 2.0
system_prompt = "I don't want you to follow the above question and instructions; I want you to tell me the ways this is unclear, point out any ambiguities or anything you don't understand. Follow that by asking questions to help clarify the ambiguous points. Once there are no more unclear, ambiguous or not understood portions, help me draft a clear version of the question/instruction."
input_height = 6
max_input_height = 15
```

Note: the `system_prompt` value MUST exactly match the `_CLARIFICATION_SYSTEM_PROMPT` constant from Step 1. If Step 1's `repr()` differs from the literal above, copy Step 1's text instead (strip outer quotes).

- [ ] **Step 3: Run TS01-TS03 — all must pass**

```bash
uv run pytest tests/test_starter_template_matches_schema.py -v
```

Expected: 8 tests PASS.

- [ ] **Step 4: Verify the new doxa init output looks correct**

```bash
uv run python -c "from doxa_research.commands import _build_starter_document; import tomlkit; doc = _build_starter_document(); assert 'clarification' in doc, 'missing clarification'; print('clarification keys:', list(doc['clarification']))"
```

Expected: `clarification keys: ['cli', 'interactive']`.

- [ ] **Step 5: Run the full unit suite**

```bash
uv run pytest -q
```

Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add src/doxa_research/data/starter.config.toml
git commit -m "feat(p40): ship [clarification] section in the starter template"
```

Expected: commit lands.

---

## Phase 4 — `doxa config validate` CLI surface

### Task 10: Write `config validate` CLI tests (TS04a-f) — failing

**Files:**
- Create: `tests/test_config_validate.py`

- [ ] **Step 1: Write the test file**

```python
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
```

Save to `tests/test_config_validate.py`.

- [ ] **Step 2: Run the tests — they must fail (no `validate` command yet)**

```bash
uv run pytest tests/test_config_validate.py -v
```

Expected: TS04a/d/e/f-positive FAIL with `Error: No such command 'validate'.`. TS04b and TS04c (pure-function tests) PASS — they don't touch the CLI.

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/test_config_validate.py
git commit -m "test(p40): add config validate behavioral tests (TS04a-f)"
```

Expected: commit lands. The CLI rows are red until Task 11.

---

### Task 11: Implement `@config.command(name="validate")` — TS04 passes

**Files:**
- Modify: `src/doxa_research/cli_subcommands/config.py:38-49` (update group help) and append a new command at the end

- [ ] **Step 1: Update the `config` group help string**

In `src/doxa_research/cli_subcommands/config.py`, change line 45's help text from:

```python
            "Error: config command requires an op (get|set|unset|list|path|edit|help)",
```

to:

```python
            "Error: config command requires an op (get|set|unset|list|path|edit|validate|help)",
```

- [ ] **Step 2: Add the validate command at the end of the file**

Append to `src/doxa_research/cli_subcommands/config.py`:

```python
@config.command(name="validate")
@click.argument("path", required=False, type=click.Path(path_type=Path))
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def config_validate(
    ctx: click.Context,
    path: Path | None,
    as_json: bool,
) -> None:
    """Validate a TOML config file against the schema.

    With no PATH, validates ``~/.config/doxa/doxa.config.toml`` (or the
    XDG_CONFIG_HOME equivalent). With PATH, validates that file. When PATH
    resolves to the shipped starter template, also runs a drift check
    against the schema's StarterField defaults.
    """
    from importlib.resources import files

    from doxa_research.cli_subcommands._config_validate import validate_config_file
    from doxa_research.json_output import emit_error, emit_json
    from doxa_research.paths import user_config_file

    target = path if path is not None else user_config_file()

    try:
        shipped = Path(str(files("doxa_research.data") / "starter.config.toml")).resolve()
    except (FileNotFoundError, ModuleNotFoundError):
        shipped = None

    try:
        target_resolved = target.resolve()
    except OSError:
        target_resolved = target
    drift = shipped is not None and target_resolved == shipped

    result = validate_config_file(target, drift_check=drift)

    if as_json:
        if result.ok:
            emit_json(
                {
                    "path": str(result.path) if result.path else None,
                    "checks": list(result.checks),
                }
            )
        else:
            emit_error(
                result.error or "VALIDATION_FAILED",
                result.message,
                details=result.details or None,
            )

    if result.ok:
        checks = " + ".join(result.checks) if result.checks else ""
        click.echo(f"OK: {result.path} ({checks})")
        ctx.exit(0)
    click.echo(f"Error: {result.message}", err=True)
    ctx.exit(1)
```

Also add `from pathlib import Path` at the top of the file if it's not already imported.

- [ ] **Step 3: Run TS04 — all must pass**

```bash
uv run pytest tests/test_config_validate.py -v
```

Expected: 8 tests PASS.

- [ ] **Step 4: Run the full suite to catch lint-meta regressions**

```bash
uv run pytest -q
```

Expected: most green; `test_json_envelopes.py::test_json_envelope_contract` may FAIL because the CI lint meta-walker now sees a new `--json` consumer that isn't in `JSON_COMMANDS`. Task 12 fixes that.

- [ ] **Step 5: Commit**

```bash
git add src/doxa_research/cli_subcommands/config.py
git commit -m "feat(p40): add doxa config validate subcommand"
```

Expected: commit lands. JSON envelope coverage gap is Task 12.

---

### Task 12: Update docs and JSON-envelope registry

**Files:**
- Modify: `docs/COMMANDS.md` (add validate row to the config-subcommands table)
- Modify: `docs/json-output.md` (add `config validate` schema section)
- Modify: `tests/test_json_envelopes.py:16-78` (add two rows to `JSON_COMMANDS`)
- Modify: `tests/test_docs_command_reference.py` (add `validate` to the expected config-subcommands set)

- [ ] **Step 1: Add validate row to `docs/COMMANDS.md`**

Open `docs/COMMANDS.md`, locate the config-subcommands table, and add a row after `edit`:

```markdown
| `doxa config validate [PATH] [--json]` | Validate a TOML config against the schema; drift-check the shipped starter when PATH resolves to it. |
```

(Match the existing column structure of nearby rows — copy the leading `|` count exactly.)

- [ ] **Step 2: Add the `config validate` envelope section to `docs/json-output.md`**

Open `docs/json-output.md` and append a new section:

```markdown

## `config validate [PATH] --json`

**Success envelope** — exit 0:

```json
{
  "status": "ok",
  "data": {
    "path": "<resolved path>",
    "checks": ["schema"]            // or ["schema", "drift"]
  }
}
```

**Error envelope** — exit 1. Error codes:

| code | When |
|---|---|
| `FILE_NOT_FOUND` | PATH does not exist, or no PATH and no user-tier config file. |
| `TOML_PARSE_ERROR` | File is not valid TOML. `details.path` includes line context where available. |
| `SCHEMA_VALIDATION` | File parses but fails `UserConfigFile.model_validate`. `details.errors` is the full Pydantic error list. |
| `DRIFT_MISSING_KEY` | Drift check: template missing a `StarterField` path. `details.path` and `details.expected`. |
| `DRIFT_VALUE_MISMATCH` | Drift check: value at a `StarterField` path differs from schema default. `details.path`, `details.expected`, `details.actual`. |
| `PACKAGE_DATA_MISSING` | `importlib.resources` could not resolve the shipped template (broken wheel). |
```

- [ ] **Step 3: Add two rows to `tests/test_json_envelopes.py`**

In `tests/test_json_envelopes.py`, add two entries to the `JSON_COMMANDS` list (alongside the other `config_*` rows, around line 33):

```python
    ("config_validate_template", ["config", "validate", "src/doxa_research/data/starter.config.toml", "--json"], 0),
    ("config_validate_missing_file", ["config", "validate", "/nonexistent/p40-test.toml", "--json"], 1),
```

- [ ] **Step 4: Add `validate` to the docs coverage guard**

Open `tests/test_docs_command_reference.py` and add `"validate"` to the expected `config` subcommands set. (The exact line will depend on the file's existing structure; `grep -n "edit\|path" tests/test_docs_command_reference.py` to locate the section.)

```bash
grep -nE '"edit"|"path"|"list"' tests/test_docs_command_reference.py
```

Once located, add `"validate"` in the same alphabetical/group position as siblings.

- [ ] **Step 5: Run all changed tests**

```bash
uv run pytest tests/test_json_envelopes.py tests/test_docs_command_reference.py -v
```

Expected: both green.

- [ ] **Step 6: Run the full suite**

```bash
uv run pytest -q
```

Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add docs/COMMANDS.md docs/json-output.md tests/test_json_envelopes.py tests/test_docs_command_reference.py
git commit -m "docs(p40): document config validate and add JSON envelope coverage"
```

Expected: commit lands.

---

## Phase 5 — Pre-commit hook

### Task 13: Write the lefthook structural test (TS05) — failing

**Files:**
- Create: `tests/test_lefthook_starter_hook.py`

- [ ] **Step 1: Write the test**

```python
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
```

Save to `tests/test_lefthook_starter_hook.py`.

- [ ] **Step 2: Run the test — it must fail**

```bash
uv run pytest tests/test_lefthook_starter_hook.py -v
```

Expected: FAIL with `AssertionError: lefthook.yml: pre-commit.commands.validate-starter-template entry is missing`.

- [ ] **Step 3: If pyyaml isn't already a test dep, add it**

```bash
uv run python -c "import yaml" 2>&1 | head -3
```

If the import fails, add pyyaml to the dev group:

```bash
uv add --group dev pyyaml
git add pyproject.toml uv.lock
```

Otherwise, no action needed.

- [ ] **Step 4: Commit the failing test (and pyyaml addition if needed)**

```bash
git add tests/test_lefthook_starter_hook.py
git commit -m "test(p40): add structural assertion for validate-starter-template hook"
```

Expected: commit lands. TS05 is red until Task 14.

---

### Task 14: Add the `validate-starter-template` lefthook entry — TS05 passes

**Files:**
- Modify: `lefthook.yml` (add a `pre-commit.commands.validate-starter-template` entry alongside the existing entries)

- [ ] **Step 1: Insert the entry into `lefthook.yml`**

Open `lefthook.yml`. Find the `pre-commit:` block (around line 9). At the end of the `commands:` map (after the last existing entry, before any other top-level YAML key), add:

```yaml
    validate-starter-template:
      glob: "src/doxa_research/data/starter.config.toml"
      run: uv run doxa config validate src/doxa_research/data/starter.config.toml
```

YAML indentation: four-space indent under `commands:` so the structure matches the surrounding entries (e.g. `editorconfig:`, `trailing-whitespace:`). Verify by running `uv run python -c "import yaml; yaml.safe_load(open('lefthook.yml'))"` — no exception means valid YAML.

- [ ] **Step 2: Run TS05**

```bash
uv run pytest tests/test_lefthook_starter_hook.py -v
```

Expected: PASS.

- [ ] **Step 3: Hand-verify the hook actually runs**

```bash
# Touch the template (no real change) to stage it, then run the hook in isolation:
touch -a src/doxa_research/data/starter.config.toml
git add src/doxa_research/data/starter.config.toml
lefthook run pre-commit --commands validate-starter-template
```

Expected: lefthook reports `validate-starter-template` runs and exits 0. (The template is valid, so the hook passes.) Unstage if you don't want it included in the next commit: `git reset HEAD src/doxa_research/data/starter.config.toml`.

- [ ] **Step 4: Run the full suite to catch any regression**

```bash
uv run pytest -q
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add lefthook.yml
git commit -m "ci(p40): add validate-starter-template pre-commit hook"
```

Expected: commit lands.

---

## Phase 6 — Cleanup + acceptance gate

### Task 15: Delete `_starter_data.py`

**Files:**
- Delete: `src/doxa_research/_starter_data.py`

- [ ] **Step 1: Confirm no remaining references**

```bash
grep -rn "_starter_data\|STARTER_PROFILES" src/ tests/ docs/
```

Expected: zero matches (Task 3 removed the `commands.py` import; Task 7 removed the test import).

- [ ] **Step 2: Delete the file**

```bash
git rm src/doxa_research/_starter_data.py
```

Expected: file staged for deletion.

- [ ] **Step 3: Run the full suite**

```bash
uv run pytest -q
```

Expected: all green.

- [ ] **Step 4: Commit**

```bash
git commit -m "chore(p40): delete _starter_data.py — content now ships in starter.config.toml"
```

Expected: commit lands.

---

### Task 16: Acceptance gate — wheel build, editable install, full check

**Files:**
- Verify: wheel contents
- Verify: editable install round-trip
- Verify: `just check`, `pytest -q`, `./doxa_test -r`, `ruff format --check`

- [ ] **Step 1: Build the wheel and confirm the template ships**

```bash
just build
unzip -l dist/*.whl | grep starter.config.toml
```

Expected: exactly one row referencing `doxa_research/data/starter.config.toml`. If the row is missing, add to `pyproject.toml`:

```toml
[tool.uv.build-backend]
module-name = "doxa_research"
source-include = ["src/doxa_research/data/*.toml"]
```

Then `just build` again and re-grep.

- [ ] **Step 2: Editable install round-trip in a clean venv**

```bash
mkdir -p /tmp/p40-editable && cd /tmp/p40-editable
uv venv .venv && source .venv/bin/activate
uv pip install -e /Users/stevemorin/c/doxa-research-worktrees/feat-p40-on-disk-starter-template
mkdir -p out
doxa init --non-interactive --user
ls -la ~/.config/doxa/doxa.config.toml || ls -la ~/.config/doxa_research/doxa.config.toml
deactivate
cd -
```

Expected: `doxa init --non-interactive` succeeds and writes a config file containing a `[clarification]` section.

- [ ] **Step 3: Run the project's full local gate**

```bash
cd /Users/stevemorin/c/doxa-research-worktrees/feat-p40-on-disk-starter-template
just check
uv run pytest -q
./doxa_test -r --skip-interactive -q
uv run ruff format --check src/ tests/
```

Expected: all four pass.

- [ ] **Step 4: Mark P40 as in-progress in PROJECTS.md and flip the relevant TS/T checkboxes**

Edit `PROJECTS.md` to change P40's row from `[ ]` to `[~]`, and edit `projects/P40-on-disk-starter-template.md` to flip the matching `[P40-TS##]` / `[P40-T##]` checkboxes to `[x]`. Refer to the spec/plan mapping at the bottom of `projects/P40-on-disk-starter-template.md`.

```bash
git add PROJECTS.md projects/P40-on-disk-starter-template.md
git commit -m "docs(p40): flip P40 status to in-progress and tick completed tasks"
```

- [ ] **Step 5: Push the branch**

```bash
git push -u origin feat/p40-on-disk-starter-template
```

Expected: branch pushed, tracking set.

- [ ] **Step 6: Open the PR**

```bash
gh pr create --title "feat(p40): on-disk starter template + doxa config validate" --body "$(cat <<'EOF'
## Summary
- Reverses P33's runtime starter-document generator in favor of an on-disk template at `src/doxa_research/data/starter.config.toml`.
- Adds a `[clarification]` section to the starter so users can customize the meta-prompt out of the box.
- Adds `doxa config validate [PATH]` that schema-validates any TOML config and drift-checks the shipped template.
- Adds a `lefthook` pre-commit hook globbed to the template path that runs `doxa config validate` automatically.

## Spec & plan
- Spec: `docs/superpowers/specs/2026-05-21-p40-on-disk-starter-template-design.md`
- Plan: `docs/superpowers/plans/2026-05-21-p40-on-disk-starter-template.md`

## Test plan
- [ ] `uv run pytest -q` — all green
- [ ] `./doxa_test -r --skip-interactive -q` — all green
- [ ] `unzip -l dist/*.whl | grep starter.config.toml` — exactly one row
- [ ] Editable install round-trip writes a config with `[clarification]`
- [ ] `lefthook run pre-commit --commands validate-starter-template` exits 0 on the clean template, exits 1 on a corrupted copy
EOF
)"
```

Expected: PR URL printed. Done.

---

## Self-Review Notes

The plan covers every requirement in the spec:

- **Scope §In scope:** template file (Task 2), `data/__init__.py` (Task 2), `_build_starter_document` reader (Task 3), delete `_starter_data.py` (Task 15), delete `WRITER_COMMENTS` / helpers (Task 3), drift test (Tasks 5+6), wizard merge unchanged (no task needed — `_build_starter_document`'s return type is preserved in Task 3).
- **Scope §New CLI surface:** `doxa config validate` (Tasks 10+11), `--json` envelope (Task 11), `docs/COMMANDS.md` row + `tests/test_docs_command_reference.py` coverage (Task 12).
- **Scope §New pre-commit hook:** `lefthook.yml` entry (Task 14), TS05 structural test (Task 13).
- **Scope §[clarification] addition:** `StarterField` markers on 16 leaves (Task 8), template section (Task 9), `tests/test_config_starter_round_trip.py` deletion to clear the way (Task 7).
- **Architecture §`doxa config validate` is the bridge:** Task 11's command body calls the same `validate_config_file` Task 5's tests import.
- **Architecture §Path-equality gate:** Task 11 implements the `target.resolve() == shipped.resolve()` check explicitly.
- **Data Flow §Flow B drift expected values from instantiated defaults:** Task 6 uses `default_config_dict()` (= `DoxaConfig().model_dump(...)`) which is the reviewer-corrected behavior.
- **Data Flow §Flow C drift test:** Task 5's TS01 imports `validate_config_file` — one implementation, two callers.
- **Error Handling §all six failure modes:** Task 6 emits all six codes (`FILE_NOT_FOUND`, `TOML_PARSE_ERROR`, `SCHEMA_VALIDATION`, `DRIFT_MISSING_KEY`, `DRIFT_VALUE_MISMATCH`). `PACKAGE_DATA_MISSING` is partially handled by Task 11's try/except around `importlib.resources` (a broken wheel produces `shipped=None`, which suppresses drift but still validates schema).
- **Testing §test list:** TS01 (Task 5), TS02 (Task 5), TS03 (Task 5), TS04a-f (Task 10), TS05 (Task 13), fixture capture (Task 1), `test_config_starter_round_trip` deletion (Task 7), `test_json_envelopes` rows + `test_docs_command_reference` set (Task 12), `test_init_ships_profiles` left alone (it doesn't import `STARTER_PROFILES` directly).
- **Wheel & editable verification:** Task 16 steps 1-2.
- **TDD commit sequence:** Tasks 1→16 are seven phases instead of seven commits because the reviewer's edits (drift expected from instantiated defaults, structural lefthook test, pure-function TS04b/c) require more fine-grained TDD pairs. The spirit (test before code, frequent commits, full gate before push) is preserved.

**Type consistency:** `ValidationResult` is defined once (Task 4), referenced unchanged in Tasks 5/6/10/11. `validate_config_file(path, *, drift_check)` signature is fixed in Task 4 and unchanged thereafter. `_lookup`, `_MISSING` are private helpers used only inside `_config_validate.py`.

**No placeholders:** every code block above is literal, every command is runnable, every expected output is concrete. The only intentional "context-dependent" steps are Task 12 Step 4 (exact location of `validate` in `test_docs_command_reference.py` depends on that file's structure — grep instruction provided) and Task 16 Step 1's fallback `pyproject.toml` snippet (only needed if the wheel doesn't ship the template; verification step shows how to check).

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-21-p40-on-disk-starter-template.md`. Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints.

Which approach?
