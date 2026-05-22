# Changelog

All notable changes to Doxa Research are documented here.

## [3.0.13](https://github.com/smorin/doxa-research/compare/v3.0.12...v3.0.13) (2026-05-22)


### Bug Fixes

* **ci:** remove trailing whitespace in P40 starter template doc ([d2f4c0d](https://github.com/smorin/doxa-research/commit/d2f4c0de4e2a20fc5a47e5a0a59f3c2918dd464d))

## [3.0.12](https://github.com/smorin/doxa-research/compare/v3.0.11...v3.0.12) (2026-05-22)


### Documentation

* **projects:** propose P40 — on-disk starter template (reverse P33) ([#81](https://github.com/smorin/doxa-research/issues/81)) ([edd23eb](https://github.com/smorin/doxa-research/commit/edd23ebd8d4cfafec4449e595c55f22c36fd20ba))

## [3.0.11](https://github.com/smorin/doxa-research/compare/v3.0.10...v3.0.11) (2026-05-18)


### Documentation

* **claude-md:** add 4 sub-CLAUDE.md files capturing conventions ([#78](https://github.com/smorin/doxa-research/issues/78)) ([b14b2a1](https://github.com/smorin/doxa-research/commit/b14b2a179fee15e0ca2d813f0a4af43d53d6fdc1))

## [3.0.10](https://github.com/smorin/doxa-research/compare/v3.0.9...v3.0.10) (2026-05-17)


### Documentation

* **claude:** compress CLAUDE.md from 529 to 256 lines without losing info ([#75](https://github.com/smorin/doxa-research/issues/75)) ([9c56468](https://github.com/smorin/doxa-research/commit/9c5646816f5f5d484f7552866c85d16e2353fdf9))

## [3.0.9](https://github.com/smorin/doxa-research/compare/v3.0.8...v3.0.9) (2026-05-17)


### CI/CD

* harden all 7 workflows with explicit permissions + concurrency ([#74](https://github.com/smorin/doxa-research/issues/74)) ([14b4d1d](https://github.com/smorin/doxa-research/commit/14b4d1d34553bb8cf1a8411b47ec191656733907))

## [3.0.8](https://github.com/smorin/doxa-research/compare/v3.0.7...v3.0.8) (2026-05-16)


### CI/CD

* **release-please:** auto-sync uv.lock after release tag ([5164488](https://github.com/smorin/doxa-research/commit/51644885f1a003293b10d2f5d79d18cd1c4a0aef))

## [3.0.7](https://github.com/smorin/doxa-research/compare/v3.0.6...v3.0.7) (2026-05-16)


### Bug Fixes

* **deps:** bump ty dev dependency to &gt;=0.0.33 (PR [#42](https://github.com/smorin/doxa-research/issues/42)) ([fccc245](https://github.com/smorin/doxa-research/commit/fccc245fe09e07003502016ac007201339d44d50))


### Documentation

* **claude:** add release coordination + drift prevention rules ([b46d86d](https://github.com/smorin/doxa-research/commit/b46d86d9b33d1d1ce9190bb078b2bff0d537c678))
* **release:** document publish-manual emergency-only + hooksPath gotcha ([2ad8e22](https://github.com/smorin/doxa-research/commit/2ad8e22ab0991d3701ec8e6ebbb75c99d86f6cf3))

## [3.0.6](https://github.com/smorin/doxa-research/compare/v3.0.3...v3.0.6) (2026-05-16)

Consolidated release of all work between v3.0.3 and 2026-05-16. Supersedes
the unpublished v3.0.4 and v3.0.5 tags (see notes below for context).

### CI/CD

* **publish:** verify tag is reachable from origin/main before release; defense
  in depth against an attacker-tagged feature-branch commit triggering a
  release ([2139ee4](https://github.com/smorin/doxa-research/commit/2139ee47efccf7d722f1ba6900c85c80bd1d4bf2))
* **release-please:** upgrade `actions/create-github-app-token` v1 → v3 for
  Node.js 24 support; v1 was deprecated and would be force-migrated on
  2026-06-02 ([ca64dfd](https://github.com/smorin/doxa-research/commit/ca64dfdab4d05735c7ca3f254346700071b14cc3))
* **release-please:** customize PR title to clarify publish action; titles now
  read `chore(release): publish vX.Y.Z — review and merge to ship to PyPI`
  ([8768d48](https://github.com/smorin/doxa-research/commit/8768d486de2ce21a95c50e2f093f3ef57f1c5f4e))
* **release-please:** stop chore commits from triggering version bumps; sets
  `"hidden": true` on chore in `changelog-sections`, preventing recursive
  release PR loops from chore-only commits
  ([0600676](https://github.com/smorin/doxa-research/commit/0600676ce3a3e0f60f127b6cee3f25ff85e4daa1))

### Bug Fixes

* **ci:** wrap long `publish.yml` line as a YAML folded scalar to satisfy
  yamllint `line-length: max: 120`; the failure had been preventing CI
  Hygiene from passing on every commit since the `--check-url` flag was
  added ([4336f09](https://github.com/smorin/doxa-research/commit/4336f0907a85e6fee37ada008b46a35c0bdb6862))

### Testing

* **sigint:** replace `SimpleNamespace` stubs with real `ConfigManager` /
  `CheckpointManager` instances; resolves 8 long-standing `ty` type errors
  without any `# type: ignore` comments
  ([651d037](https://github.com/smorin/doxa-research/commit/651d037861efc1bdd1800cfd487b71d5000c0ef2))

### Notes

The intermediate tags v3.0.4 and v3.0.5 were created by release-please's
cascading-chore mechanism but never published to PyPI (the publish workflow's
required-reviewer gate was rejected for both). The tags + GitHub Releases
existed transiently; this 3.0.6 release contains the same code as v3.0.5 plus
the chore-hidden config that prevents the cascade from repeating.

There is no v3.0.4 or v3.0.5 on PyPI. Users upgrading from v3.0.3 go directly
to v3.0.6.

## ~~[3.0.5]~~ (never published)

Tagged on 2026-05-16; rejected at the PyPI approval gate. Same code as
v3.0.6 minus the chore-hidden config commit. Tag and GitHub Release have
been removed; this entry is preserved for history. The substantive changes
under this tag are listed under v3.0.6 above.

## ~~[3.0.4]~~ (never published)

Tagged on 2026-05-16; rejected at the PyPI approval gate. Tag and GitHub
Release have been removed; this entry is preserved for history. The
substantive changes under this tag are listed under v3.0.6 above.

## [3.0.3](https://github.com/smorin/doxa-research/compare/v3.0.2...v3.0.3) (2026-05-16)


### Documentation

* **release:** add RELEASE-PLEASE-APP.md canonical App setup guide ([abb0742](https://github.com/smorin/doxa-research/commit/abb0742ed1a370dfb8381ac0f2166a91dd7028d4))

## [3.0.2](https://github.com/smorin/doxa-research/compare/v3.0.1...v3.0.2) (2026-05-16)


### Miscellaneous

* retrigger release-please after credentials fix ([f2fca18](https://github.com/smorin/doxa-research/commit/f2fca1865e24931d04f52c92c56e98a7820313c9))
* trigger release-please after App credentials setup ([4ea31a9](https://github.com/smorin/doxa-research/commit/4ea31a90c68ddc6ef57348213b158fecb33410a4))

## [3.0.1] — 2026-05-16

### Changed

- Re-release of 3.0.0 under a new version number. TestPyPI's permanent
  file-name-reuse policy blocked re-upload of `doxa_research-3.0.0-*`
  files after the original laptop-built artifacts were deleted (they had
  a different hash than the CI-built artifacts; deleting was the
  recovery, but PyPI/TestPyPI never allow reusing a filename even after
  deletion). 3.0.1 is the first publicly installable release of the
  doxa-research rebrand. No functional changes from the unpublished
  3.0.0 tag.

## [3.0.0] — 2026-05-15

### Renamed (BREAKING)

This release renames the project from `thoth` to `doxa-research`. Every public-facing identifier changes — there is **no automatic migration** for existing users.

| Surface | Old | New |
|---|---|---|
| PyPI distribution | `thoth` | `doxa-research` |
| Install command | `pip install thoth` | `pip install doxa-research` |
| Python import | `import thoth` | `import doxa_research` |
| CLI command | `thoth …` | `doxa …` (also `doxa-research …`) |
| Module entry point | `python -m thoth` | `python -m doxa_research` |
| Environment variables | `THOTH_*` (13 vars) | `DOXA_*` |
| Click completion env | `_THOTH_COMPLETE` | `_DOXA_COMPLETE` |
| User config dir | `~/.config/thoth/` | `~/.config/doxa/` |
| User state dir | `~/.local/state/thoth/` | `~/.local/state/doxa/` |
| User cache dir | `~/.cache/thoth/` | `~/.cache/doxa/` |
| Config file name | `thoth.config.toml` | `doxa.config.toml` |
| GitHub repo | `smorin/thoth` | `smorin/doxa-research` |
| Internal classes | `ThothError`, `ThothGroup`, `ThothConfig`, `ThothCommand`, `ThothOrchestrator` | `DoxaError`, `DoxaGroup`, `DoxaConfig`, `DoxaCommand`, `DoxaOrchestrator` |

**Migration for existing users** (one-time):

```bash
# 1. Install the new package
pip uninstall thoth
pip install doxa-research

# 2. Copy your config + state + cache (no auto-migration)
mkdir -p ~/.config/doxa ~/.cache/doxa ~/.local/state/doxa
cp -r ~/.config/thoth/. ~/.config/doxa/ 2>/dev/null || true
cp -r ~/.cache/thoth/. ~/.cache/doxa/ 2>/dev/null || true
cp -r ~/.local/state/thoth/. ~/.local/state/doxa/ 2>/dev/null || true
mv ~/.config/doxa/thoth.config.toml ~/.config/doxa/doxa.config.toml 2>/dev/null || true

# 3. Update shell init scripts: THOTH_* → DOXA_*, _THOTH_COMPLETE → _DOXA_COMPLETE
# 4. Old thoth 2.5.0 remains on PyPI (frozen, will not receive updates)
```

The `thothspinner` dependency is unrelated to this rename and keeps its name.

### Removed (BREAKING)

- The `--resume` / `-R` global flag is removed. Use `doxa-research resume OP_ID` instead.
- The `doxa-research providers -- --list` / `--models` / `--keys` / `--check` / `--refresh-cache` / `--no-cache` legacy `--`-separator forms are removed. Use `doxa-research providers list|models|check` instead.
- The `doxa-research providers --list` / `--models` / `--keys` / `--check` in-group flag forms (PR1.5 hidden subcommands) are removed. Same migration as above.
- The `doxa-research modes --json` / `--show-secrets` / `--full` / `--name X` / `--source X` flag-style forms are removed. Use `doxa-research modes list <flag>` instead.
- The `doxa-research --help <topic>` parse-time hijack is removed. Use `doxa-research help <topic>` (or `doxa-research <topic> --help` for real subcommands).
- The `auth` virtual help topic on `doxa-research help auth` is removed.
- `completion` was removed from the help renderer's command listing (it was a phantom — never registered as a real subcommand).

### Added

- `doxa-research ask "PROMPT"` — canonical scripted research entry point. Accepts the full research-options stack (per Q3-PR2-C, applied identically to the cli group).
- `doxa-research resume OP_ID` — canonical resume entry point. Honors `--verbose`, `--config`, `--quiet`, `--no-metadata`, `--timeout`, `--api-key-{openai,perplexity,mock}` per Q1-PR2-C.
- `doxa-research completion {bash,zsh,fish}` — emit eval-able shell init scripts. Supports `--install` (TTY-detect + prompt-before-overwrite), `--install --force` (CI-friendly silent overwrite), `--install --manual` (print block + instructions; never write), and `--json` (structured success/error envelopes for install metadata or shell-validation errors). Closes PRD F-70.
- TAB completion of operation IDs (`resume`, `status`), mode names (`modes list --name`), config keys (`config get`), and provider names (`providers list/models/check --provider`).
- `--json` flag on every data/action admin command: `init`, `status`, `list`, `providers list/models/check`, `config get/set/unset/list/path/edit`, `modes list`, `ask`, `resume`. Envelope contract documented in `docs/json-output.md`.
- `ask --json` immediate-mode returns full result inline; background-mode auto-asyncs and returns an op-id submit envelope.
- `resume --json` is a pure snapshot — never advances state, never polls. Use without `--json` to retry.

### Changed (BREAKING)

- `doxa-research config get KEY --raw` no longer bypasses secret masking. To reveal a secret value, use `--show-secrets` (with or without `--raw`). `--raw` now controls only output formatting. `--raw` is supported only on `doxa-research config get`; `doxa-research config list --raw` exits 2 with a clear message (use `doxa-research config list --json` for machine-readable list output).
- `doxa-research status` (no OP_ID) now exits 2 instead of 1 (matches Click's default for a missing required argument).
- `doxa-research providers` (no leaf) now exits 2 (was 0) — Click default for required-subcommand groups.
- `doxa-research modes` (no leaf) now exits 2 (was 0). Use `doxa-research modes list` for the previous default behavior.
- `doxa-research providers models --refresh-cache --no-cache` is now mutually exclusive (was a silent ambiguity that fell through to the provider implementation).
- `doxa-research modes list --name X --source Y` now intersects both filters (was: silently dropped `--source`).
- `doxa-research --clarify` (without `--interactive`) now exits 2 with `--clarify requires --interactive` (was: silent no-op).
- `doxa-research config get KEY --layer L` now validates `L` against the actual layer set (`defaults|user|project|env|cli`) and exits 2 on invalid values (was: silently returned wrong-layer data).

### Migration from v2.x

| Old form | New form |
|---|---|
| `doxa-research --resume OP_ID` | `doxa-research resume OP_ID` |
| `doxa-research providers -- --list` | `doxa-research providers list` |
| `doxa-research providers -- --models` | `doxa-research providers models` |
| `doxa-research providers -- --models --provider openai` | `doxa-research providers models --provider openai` |
| `doxa-research providers -- --models --refresh-cache` | `doxa-research providers models --refresh-cache` |
| `doxa-research providers -- --keys` (or `--check`) | `doxa-research providers check` |
| `doxa-research providers --list` (in-group shim) | `doxa-research providers list` |
| `doxa-research modes --json` | `doxa-research modes list --json` |
| `doxa-research modes --name deep_research` | `doxa-research modes list --name deep_research` |
| `doxa-research --help auth` | (no replacement — `auth` topic dropped) |
| `doxa-research config get KEY --raw` (revealing secrets) | `doxa-research config get KEY --show-secrets` |

## [Unreleased]

### Fixed
- **BUG-01**: Sync deep-research mode no longer renders two `rich.Live` displays simultaneously. `_execute_research` now picks the polling-progress bar XOR the `thothspinner` Live via the new `_poll_display` helper.
- **BUG-02**: `--pick-model` is rejected (with a helpful message) when combined with `--resume`, `--interactive`, a subcommand, or no prompt — previously the picker fired and the user's selection was silently discarded.
- **BUG-03**: `--prompt-file` now stat-checks file size before reading and rejects non-UTF-8 input. Cap is configurable via `[execution].prompt_max_bytes` (default: `1048576` = 1 MiB).
- **BUG-06**: Interactive picker walks the merged config (`config.data["modes"]`) so user-defined modes appear in `--pick-model`. Removed the OpenAI-only hardcoded `{o3, gpt-4o-mini, gpt-4o}` extras for provider symmetry.

### Changed
- `run_with_spinner` accepts a `console` kwarg so the spinner shares the caller's `rich.Console` (preventing cross-Console Live conflicts).
- ThothSpinner construction in `progress.py` sets `spinner_style="npm_dots"`, `message_shimmer=True`, `timer_format="auto"`, `hint_text="Ctrl-C to background"`, and hides the (zero-progress) progress component for deep-research UX.

### Added
- `doxa-research providers list`, `doxa-research providers models`, `doxa-research providers check` — explicit subcommands replace `doxa-research providers -- --list`.
- `doxa-research help auth` — in-CLI authentication guidance.
- `doxa-research cancel OP_ID` — cancels an in-flight background operation where the provider supports upstream cancellation and marks the local checkpoint cancelled.
- `--pick-model` / `-M` flag for interactively selecting a model on immediate (non-background) modes.
- Progress spinner during sync background-mode runs (via `thothspinner`).
- Config file path surfaced in `APIKeyError` messages.
- "Resume later: doxa-research resume OP_ID" hint on Ctrl-C.

### Changed
- `--help` now shows the workflow chain (clarification → … → tdd) and worked examples for `--auto`, `--async`/`--resume`, and `-v` debugging.
- `--input-file` / `--auto` help rewritten for clarity.
- `--api-key-openai` / `--api-key-perplexity` / `--api-key-mock` help now says "(not recommended; prefer env vars)".
- README Authentication section documents env-vars → config-file → CLI-flags in that order.

### Deprecated
- `doxa-research providers -- --list` — still works for one release; use `doxa-research providers list`.

## [2.6.0] — In Development

### Added
- Clarification mode in interactive session (Shift+Tab toggle)
- `--clarify` flag for starting in Clarification Mode
- Virtual environment management in Makefile (`make venv`, `make venv-install`, `make venv-sync`, `make venv-clean`)
- UV export for dependency extraction

## [2.5.0]

### Added
- Operation lifecycle state machine with full checkpoint recovery
- Interactive mode with Clarification Mode support
- Enhanced signal handling for graceful shutdown with checkpoint save

## [2.2.0]

### Added
- Provider discovery (`doxa-research providers -- --list`, `--models`, `--keys`)
- Provider-specific API key flags (`--api-key-openai`, `--api-key-perplexity`, `--api-key-mock`)
- Enhanced metadata headers in output files (model, operation_id, created_at)

## [2.1.0]

### Added
- `providers` command for listing available providers
- Dynamic model listing from provider APIs

## [2.0.0]

### Added
- Mode chaining (clarification → exploration → deep_research with `--auto`)
- Checkpoint/resume for async operations (`doxa-research --resume <operation-id>`)
- Operation management (`doxa-research list`, `doxa-research status <id>`)
- Project-based output organization (`--project`)
- Async submit-and-exit mode (`--async`)

## [1.5.0]

### Added
- Core research functionality with multiple modes: `default`, `deep_research`, `clarification`, `exploration`, `thinking`
- OpenAI and Perplexity provider support
- Mock provider for testing
- Rich terminal UI with progress indicators
- Interactive prompt mode with slash commands and tab completion
- Combined report generation (`--combined`)
- Config file support (`~/.doxa-research/config.toml`)
