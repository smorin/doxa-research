# P41 - `--no-validate` Redesign (Visible Safety Contract + Strict-Mode CLI Surface)

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)
- **Related:** P40 (`projects/P40-on-disk-starter-template.md`) — sibling
  project that introduces `doxa config validate` as a standalone
  subcommand; this project addresses the global flag.
- **Related:** `src/doxa_research/cli_subcommands/_options.py` (the
  `--no-validate` flag definition)
- **Related:** `src/doxa_research/cli.py` (lines 99–111 wire the flag
  into the module-level `_doxa_config_schema._no_validate`)
- **Related:** `src/doxa_research/config_schema.py` (`ConfigSchema.validate()`
  at line 564 — short-circuited by `_no_validate`)
- **Related:** `tests/test_config_validate.py` — existing coverage
  (`test_no_validate_global_suppresses_warnings`,
  `test_no_validate_flag_suppresses_runtime_warnings`,
  `test_strict_mode_raises_on_unknown_field`)

**Status:** `[ ]` Scoped, not started.

**Goal**: Two coordinated improvements to Doxa's validation surface:

1. Add a visible safety-contract warning so users always know when
   `--no-validate` is in effect (today the flag silently disables all
   schema-validation feedback with no acknowledgement).
2. Expose the existing `strict=True` validation mode that lives in
   `ConfigSchema.validate(...)` as a new global CLI flag so CI
   gates and pre-deploy audits can require schema-clean configs.

No change to default validation semantics; no change to what
`--no-validate` suppresses; the existing tests stay green.

## Motivation

Original proposal mis-characterized the current behavior. Updated
description after reading `ConfigSchema.validate()` directly:

**Today's three validation states** (all already exist in source):

| State | Trigger | Behavior |
|---|---|---|
| Default (non-strict) | no flag | Pydantic errors caught, converted to `ValidationWarning`s, emitted via the report. Never raises. |
| Bypassed | `--no-validate` | `ConfigSchema.validate()` returns an empty `ValidationReport`. All schema warnings (not just deprecation) suppressed. |
| Strict | `strict=True` keyword in code | Pydantic raises on schema violations. Currently only reachable from internal code paths — no CLI flag exposes it. |

The flag-name "`--no-validate`" reads as "skip validation entirely."
In the warn-only paradigm it does effectively that — the user sees
no validation feedback. So the flag does what its name implies, but
two real gaps remain:

1. **No safety acknowledgement.** A user who passes `--no-validate`
   (perhaps reflexively, copying a script) gets no signal that
   schema checking has been disabled. There's no equivalent of
   `git commit --no-verify`'s "warning: --no-verify in effect"
   line. A misconfigured config silently runs as if it were clean.
