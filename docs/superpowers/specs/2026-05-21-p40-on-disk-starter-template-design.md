# P40 — On-Disk Starter Template Design

**Status:** Design approved, ready for implementation plan
**Date:** 2026-05-21
**Project trunk row:** [P40 — On-Disk Starter Template (Reverse P33 Generation)](../../../projects/P40-on-disk-starter-template.md)
**Predecessor:** P33 (`projects/P33-schema-driven-config-defaults.md`) — the project this reverses architecturally
**Branch:** `feat/p40-on-disk-starter-template`
**Worktree:** `../doxa-research-worktrees/feat-p40-on-disk-starter-template`

## Goal

Restore an on-disk starter config template as the source of truth for `doxa init` output, replacing the schema-driven generator introduced in P33. Preserve the no-drift property P33 was enforcing — but achieve it through a bidirectional drift test plus a new `doxa config validate` CLI command and lefthook pre-commit hook, rather than through runtime assembly of a single text artifact across three Python modules.

## Background

P33 split the starter `doxa.config.toml` bytes across three Python sources:

- `config_schema.py` — `StarterField(...)` default values
- `commands.py` — `WRITER_COMMENTS` dict for inline prose
- `_starter_data.py` — `STARTER_PROFILES` list for the six shipped profiles

The starter doc was assembled at runtime by `_build_starter_document()` walking those structures. The motivating gain was preventing drift between schema defaults and template literal values.

In practice the trade reads net-negative for this project's audience and cadence: contributors editing the starter file must work across three Python modules and execute the generator mentally to predict the on-disk output. The same drift property is recoverable from a ~30-line schema-walking test without the structural cost.

