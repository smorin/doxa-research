# P41 - `--no-validate` Redesign (Make the Flag Mean What It Says)

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)
- **Related:** P40 (`projects/P40-on-disk-starter-template.md`) — sibling
  project that introduces `doxa config validate` as a standalone
  subcommand; this project addresses the global flag.
- **Related:** `src/doxa_research/cli_subcommands/_options.py` (the
  `--no-validate` flag definition)
- **Related:** `src/doxa_research/cli.py` (lines 99–111 wire the flag
  into the global module state)
- **Related:** `src/doxa_research/config_schema.py` (line 25 the
  `_no_validate` global, line 570 the consumer)

**Status:** `[ ]` Scoped, not started.

**Goal**: Make `--no-validate` mean what its name says — actually bypass
Pydantic schema validation — instead of its current behavior of merely
suppressing deprecation warnings. Surface as a global option recognized
on every subcommand. Print a one-line stderr warning whenever it's used
so the user-takes-responsibility contract is explicit.

## Motivation

The current flag has a name/behavior mismatch:

- Help text reads: `"Suppress config schema validation warnings (debug/CI use only)"`
- Actual behavior: sets `_no_validate = True`, which only short-circuits
  one specific block in `config_schema.py:570` — the deprecation-warning
  emitters. Pydantic's `model_validate()` calls in `load_all_layers`
  still run and still raise on schema violations.

This produces a confusing user model:

- A user expecting "skip validation entirely" passes `--no-validate`, hits
  a Pydantic error on a malformed config, and concludes the flag is
  broken.
- A user passing `--no-validate` for the deprecation-warning suppression
  it actually provides has to read the help carefully to discover that's
  what it does.

The fix is to honor the name. `--no-validate` should bypass Pydantic
schema validation on every config layer — exactly the emergency escape
hatch users reach for with this kind of flag in `kubectl --validate=false`
or `git commit --no-verify` style commands.

## Scope

**Behavior change:**

- `--no-validate` becomes a true bypass of `DoxaConfig.model_validate()`
  on every config layer in `ConfigManager.load_all_layers`. Schema
  violations no longer raise; they're recorded but don't halt the
  process.
- Per-mode `kind` deprecation warnings (the current narrow effect) also
  remain suppressed under `--no-validate` (preserves the existing
  warning-suppression behavior as a side effect).
- On any invocation with `--no-validate` set, doxa emits exactly one
  stderr line before any other output:
  ```
  warning: --no-validate set; config schema checks bypassed. Crashes
  downstream are user-accepted.
  ```
- The flag is recognized at the top-level Click group (`cli.py`),
  not per-subcommand, so it works uniformly across every
  `doxa <command>` invocation.

**Help text update:**

```
--no-validate    Bypass config schema validation entirely. Use only
                 when you've manually verified your config works and
                 need to run despite a schema mismatch (e.g. forward-
                 compat with a newer doxa version). Emits a one-line
                 warning to stderr on use.
```

**Module state cleanup:**

- The current `_no_validate` global lives in `config_schema.py`. Move
  it to a more explicit location (e.g. `cli.py` or a small
  `runtime_flags.py` module) so the schema layer reads a single
  predicate `should_skip_validation()` rather than direct module-global
  access. Avoids the import-side-effect pattern.

## Out of scope

- The `doxa config validate` standalone command — that's P40-T09.
- A `--config-strict` / `--config-quiet` strictness dial. The earlier
  design exploration considered three flags total (`--config-strict`,
  `--config-quiet`, `--config-unsafe`) for finer-grained control.
  Deferred — the demand signal for those isn't here yet, and adding
  them now would crowd the CLI surface for one well-understood emergency
  case. They can ship in a follow-up project (call it P42) if a real
  use case surfaces.
- Restructuring the `_validate_*` warning system in
  `ConfigManager._validate_config`. The current per-mode kind warning
  works; this project doesn't touch its rendering.
- Any change to per-command behavior. `--no-validate` works the same
  on every subcommand; no command-specific carve-outs.

## Open questions

1. **Behavior change risk: who relies on the current behavior?**
   No tests cover `--no-validate`'s warning-suppression behavior;
   no docs mention it as the canonical way to silence warnings; no
   community discussion references it. Risk of behavior-change
   surprise is low but nonzero. Recommendation: ship in the next
   minor (v3.X.0) with an explicit changelog entry under "Behavior
   change" — not a deprecation cycle, because the current behavior
   is broken-by-design.
2. **Where does the stderr warning render?**
   Recommend `rich.console.Console(stderr=True).print(...)` to keep
   it consistent with other stderr-routed messages in the codebase.
   The warning should NOT be subject to the existing config-warning
   suppression (since suppressing the "validation skipped" notice
   would defeat the safety contract).
3. **Should we cover `--no-validate` in `--json` envelope output?**
   Yes — when `--json` is set, the warning should appear as a
   `warnings` array entry in the envelope rather than free-form
   stderr. Avoid breaking the JSON contract for script consumers.
4. **What does `doxa config validate` (P40-T09) do when called with
   `--no-validate`?** The combination is nonsensical (you can't ask
   to validate and bypass validation at the same time). CLI should
   reject the combination at preflight with a clear error. This is a
   cross-project concern; coordinate with P40.

