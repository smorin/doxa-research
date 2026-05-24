# P40 - On-Disk Starter Template (Reverse P33 Generation)

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)
- **Predecessor:** P33 (`projects/P33-schema-driven-config-defaults.md`) — the
  project this proposal reverses architecturally.
- **Related:** `src/doxa_research/commands.py` (`_build_starter_document`)
- **Related:** `src/doxa_research/_starter_data.py` (the `STARTER_PROFILES` list)
- **Related:** `src/doxa_research/config_schema.py` (`StarterField` marker)

**Status:** `[~]` In progress (PR open; all tasks complete, pending merge).

**Goal**: Restore an on-disk starter config template as the source of truth for
`doxa init` output, replacing the schema-driven generator introduced in P33.
Keep the no-drift property P33 was enforcing by adding (1) a new
`doxa config validate` CLI command that runs Pydantic schema validation
against any TOML file and, when pointed at the starter template, also
enforces `StarterField` value-parity, and (2) a `lefthook` pre-commit hook
scoped to the template path that invokes the new command automatically
whenever the template is staged.

## Motivation

P33 moved the starter `doxa.config.toml` content into three Python sources
(`config_schema.py` field defaults, `WRITER_COMMENTS` dict in `commands.py`,
`STARTER_PROFILES` list in `_starter_data.py`). The starter doc is rebuilt at
runtime by walking those structures. The motivating gain was preventing drift
between the schema's default values and the template's literal values.

In practice this trade reads as net-negative for this project's audience and
maintenance cadence:

| Concern | Schema-driven (current) | On-disk template (proposed) |
|---|---|---|
| Source of truth for default values | Pydantic `StarterField(...)` | Template file + schema, pinned by a drift test |
| Default-value drift risk | None (impossible by construction) | Caught at CI by the drift test |
| "What does `doxa init` write?" | Read three Python modules, mentally execute the generator | `cat src/doxa_research/data/starter.config.toml` |
| Editing a comment | Edit `WRITER_COMMENTS` dict in commands.py, runtime re-render | Edit the comment in the template file |
| Adding/removing a profile | Append to `STARTER_PROFILES` list (Python literals) | Add a `[profiles.<name>]` block in the template |
| Reviewer skill needed for changes | Python + Pydantic + tomlkit | TOML |
| Round-trip parity testing | Indirect (generator output vs. expected dict) | Direct (parse template → validate against schema) |

The schema-driven generator solves a small problem (default-value drift) with
a structural change that splits a single text artifact across three Python
modules. The same drift property is recoverable from a ~30-line drift test
without the structural cost.

Reversal is also low-risk: the consumer surface (`doxa init`'s on-disk
output) is unchanged. Only the *source* of those bytes changes.

## Scope

**In scope:**

- Add `src/doxa_research/data/starter.config.toml` containing the exact bytes
  that `_build_starter_document()` currently emits for a fresh install.
- Add `src/doxa_research/data/__init__.py` (or update `pyproject.toml`
  `[tool.setuptools.package-data]` / equivalent) so the template ships in the
  built wheel and is reachable via `importlib.resources`.
- Replace `_build_starter_document()` in `commands.py` with a thin reader
  that returns a `tomlkit.TOMLDocument` parsed from the template file.