The reversal is also low-risk: the consumer surface (`doxa init`'s on-disk output) is unchanged. Only the *source* of those bytes changes, plus the deliberate addition of a `[clarification]` section to the starter (resolved during brainstorming — see Scope).

## Scope

### In scope

- **Template file** at `src/doxa_research/data/starter.config.toml` containing every `StarterField` value with inline comments.
- **`[clarification]` section is included** in the starter template. `ClarificationCLIConfig` (7 fields) and `ClarificationInteractiveConfig` (9 fields) all gain `StarterField(...)` markers. The duplicated `_CLARIFICATION_SYSTEM_PROMPT` prose ships inline in both sub-tables. This resolves the contradiction between P40's open-question Q2 answer and its out-of-scope statement — we honor the Q2 answer ("move into config so it's configurable").
- **`src/doxa_research/data/__init__.py`** (empty file) so `data` is an importable subpackage and `importlib.resources.files("doxa_research.data")` resolves under both editable and wheel installs.
- **`_build_starter_document()` becomes a thin reader.** Same signature, same return type (`tomlkit.TOMLDocument`). Body: load template bytes via `importlib.resources`, return `tomlkit.parse(text)`. All three call sites in `commands.py` (lines 224, 280, 423) keep working unchanged.
- **Delete `_starter_data.py`** entirely. `STARTER_PROFILES` moves inline into the template's `[profiles.*]` blocks.
- **Delete `WRITER_COMMENTS`, `_emit_starter_section`, `_build_starter_profiles`** from `commands.py`. Comments move inline next to values in the template.
- **New `doxa config validate [PATH]` subcommand** in `cli_subcommands/config.py`. With no PATH, validates `~/.config/doxa/doxa.config.toml`. With PATH, validates that file against `UserConfigFile` (the actual on-disk config shape, including `[profiles.*]`). When PATH resolves to the shipped starter template, also runs the bidirectional drift check. Supports `--json`.
- **New `cli_subcommands/_config_validate.py`** module containing the pure validation function. Imported by the CLI command and the drift test — one implementation, two callers.
- **Bidirectional drift test** (`tests/test_starter_template_matches_schema.py`):
  - Schema → template: every `StarterField` in `DoxaConfig` exists at the expected TOML path with the expected default value read from an instantiated `DoxaConfig()` at that same path.
  - Template → on-disk schema: `UserConfigFile.model_validate(tomllib.loads(template_text))` succeeds (catches stray keys, typos, `extra="forbid"` violations while allowing the shipped `[profiles.*]` blocks).
- **Lefthook pre-commit hook** entry scoped via `glob` to `src/doxa_research/data/starter.config.toml`. Invokes `uv run doxa config validate <path>`. Reuses the same code path as the standalone command.
- **Docs:** add `validate` row to `docs/COMMANDS.md` config-subcommands table and to the `tests/test_docs_command_reference.py` coverage guard.

### Out of scope

- Re-evaluating which profiles ship (that's P37, "Review starter-profile selection").
- Re-evaluating which non-`Clarification` schema fields are `StarterField` vs plain `Field` — the only schema markers changing in this PR are the 16 `ClarificationConfig` leaf fields.
- Changes to `doxa init`'s CLI surface (`--force`, `--non-interactive`, `--user`, `--hidden`) — unchanged.
- Changes to the user-tier config file location or filename.
- A `doxa config fix` auto-repair command — possible future project, not on the trunk.

## Architecture

### Role partition after P40

| Concern | Owner | Enforcement |
|---|---|---|
| Schema correctness (types, required, `extra="forbid"`) | `UserConfigFile` for on-disk files; `DoxaConfig` for runtime defaults | `UserConfigFile.model_validate()` in `config validate` + tests |
| "Which fields ship to users on `init`" | `StarterField(...)` marker in schema | Walked by drift test |
| Default *values* for shipped fields | `starter.config.toml` (on-disk) | Drift test pins each value against an instantiated `DoxaConfig()` default at the same path |
| Comment prose users see | Inline in `starter.config.toml` | Reviewer eyeball; no test |
| Validation pipeline | `doxa config validate` reads TOML → `UserConfigFile.model_validate` → optional drift check if PATH resolves to shipped template | Same code path as the drift test |
| Pre-commit guard on the template | `lefthook.yml` entry globbed to the template path | Blocks commits on validation failure |

### Key architectural choices

- **Single template file** at `src/doxa_research/data/starter.config.toml`.
- **`StarterField` marker is now a contract**, not a generator input. The drift test reads it; nothing assembles bytes from it.
- **`doxa config validate` is the bridge.** End users (`doxa config validate ~/.config/doxa/doxa.config.toml`) and CI (`lefthook` invoking the same command on the shipped template) traverse the same code. The drift check is conditional on PATH resolving to the shipped template path; for any other PATH it's schema validation only.
- **Drift expected values come from instantiated defaults.** The walker uses `StarterField` metadata to discover paths, but reads expected values from `DoxaConfig().model_dump(mode="python", exclude_none=True)`. This preserves parent default factories such as `[providers.openai].api_key = "${OPENAI_API_KEY}"`.
- **Path-equality gate** uses `target_path.resolve() == (importlib.resources.files("doxa_research.data") / "starter.config.toml").resolve()`. Handles relative paths, symlinks, editable vs wheel installs.
- **`StarterField(default_factory=...)` is env-derived; the field is computed
  at runtime by Pydantic per-user and is NOT shipped in the on-disk template.
  Only `StarterField(literal_value)` fields appear in the template. This
  prevents baking the build machine's environment into every wheel install.**

## Components

### New files

| Path | Purpose |
|---|---|
| `src/doxa_research/data/__init__.py` | Empty file; makes `data` an importable subpackage. |
| `src/doxa_research/data/starter.config.toml` | On-disk source of truth. Every `StarterField` value with inline comments, plus the new `[clarification.cli]` / `[clarification.interactive]` blocks. |
| `src/doxa_research/cli_subcommands/_config_validate.py` | Pure validation function `validate_config_file(path: Path, *, drift_check: bool) -> ValidationResult`. Schema-validates with `UserConfigFile`; when `drift_check=True`, compares starter paths from `DoxaConfig` against instantiated defaults. |
| `tests/test_starter_template_matches_schema.py` | Drift test (TS01) bidirectional + profile parse test (TS02) + structural-superset parity test (TS03). |
| `tests/test_config_validate.py` | Behavioral tests for the new CLI command (TS04a–f). |
| `tests/test_lefthook_starter_hook.py` | Structural test for the lefthook hook (TS05). |
| `tests/fixtures/starter.pre-p40.toml` | Captured pre-P40 generator output; referenced by TS03 for structural-superset assertion. |

### Modified files

| Path | Change |
|---|---|
| `src/doxa_research/config_schema.py` | `ClarificationCLIConfig` (7 fields) and `ClarificationInteractiveConfig` (9 fields): every `Field(...)` becomes `StarterField(...)`. No other schema changes. |
| `src/doxa_research/commands.py` | Replace `_build_starter_document()` body with a thin reader. Delete `WRITER_COMMENTS`, `_emit_starter_section`, `_build_starter_profiles`. Function signature unchanged. |
| `src/doxa_research/cli_subcommands/config.py` | Add `@config.command(name="validate")` following the existing `config_get` / `config_set` pattern. Standard `--json` flag, dispatched through `_emit_doxa_error_for_output_mode`. |
| `lefthook.yml` | Add `validate-starter-template` entry under `pre-commit`, globbed to `src/doxa_research/data/starter.config.toml`. |
| `pyproject.toml` | Build backend is `uv_build` (per `[build-system]`). Adding `src/doxa_research/data/__init__.py` makes `data` a proper subpackage, which `uv_build` includes by default along with its non-Python siblings. If `unzip -l dist/*.whl | grep starter.config.toml` returns empty after a `just build`, add an explicit include rule under `[tool.uv.build-backend]` (e.g., `source-include = ["src/doxa_research/data/*.toml"]`). |
| `docs/COMMANDS.md` | Add `validate` row to config-subcommands table. |
| `docs/json-output.md` | Add a `config validate [PATH] --json` schema sketch and error codes. |
| `tests/test_docs_command_reference.py` | Add `validate` to expected config-subcommands set. |
| `tests/test_json_envelopes.py` | Add success and failure rows for `config validate --json` so the repo-wide JSON envelope meta-test remains complete. |
| `tests/test_config_starter_round_trip.py` | Remove the direct `STARTER_PROFILES` import; replace it with template/profile parsing or fold the assertion into TS02/TS03. |
| `tests/test_init_ships_profiles.py` | If any assertion depends on the Python `STARTER_PROFILES` import path, switch to parsing the template; otherwise leave alone. |

### Deleted files

| Path | Why |
|---|---|
| `src/doxa_research/_starter_data.py` | `STARTER_PROFILES` moves inline into the template's `[profiles.*]` blocks. Remove all imports from source and tests before deleting it. |

### No-touch

- `doxa init`'s CLI surface — unchanged.
- Wizard mutations (`general.default_mode`, `providers.<name>.api_key`) — unchanged; the wizard still operates on a parsed `TOMLDocument`.
- `_PartialClarificationConfig` (line 372 of `config_schema.py`) — derived via `make_partial(ClarificationConfig)`, so it picks up the `StarterField` change automatically.
- Runtime config validation, profile catalog, user-tier config location — all unchanged.

## Data Flow

### Flow A — `doxa init` (unchanged user surface)

```
doxa init [--force|--non-interactive|--user|--hidden]
  │
  ├─► commands.py:_build_starter_document()
  │     ├─► importlib.resources.files("doxa_research.data") / "starter.config.toml"
  │     ├─► path.read_text(encoding="utf-8")
  │     └─► tomlkit.parse(text)  →  TOMLDocument
  │
  ├─► [interactive] wizard mutates TOMLDocument
  │     • general.default_mode   ← user choice
  │     • providers.<name>.api_key  ← "${ENV}" placeholder per chosen provider
  │
  └─► target.write_text(tomlkit.dumps(doc))
```

Only the first sub-step differs from pre-P40. Every existing caller of `_build_starter_document()` keeps working without edits.

### Flow B — `doxa config validate [PATH]` (new)

```
doxa config validate [PATH] [--json]
  │
  ├─► resolve target_path:
  │     • PATH given            →  Path(PATH).resolve()
  │     • PATH omitted          →  ~/.config/doxa/doxa.config.toml
  │
  ├─► is_shipped_template = (target_path == resolve(importlib.resources.files(...)/"starter.config.toml"))
  │
  └─► _config_validate.validate_config_file(target_path, drift_check=is_shipped_template)
        │
        ├─► text = target_path.read_text()
        ├─► doc = tomllib.loads(text)                  # parse phase
        │     └─► on TOMLDecodeError → ValidationResult(ok=False, error="toml_parse_error", path=…)
        │
        ├─► UserConfigFile.model_validate(doc)         # schema phase for on-disk files
        │     └─► on ValidationError → ValidationResult(ok=False, error="schema_validation", path=err.errors()[0]["loc"])
        │
        ├─► if drift_check:                            # parity phase (shipped template only)
        │     expected_doc = DoxaConfig().model_dump(mode="python", exclude_none=True)
        │     for field in walk_starter_fields(DoxaConfig):
        │         expected = lookup_toml_path(expected_doc, field.toml_path)
        │         actual   = lookup_toml_path(doc, field.toml_path)
        │         if actual is MISSING:
        │             return ValidationResult(ok=False, error="drift_missing_key", path=field.toml_path, expected=expected)
        │         if actual != expected:
        │             return ValidationResult(ok=False, error="drift_value_mismatch", path=field.toml_path, expected=expected, actual=actual)
        │
        └─► return ValidationResult(ok=True)
              │
              ├─► CLI human: stdout "OK: <path> (schema [+ drift])"; exit 0
              └─► CLI on !ok: stderr formatted message; exit 1
```

### Flow C — Drift test (TS01)

```python
def test_starter_template_matches_schema():
    path = importlib.resources.files("doxa_research.data") / "starter.config.toml"
    result = validate_config_file(Path(path), drift_check=True)   # reuses Flow B
    assert result.ok, f"{result.path}: {result.error}"
```

The test is ~5 lines because all logic lives in `_config_validate`. Same function, called from a test instead of from Click. *This is the one-implementation-two-callers property that guarantees CLI behavior and test behavior cannot diverge.*

### Flow D — lefthook pre-commit hook

```
git commit (staging includes src/doxa_research/data/starter.config.toml)
  │
  ├─► lefthook pre-commit
  │     └─► validate-starter-template entry
  │           glob: src/doxa_research/data/starter.config.toml
  │           run:  uv run doxa config validate src/doxa_research/data/starter.config.toml
  │
  └─► on exit 1: lefthook blocks the commit, surfacing stderr from validate
```

Thin CLI invocation — no Python imports, no module wiring. If the validate command works, the hook works.

## Error Handling

### Failure modes

| Failure | When | Exit | Stderr (no `--json`) | JSON envelope shape |
|---|---|---|---|---|
| Template missing from package | `importlib.resources` raises `FileNotFoundError` (broken wheel) | 1 | `package data missing: doxa_research/data/starter.config.toml` | `{"status":"error","error":{"code":"PACKAGE_DATA_MISSING","message":...,"details":{"path":...}}}` |
| PATH does not exist | User typo, deleted file | 1 | `no such file: <path>` | `{"status":"error","error":{"code":"FILE_NOT_FOUND","message":...,"details":{"path":...}}}` |
| TOML parse error | Syntax error | 1 | `TOML parse error at line N: <msg>` — surface `tomllib` message verbatim | `{"status":"error","error":{"code":"TOML_PARSE_ERROR","message":...,"details":{"path":"<file>:<line>"}}}` |
| Schema validation error | `UserConfigFile.model_validate` raises `ValidationError` | 1 | `<dotted.toml.path>: <pydantic_msg>` — first error in the brief; full list in `--json` | `{"status":"error","error":{"code":"SCHEMA_VALIDATION","message":...,"details":{"errors":[...]}}}` |
| Drift: missing `StarterField` key | Template missing a path the schema marks `in_starter=True` | 1 | `starter template missing required key: <path> (expected default: <repr>)` | `{"status":"error","error":{"code":"DRIFT_MISSING_KEY","message":...,"details":{"path":...,"expected":...}}}` |
| Drift: value mismatch | Template has the key but value != instantiated schema default | 1 | `starter template value mismatch at <path>: expected <repr>, got <repr>` | `{"status":"error","error":{"code":"DRIFT_VALUE_MISMATCH","message":...,"details":{"path":...,"expected":...,"actual":...}}}` |

### Success

| Case | Exit | Stdout (human) | Stdout (`--json`) |
|---|---|---|---|
| Validation + drift check both passed | 0 | `OK: <path> (schema + drift)` | `{"status":"ok","data":{"path":...,"checks":["schema","drift"]}}` |
| Validation passed, drift check skipped | 0 | `OK: <path> (schema)` | `{"status":"ok","data":{"path":...,"checks":["schema"]}}` |

### Behavior rules

- **Fail-fast on parse errors.** If TOML doesn't parse, do not attempt `model_validate`.
- **Fail-fast within schema phase.** Report the first `ValidationError`'s first error; full list lives under the standard JSON error envelope's `error.details.errors`.
- **Drift phase fails one finding at a time** (even in `--json`). Fix one, rerun, find the next.
- **No partial success.** If schema passes but drift fails, overall result is failure.
- **Errors → stderr; JSON envelope → stdout.** `--json` always uses `json_output.py`'s shared `{"status":"ok","data":...}` / `{"status":"error","error":...}` envelope. The internal `ValidationResult` shape is not printed directly.
- **Validate is read-only.** No tempfiles, no caching, no writes. Safe for lefthook on partially-staged trees.

### Deliberate non-features

- **No multi-error aggregation across phases.** A parse error reshapes everything downstream; reporting downstream is noise.
- **No soft warnings.** Validate is boolean.
- **No recovery suggestions** beyond what Pydantic emits for `extra="forbid"` typos.
- **No auto-fix.**

## Testing

### Test list

| ID | File | Asserts |
|---|---|---|
| TS01 | `tests/test_starter_template_matches_schema.py` | Bidirectional drift. Schema → template: every `StarterField` in `DoxaConfig` exists at the expected TOML path with the expected default value read from an instantiated `DoxaConfig()` at that path. Template → on-disk schema: `UserConfigFile.model_validate(tomllib.loads(template_text))` succeeds. |
| TS02 | (same file) | Each of the six shipped profiles (`daily`, `quick`, `openai_deep`, `all_deep`, `interactive`, `deep_research`), parsed from the template's `[profiles.*]` blocks, validates against `ProfileConfig`. |
| TS03 | (same file) | Structural-superset parity. Parse `tests/fixtures/starter.pre-p40.toml` and the new template; every top-level table/key in the fixture exists in the new template with the same value, and the only new top-level table is `[clarification]`. |
| TS04a | `tests/test_config_validate.py` | Valid shipped template → exit 0, stdout `OK: <path> (schema + drift)`. |
| TS04b | (same file) | Pure function drift mismatch: call `validate_config_file(tempfile_copy, drift_check=True)` on a mutated copy → `ok=False`, result names the offending path. The CLI copy path is covered by TS04e and intentionally skips drift. |
| TS04c | (same file) | Pure function drift missing key: call `validate_config_file(tempfile_copy, drift_check=True)` on a copy missing a `StarterField` path → `ok=False`, result names the missing path. The CLI copy path is covered by TS04e and intentionally skips drift. |
| TS04d | (same file) | `--json` envelope shape on success and failure paths: verify the shared outer `status`/`data` or `status`/`error` envelope, with validate-specific fields under `data` or `error.details`. |
| TS04e | (same file) | Non-template path: `doxa config validate <user-config-tempfile>` skips drift check, returns `OK: <path> (schema)`. |
| TS04f | (same file) | No-PATH form: with `HOME=<tempdir>` containing a synthetic `~/.config/doxa/doxa.config.toml`, succeeds. With no such file, exits 1 with `file_not_found`. |
| TS05 | `tests/test_lefthook_starter_hook.py` | Structural hook test. Parse `lefthook.yml`, assert a `validate-starter-template` pre-commit entry is globbed to `src/doxa_research/data/starter.config.toml` and runs `uv run doxa config validate src/doxa_research/data/starter.config.toml`. CLI behavior itself is covered by TS04a/TS04d. |
| (existing) | `tests/test_config_starter_round_trip.py` | Remove the `STARTER_PROFILES` import before deleting `_starter_data.py`; replace with template/profile parsing or fold into TS02/TS03. |
| (existing) | `tests/test_init_ships_profiles.py` | Update only if it imports or indirectly assumes `STARTER_PROFILES`; current profile behavior assertions should keep validating initialized config output. |
| (existing) | `tests/test_docs_command_reference.py` | Add `validate` to expected config-subcommands set. |

All tests run in the default `pytest` invocation (no `extended` or `live_api` marker). All are hermetic — no API keys, no network.

### Wheel & editable verification (acceptance gate, not pytest)

- `just build` → `unzip -l dist/*.whl | grep starter.config.toml` returns one row.
- `uv pip install -e .` in a clean venv → `doxa init` to a tempdir → `diff` against expected output (excluding wizard-mutated keys). Confirms `importlib.resources` resolves under editable install.
- `pip install dist/*.whl` in a clean venv → same smoke test. Confirms wheel-install path.

### TDD commit sequence

Each row is one commit pair (test commit + code commit) on the `feat/p40-on-disk-starter-template` branch:

1. **Capture fixture** — commit `tests/fixtures/starter.pre-p40.toml` (output of current `_build_starter_document()` before any code changes).
2. **TS01 + TS02 fail** → add `starter.config.toml`, `data/__init__.py`, replace `_build_starter_document()` body with thin reader, add `StarterField` markers to `ClarificationConfig` fields → TS01 + TS02 pass.
3. **TS03 fails** → no code change needed if step 2 was clean; confirms structural-superset shape.
4. **Delete `_starter_data.py`, `WRITER_COMMENTS`, `_emit_starter_section`, `_build_starter_profiles`** → all tests still pass.
5. **TS04a–f fail** → add `_config_validate.py` + `@config.command("validate")` wiring + JSON envelope rows in `tests/test_json_envelopes.py` + `docs/COMMANDS.md` row + `config validate` schema/error-codes section in `docs/json-output.md` → TS04 passes.
6. **TS05 fails** → add `lefthook.yml` entry → TS05 passes. Keep TS05 structural; do not build a temp repo that cannot run `uv run doxa`.
7. **Full gate** (`just check`, `pytest -q`, `./doxa_test -r`, `ruff format --check`) → green → push and open PR.

6–7 logical commits, each independently revertable.

## Acceptance Criteria

Revised from the P40 proposal to reflect the `[clarification]` addition and the bidirectional drift test.

- `cat src/doxa_research/data/starter.config.toml` is a complete, valid TOML config file a user could drop into `~/.config/doxa/` and have Doxa load cleanly.
- `doxa init` produces an output equal to pre-P40 output **plus** the new `[clarification]` section (structural-superset parity). All non-`[clarification]` bytes are unchanged, modulo wizard-mutated fields.
- `doxa config validate src/doxa_research/data/starter.config.toml` exits 0 on a clean template (`OK: <path> (schema + drift)`).
- `doxa config validate src/doxa_research/data/starter.config.toml` exits 1 with a precise error path when any `StarterField` default in the schema differs from the template's value at the same TOML path.
- `doxa config validate ~/.config/doxa/doxa.config.toml` (no PATH form) validates the user-tier config against `UserConfigFile` and reports any schema violation.
- Pre-commit hook `validate-starter-template` runs when the template is staged and blocks the commit on validation failure.
- `_starter_data.py`, `WRITER_COMMENTS`, `_emit_starter_section`, `_build_starter_profiles` are removed from the source tree.
- `just check` + `pytest -q` + `./doxa_test -r` + `ruff format --check src/ tests/` all pass.
- Built wheel contains the template: `unzip -l dist/*.whl | grep starter.config.toml` returns one row.

## Risk Surface

- **Wheel packaging.** If the template isn't correctly declared as package data, `importlib.resources.files("doxa_research.data")` raises at runtime. Mitigated by `src/doxa_research/data/__init__.py` (making `data` a proper subpackage) + acceptance-gate `unzip` check.
- **Editable installs.** `importlib.resources.files()` works for editable installs (`uv pip install -e .`) but the path resolution differs slightly from wheel installs. Both paths are exercised in the acceptance gate.
- **Comment fidelity.** P33's `WRITER_COMMENTS` is a list-of-strings schema attached by section name. Template inline comments must preserve the same prose verbatim where possible. The drift test enforces *value* parity, not *comment* parity. Reviewers should eyeball template comments for unintentional prose drift.
- **Backward compat.** None broken externally. The starter file format and contents from a user's perspective gain a `[clarification]` section (visible additive change). Internal API consumers of `_starter_data.STARTER_PROFILES` would break — remove the known test import in `tests/test_config_starter_round_trip.py` and re-run `git grep STARTER_PROFILES` before deleting the module.
- **Drift-test scope.** Bidirectional test catches both schema-side and template-side mistakes (typos, stray keys, `extra="forbid"` violations), closing the gap in P40's original proposal which was schema → template only.

## Estimated Impact

- **LOC delta:** roughly −250 (remove generator + `_starter_data.py` + `WRITER_COMMENTS`) and +220 (template file with `[clarification]`, drift test, new `doxa config validate` subcommand + `_config_validate` module, lefthook entry, hook structural test). Net simplification ~30 lines.
- **Cognitive surface:** starter content moves from 3 Python sources to 1 text file + 1 schema marker. Onboarding cost drops noticeably.
- **New user-visible surface:** `doxa config validate` is a useful addition for users debugging their own configs.
- **Pre-commit guarantee:** contributors editing the template can't ship a desynchronized version.
- **No CLI behavior change** beyond the additive `[clarification]` section appearing in newly-initialized configs.

## Open Items (deferred to implementation plan)

These are minor refinements that don't block the design. The implementation plan can finalize them:

- Whether `tests/fixtures/starter.pre-p40.toml` stays in the tree long-term or is removed once TS01's bidirectional drift test is in place (TS03 becomes redundant once we're past P40 merge — the bidirectional test catches the same divergence modes).
- Whether TS05 should remain a structural YAML test long-term or be hand-verified once and trusted thereafter. A temp-repo smoke test is intentionally avoided because `uv run doxa` requires an importable project environment.
- Whether `pyproject.toml` needs an explicit `[tool.uv.build-backend]` `source-include` entry or whether `data/__init__.py` alone suffices to bundle `starter.config.toml` into the wheel. Verify after the first `just build`.