## Tests & Tasks

- [ ] [P41-TS01] Test that `--no-validate` allows a config with a
  schema violation (e.g. `format = "json"` after standardization
  #7 restricted it to `markdown`) to load without raising. Assert
  the stderr warning appears once.
- [ ] [P41-TS02] Test that `--no-validate` still suppresses the
  per-mode kind deprecation warning (regression-check of current
  behavior).
- [ ] [P41-TS03] Test that `--no-validate` with `--json` causes the
  bypass-warning to appear in the JSON envelope's `warnings` array,
  not on stderr.
- [ ] [P41-TS04] Test that `--no-validate` is recognized on every
  subcommand (parametrize over `ask`, `init`, `config get`, `modes
  list`, etc.). Assert the warning appears for each.
- [ ] [P41-TS05] Cross-project: test that `doxa config validate
  --no-validate <path>` raises a preflight error (the combination
  is nonsensical). Wire after P40-T09 lands.
- [ ] [P41-T01] Rename the `_no_validate` predicate to a function
  in a new `src/doxa_research/runtime_flags.py` (or fold into an
  existing app-context module). Single accessor:
  `should_skip_config_validation() -> bool`.
- [ ] [P41-T02] Modify `ConfigManager.load_all_layers` to skip
  `DoxaConfig.model_validate(...)` calls when
  `should_skip_config_validation()` returns True. Preserve the
  raw-dict layer merge — Doxa still loads the config; it just
  doesn't enforce schema.
- [ ] [P41-T03] Add the one-line stderr warning. Single point of
  emission inside `cli.py`'s top-level group, gated on the
  `--no-validate` flag value. Skipped when `--quiet` is set
  (matches the existing convention that `--quiet` silences
  doxa's own informational output).
- [ ] [P41-T04] Update the `--no-validate` help text in
  `_options.py` to describe the new behavior precisely.
- [ ] [P41-T05] CHANGELOG.md entry under "Behavior change":
  call out that `--no-validate` now actually bypasses schema
  validation. Link the deprecation rationale to this project doc.
- [ ] [P41-T06] Update `docs/COMMANDS.md` if it mentions
  `--no-validate` (search for references; surface in the global-
  options section).
- [ ] [P41-T07] Update the JSON envelope rendering in
  `json_output.py` to include the bypass-warning in the
  `warnings` array when `--no-validate` is active.

## Acceptance Criteria

- `doxa ask "..." --no-validate` with a config that has a real
  schema violation (e.g. a bogus `output.format` value) does NOT
  raise during config loading. The run proceeds. The stderr warning
  appears once.
- `doxa ask "..."` (without `--no-validate`) on the same config
  still raises with the precise Pydantic error.
- `doxa ask "..." --no-validate --quiet` suppresses the bypass
  warning (per the `--quiet` convention).
- `doxa ask "..." --no-validate --json` includes the bypass warning
  in the JSON envelope's `warnings` array, not on stderr.
- `doxa config validate <path> --no-validate` (post-P40) rejects
  the combination at preflight with a clear error message.
- `_no_validate` module global is gone; replaced by a function
  accessor in a clearly-named runtime-flags module.
- `just check-all` and `./doxa_test -r` pass green.

## Risk surface

- **Behavior change**. The current `--no-validate` silently
  suppresses deprecation warnings; the new behavior also bypasses
  Pydantic. Any user passing `--no-validate` today to silence
  noise will, post-P41, also be bypassing schema validation.
  Mitigation: the new behavior is a strict superset of the old
  (warnings are still suppressed; the difference is that schema
  errors no longer raise). The only break is for users who pass
  `--no-validate` AND rely on Pydantic to catch their config
  mistakes — a self-contradictory expectation. CHANGELOG entry +
  acceptance criterion #2 (default behavior unchanged) cover the
  rollout.
- **Downstream crashes**. If a user with `--no-validate` set has
  a config that's actually invalid (wrong types, missing required
  fields), Doxa proceeds and may crash at a less-obvious point
  later. The stderr warning is the safety contract: "you accepted
  responsibility for this." Aligns with `kubectl --validate=false`
  and `git commit --no-verify`.
- **JSON envelope contract**. The `--json` rendering needs a
  `warnings` array; check the existing envelope schema in
  `docs/json-output.md` to confirm there's a place for one (or
  add one cleanly). Coordinate with the json-output contract.
- **Per-command parsing**. The current flag is wired through
  Click's group `--no-validate` option. Verify it's recognized
  the same way on every subcommand — particularly the dynamically
  generated `doxa modes <op>` leaves and the `doxa config
  profiles` subgroup — and add the parametrized test to lock that
  contract.

## Estimated impact

- **LOC delta**: roughly +80 (warning emission path, JSON envelope
  integration, runtime_flags module, expanded help) and −20 (the
  current `_no_validate` global and its single direct-access
  consumer). Net ~+60 lines.
- **User-visible change**: one stderr line on `--no-validate` use;
  a meaningful behavior change for the (rare) users who pass it
  today. Self-correcting — if they were expecting the old
  warning-suppression-only behavior, the new behavior is a
  superset.
- **Cleanup benefit**: removes a name/behavior mismatch from the
  CLI surface. Reduces "wait, what does this flag actually do?"
  confusion at minimal implementation cost.