2. **No way to opt into strict.** The codebase has a `strict=True`
   keyword on `ConfigSchema.validate()` that makes Pydantic raise.
   Useful for CI gates ("fail the pre-deploy check if any schema
   violation exists"), pre-merge audits, and tooling that wants
   hard guarantees rather than warn-only feedback. No CLI flag
   exposes it today.

## Scope

**Safety-contract warning (default behavior addition):**

- When `--no-validate` is set on any invocation, doxa emits exactly
  one line to stderr **before** any other output:
  ```
  warning: --no-validate set — config schema checks suppressed.
  ```
  Uses `rich.console.Console(stderr=True)` (per existing
  config-warning rendering convention).
- Suppressed under `--quiet` (matches the existing convention that
  `--quiet` silences doxa's own informational output).
- Under `--json`, the warning is **omitted from stderr** and does
  NOT modify the existing envelope contract — see Open Question 3
  for the rationale.
- Suppression precedence (highest first): `--json` > `--quiet` >
  default (stderr emission).

**New `--strict` global flag:**

- Add `--strict` (or `--strict-config` if naming collides) at the
  top-level Click group in `cli.py`, alongside `--no-validate`.
- When set, every `ConfigSchema.validate(...)` call propagates
  `strict=True` to Pydantic, which then raises on any schema
  violation instead of converting to a warning.
- Mutually exclusive with `--no-validate` — passing both at once
  is rejected at CLI preflight with a clear error pointing the
  user at one or the other.
- Help text for `--strict` (working draft):
  ```
  --strict    Treat config schema warnings as errors. Pydantic raises
              on any schema violation in any config layer. Use in CI
              gates and pre-deploy audits. Mutually exclusive with
              --no-validate.
  ```

**Help-text update for `--no-validate`:**

Current help says
`"Suppress config schema validation warnings (debug/CI use only)"`.
Update to reflect that it covers ALL schema feedback (not just
warnings) and that it now emits a safety acknowledgement:

```
--no-validate    Suppress all config schema validation feedback for this
                 invocation. Useful for forward-compat with newer config
                 schemas or to skip checks during debugging. Emits a
                 one-line acknowledgement to stderr unless --quiet or
                 --json is set. Mutually exclusive with --strict.
```

## Out of scope

- The `doxa config validate` standalone command — that's P40-T09.
  It will use `strict=True` internally so it always raises on
  violations; this is a different access path from the global
  flag.
- Adding finer-grained validation controls beyond `--strict` and
  `--no-validate` (e.g. a per-layer toggle, a category-filter for
  which warning classes to surface). Deferred — no demand signal.
- Restructuring the `_validate_*` warning system in
  `ConfigManager._validate_config`. The current per-mode kind
  warning works; this project doesn't touch its rendering.
- Modifying the `--json` envelope contract (see Open Question 3).
- Behavior change to the default (non-strict) path — the existing
  warn-only validation stays warn-only.

## Open questions

1. **Should the safety warning emit under `--json`?**
   Decision: NO — `--json` users opted into a strict envelope
   contract (`{status, data|error}` per `docs/json-output.md`).
   Sticking a free-form stderr line in front of JSON output
   breaks tooling that reads stderr separately and would force a
   contract change to surface the warning in-envelope. Users who
   need the safety signal under `--json` should not pass
   `--no-validate` in scripted contexts. Suppression precedence
   is `--json` > `--quiet` > default.

2. **What rendering channel for the safety warning?**
   Decision: `rich.console.Console(stderr=True).print(...)` —
   matches the existing `_console` in `config.py:42`.

3. **Should the `--json` envelope grow a `warnings` array?**
   Decision: NO. The current envelope is strictly `{status,
   data|error}` per `docs/json-output.md:11,15`. Adding a
   top-level `warnings` slot would be a versioned schema change
   affecting every script that parses doxa's JSON output. Out
   of scope for P41. If a per-command warnings surface is
   wanted in the future, embedding them inside the `data`
   payload (per-command shape) is the lighter-weight path.

4. **Cross-project interaction with `doxa config validate`
   (P40-T09).**
   Decision: The combination is nonsensical. CLI preflight in
   `doxa config validate` rejects `--no-validate`. Likewise,
   `--strict` is redundant with `doxa config validate` (which
   already uses strict mode) but harmless; allow it without
   error. Cross-coordination flagged for P40-T09's
   implementation.

5. **Mutually exclusive `--no-validate` + `--strict`.**
   Decision: Hard error at preflight. Message:
   `Error: --no-validate and --strict are mutually exclusive. Pass one or neither.`

## Tests & Tasks

- [ ] [P41-TS01] Test that `--no-validate` emits the one-line
  stderr warning exactly once on a fresh invocation, and not at all
  when `--no-validate` is absent. Cover via the existing
  `test_config_validate.py` harness; use the
  `test_no_validate_flag_suppresses_runtime_warnings` pattern.
- [ ] [P41-TS02] Test that `--no-validate --quiet` suppresses the
  safety warning.
- [ ] [P41-TS03] Test that `--no-validate --json` suppresses the
  safety warning AND that the JSON envelope remains
  `{status, data}` (no new top-level keys).
- [ ] [P41-TS04] Test that the safety warning appears uniformly
  across subcommands. Parametrize over `ask`, `config list`,
  `modes list`, `providers list`, and at least one config-profiles
  subcommand. Use the Click group-level invocation form (`doxa
  --no-validate <subcommand> ...`), per the Click ordering
  convention.
- [ ] [P41-TS05] Test that `--strict` causes Pydantic to raise on
  a config with a schema violation that's currently a warning.
  E.g. typo'd field name like `general.prompy_prefix`.
- [ ] [P41-TS06] Test that `--strict` alone (no schema violation)
  is a no-op: a clean config runs the same as without the flag.
- [ ] [P41-TS07] Test that `--no-validate --strict` is rejected
  at preflight with a clear mutually-exclusive error.
- [ ] [P41-TS08] Cross-project (after P40-T09 lands): test that
  `doxa config validate <path>` is unaffected by `--no-validate`
  (it always uses `strict=True` internally; the flag should be
  rejected by `config validate`'s own preflight).
- [ ] [P41-T01] Add the safety-warning emission in `cli.py`'s
  top-level group, gated on `--no-validate` and suppressed under
  `--quiet` or `--json`. Single emission point.
- [ ] [P41-T02] Add the `--strict` flag to `_options.py` at the
  same scope as `--no-validate`. Mutex check at preflight.
- [ ] [P41-T03] Thread `strict` from the CLI through
  `ConfigManager.load_all_layers` to
  `ConfigSchema.validate(strict=...)`. Currently `strict` is
  hard-coded `False` in the call site.
- [ ] [P41-T04] Update help text for `--no-validate` to match
  the new behavior (drop "deprecation warnings" wording, mention
  the safety acknowledgement, mention mutex with `--strict`).
- [ ] [P41-T05] Update `docs/COMMANDS.md` global-options section
  to surface both flags with their actual behavior.
- [ ] [P41-T06] CHANGELOG.md entry: new `--strict` flag (under
  Features); safety warning now emitted on `--no-validate` use
  (under Behavior changes — minor user-visible change). No
  semantic change to what `--no-validate` suppresses.
- [ ] [P41-T07] Module-state cleanup (optional but cheap): move
  the `_no_validate` global out of `config_schema.py` into an
  app-context module so the schema layer reads a predicate
  rather than a module global. Avoids the import-side-effect
  pattern.

## Acceptance Criteria

- `doxa --no-validate ask "..."` emits exactly one stderr line
  starting with `warning: --no-validate set` before any other
  output. Run again without the flag — no such line.
- `doxa --no-validate --quiet ask "..."` produces no stderr
  safety line.
- `doxa --no-validate --json ask "..."` produces no stderr
  safety line, and the JSON envelope still parses as
  `{status, data}` with no new keys.
- `doxa --strict ask "..."` with a config that has a typo
  (`general.prompy_prefix = "x"`) raises a Pydantic
  `ValidationError` and exits non-zero. Without `--strict` the
  same config runs (warning emitted, exit 0).
- `doxa --no-validate --strict ask "..."` exits non-zero with
  `Error: --no-validate and --strict are mutually exclusive`.
- Existing tests in `tests/test_config_validate.py` continue to
  pass without modification (no regression to the suppression
  semantics).
- New tests P41-TS01..TS08 pass.
- `just check-all` and `./doxa_test -r` pass.

## Risk surface

- **Backwards compatibility of `--no-validate`**. No semantic
  change to what the flag suppresses. The only observable change
  is the new stderr warning line. Scripts that pipe stderr into
  comparison may see one extra line; scripts that use `--json`
  or `--quiet` see no change. Acceptable for a minor release.
- **`--strict` raising on configs that worked before**.
  `--strict` is opt-in; nothing that runs without the flag changes.
  Users adopting `--strict` will need to clean up real schema
  drift in their configs — that's the feature.
- **Click ordering**. Existing tests like `test_no_validate_flag_
  suppresses_runtime_warnings` already use the `doxa --no-validate
  ... config list` ordering (global options before subcommand);
  the same applies to `--strict`. The parametrized TS04 test
  pins this.
- **Mutex collision**. Hard error at preflight is the standard
  pattern in this codebase (see `ImmediateMultiProviderError`,
  `CombinedNeedsMultiProviderError`). Same style applies here.

## Estimated impact

- **LOC delta**: roughly +120 (new `--strict` flag, mutex check,
  safety warning emission, threading `strict` through validate
  calls, tests) and ~−10 (the deprecation-warning-specific code
  paths can shed some comments now that the surface is honestly
  documented). Net ~+110 lines.
- **User-visible changes**: (1) one stderr line on
  `--no-validate` use, suppressed under `--quiet` / `--json`;
  (2) a new opt-in `--strict` global flag for CI/audit use.
- **Cleanup benefit**: gives Doxa a complete validation-control
  surface (off / warn / strict) that matches what users would
  reach for. Removes the "what does `--no-validate` actually do?"
  ambiguity from the help docs.