- Delete `src/doxa_research/_starter_data.py` (`STARTER_PROFILES` moves
  into the template's `[profiles.*]` blocks).
- Delete the `WRITER_COMMENTS` dict from `commands.py` (comments move
  inline next to their values in the template).
- Add a drift test `tests/test_starter_template_matches_schema.py`:
  - Parse the template via `tomllib`.
  - Walk every field in `DoxaConfig` (recursively into sub-models) whose
    `json_schema_extra["in_starter"]` is `True`.
  - Assert each such field has the same default value at the same TOML path
    in the template.
  - Assert every profile in the template parses cleanly against
    `ProfileConfig`.
- Update the wizard merge logic (`_apply_wizard_answers`) to operate on the
  parsed template — should be a no-op since the wizard already takes a
  `TOMLDocument` and only touches `[general].default_mode` and
  `[providers.<name>].api_key`.

**New CLI surface (validation tooling):**

- Add `doxa config validate [PATH]` subcommand:
  - With no PATH, validates the resolved user-tier config
    (`~/.config/doxa/doxa.config.toml`).
  - With explicit PATH, validates that TOML file against `DoxaConfig`.
  - When PATH points at the shipped starter template, ALSO runs the
    drift assertion (every `StarterField` default in the schema appears
    with the same value at the same TOML path in the template).
  - Exits 0 on success; exits 1 with a clear error pointing at the
    offending field/path on failure.
  - Supports `--json` for the standard envelope (see
    `docs/json-output.md`).
- Add `doxa config validate` to `docs/COMMANDS.md` config-subcommands
  table and to the `tests/test_docs_command_reference.py` coverage
  guard.

**New pre-commit hook (lefthook):**

- Add a `lefthook.yml` `pre-commit` entry scoped to
  `src/doxa_research/data/starter.config.toml`:
  ```yaml
  validate-starter-template:
    glob: "src/doxa_research/data/starter.config.toml"
    run: uv run doxa config validate src/doxa_research/data/starter.config.toml
  ```
  Triggers only when that exact file is staged. Fast — single TOML
  parse + schema walk + drift check — so it's fine in the always-on
  pre-commit pipeline.
- The hook reuses the same code path the standalone command exposes,
  so there's no risk of CLI behavior and hook behavior diverging.

**Preserved (no change):**

- The `StarterField(...)` marker stays in the schema. It's the contract for
  "this field gets shipped to users on init"; the drift test reads it.
- All runtime config validation (`DoxaConfig.model_validate`) is unchanged.
- The wizard UX and the `[providers.<name>] api_key = "${ENV}"` placeholder
  semantics are unchanged.
- Profile catalog (the six shipped profiles) is unchanged; they're
  represented inline in the template instead of in a Python list.

## Out of scope

- Re-evaluating which profiles ship (that's P37, "Review starter-profile
  selection").
- Re-evaluating which schema fields are `StarterField` vs plain `Field`.
- The `clarification` section being absent from the starter file (current
  intentional behavior; preserve).
- Any change to the user-tier config file location or filename.
- Changes to `doxa init`'s CLI surface (`--force`, `--non-interactive`,
  `--user`, `--hidden`).

## Open questions

1. **Where exactly does the template live in the package?** Recommend
   `src/doxa_research/data/starter.config.toml`. The convention matches the
   `cli_subcommands/` and `completion/` subpackages that ship code; `data/`
   is the standard name for non-Python resources in a wheel.

   Answer: use  `src/doxa_research/data/starter.config.toml`
2. **Should the template include `[clarification]`?** Current behavior:
   excluded from the starter doc, defaults applied at runtime via Pydantic.
   Recommend preserve — don't change observable behavior in this PR.

   Answer: move into config so it's configurable.
3. **One template or split?** Recommend single file for the simpler mental
   model; user sees one artifact. The profile section is the lengthiest
   piece (six profile blocks) but is still readable inline.

   Answer: single file
4. **What about the wizard's runtime customization?** Unchanged — the
   wizard still mutates only two keys (`general.default_mode` and
   `providers.<name>.api_key`). The parsed template is the input.

   Answer: Unchanged

## Tests & Tasks

- [x] [P40-TS01] Write `tests/test_starter_template_matches_schema.py`:
  parse template, walk `StarterField`-marked schema fields, assert
  value-and-path parity between template and schema.
- [x] [P40-TS02] Verify every shipped profile (`daily`, `quick`,
  `openai_deep`, `all_deep`, `interactive`, `deep_research`) parses
  cleanly against `ProfileConfig`.
- [x] [P40-TS03] Bit-for-bit comparison test: parse current generator
  output and the new template, assert structural equivalence
  (ignoring whitespace + comment formatting differences).
- [x] [P40-T01] Add `src/doxa_research/data/starter.config.toml`
  containing the current generator's output. Include inline comments
  from `WRITER_COMMENTS` next to the relevant sections.
- [x] [P40-T02] Add `src/doxa_research/data/__init__.py` (or
  pyproject.toml package-data) so the template is included in the
  built wheel.
- [x] [P40-T03] Replace `_build_starter_document()` with a thin
  reader using `importlib.resources.files("doxa_research.data") /
  "starter.config.toml"`.
- [x] [P40-T04] Delete `src/doxa_research/_starter_data.py` and its
  `STARTER_PROFILES` references in `commands.py`.
- [x] [P40-T05] Delete `WRITER_COMMENTS` from `commands.py` and the
  `_emit_starter_section` / `_build_starter_profiles` helpers (no
  longer needed once the template ships the literal bytes).
- [x] [P40-T06] Confirm `doxa init`, `doxa init --force`, and
  `doxa init --non-interactive` all produce identical bytes
  (modulo wizard-mutated keys) to pre-P40 behavior.
  Verified by doxa_test integration suite (75/75 passed).
- [x] [P40-T07] Update `tests/test_init_ships_profiles.py` if any
  assertion depends on the Python `STARTER_PROFILES` import path
  (replace with template-based assertion or remove if redundant
  with the new drift test).
  No changes needed; existing assertions still hold after _starter_data.py
  removal. pytest 1590 passed, including all init/profile tests.
- [-] [P40-T08] Update `docs/HERO-RECORDING.md` / `CONTRIBUTING.md`
  if either references the schema-driven generation as a feature
  contributors should know about.
  Inspected both files — neither references the schema-driven generation.
  No changes needed; marking decided-not-to-do.
- [x] [P40-T09] Implement `doxa config validate [PATH]` subcommand
  in `src/doxa_research/cli_subcommands/config.py`. With no PATH,
  validate the user-tier config; with PATH, validate that file
  against `DoxaConfig`; when PATH is the shipped starter template,
  also run drift assertions against the schema. Support `--json`.
  Exit 0 on success, 1 on failure with a precise location pointer.
- [x] [P40-T10] Add a `pre-commit` `validate-starter-template` entry
  in `lefthook.yml`, globbed to
  `src/doxa_research/data/starter.config.toml`. The entry invokes
  `uv run doxa config validate <that path>`. Hook also runs from CI
  via the existing lefthook-on-CI path (no separate workflow needed).
- [x] [P40-T11] Surface the new command in `docs/COMMANDS.md` config
  subcommands table and add coverage in
  `tests/test_docs_command_reference.py`.
- [x] [P40-TS04] Tests for `doxa config validate`:
  - Valid template → exit 0.
  - Template with a value mutated (e.g. swap `default_mode = "default"`
    for `default_mode = "bogus"`) → exit 1 with the failing path.
  - Template missing a `StarterField`-marked key → exit 1 with the
    missing path.
  - JSON envelope shape on both success and failure paths.
- [x] [P40-TS05] Smoke-test the pre-commit hook: stage a corrupted
  copy of the template, attempt `git commit`, assert the hook
  rejects the commit and surfaces the validate error.

## Acceptance Criteria

- `cat src/doxa_research/data/starter.config.toml` is a complete, valid
  TOML config file a user could drop into `~/.config/doxa/` and have
  Doxa load cleanly.
- `doxa init` produces the same on-disk file (bit-for-bit, except for
  wizard-mutated fields) as it did before P40.
- `doxa config validate src/doxa_research/data/starter.config.toml`
  exits 0 on a clean template.
- The same command exits 1 with a precise error path when any
  `StarterField` default in the schema differs from the template's
  value at the same TOML path.
- `doxa config validate ~/.config/doxa/doxa.config.toml` (no PATH
  form) validates the user-tier config against `DoxaConfig` and
  reports any schema violation.
- Pre-commit hook `validate-starter-template` runs (via `lefthook
  run pre-commit`) when the template is staged and blocks the commit
  on validation failure.
- `_starter_data.py` and `WRITER_COMMENTS` are removed from the source
  tree.
- `just check-all` and `./doxa_test -r` pass green.
- Wheel built via `just build` contains the template at the expected
  path (verify with `unzip -l dist/*.whl | grep starter.config.toml`).

## Risk surface

- **Wheel packaging**: if the template isn't correctly declared as
  package data, `importlib.resources.files("doxa_research.data")`
  raises at runtime. P40-T02 + a build-artifact verification step
  (acceptance criterion) prevents this.
- **Comment fidelity**: P33's `WRITER_COMMENTS` is a list-of-strings
  schema attached by section name. The template's inline comments
  should preserve the same prose verbatim where possible — easier to
  read but also easier to silently drift from the original intent. The
  drift test only enforces value parity, not comment parity. Reviewers
  should eyeball the template for prose changes.
- **Editable installs**: `importlib.resources` works for editable
  installs (`pip install -e .` and `uv pip install -e .`) but the
  path resolution differs slightly. Test under both layouts before
  merging.
- **Backward compat**: none broken. The starter file format and
  contents are unchanged from a user's perspective. Internal API
  consumers of `_starter_data.STARTER_PROFILES` would break, but
  `git grep` confirms only `commands.py` imports it.

## Estimated impact

- **LOC delta**: roughly −250 (remove generator + `_starter_data.py` +
  `WRITER_COMMENTS`) and +180 (template file, drift test, new
  `doxa config validate` subcommand, lefthook hook entry). Net
  simplification ~70 lines.
- **Cognitive surface**: starter content moves from 3 Python sources
  to 1 text file + 1 schema marker. Onboarding cost for contributors
  drops noticeably.
- **New user-visible surface**: `doxa config validate` is a small but
  useful addition. Without P40 it could ship standalone; pairing the
  two means the drift property is enforced and observable via the same
  command users would reach for to validate their own configs.
- **Pre-commit guarantee**: contributors editing the template can't
  ship a desynchronized version — the lefthook entry blocks commits
  on validation failure, surfacing the precise schema mismatch.
- **No CLI behavior change** if implemented correctly for the existing
  surface. Acceptance criterion #2 (bit-for-bit parity for
  `doxa init`) is the contract.

## Implementation Notes

- During Task 12 review, the code-quality reviewer caught a regression
  introduced by the static template: the build machine's literal
  `checkpoint_dir` (an `XDG_STATE_HOME`-derived path) was being shipped
  in the wheel and written into every user's `doxa init` output. Fixed
  by teaching `StarterField` to skip fields with `default_factory=...`
  — those are env-derived and computed at runtime by Pydantic per-user.
  Commit `b23858e`.
