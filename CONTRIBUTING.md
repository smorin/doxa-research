# Contributing to Doxa Research

Welcome — and thanks for your interest in contributing! This document
covers setup, the dev loop, and how to land a PR. For the high-level
project intro, see the [README](README.md).

## Setup

```bash
# Clone and enter the project
git clone https://github.com/smorinlabs/doxa-research.git
cd doxa-research

# Check bootstrap environment (uv, python3, just)
make env-check

# Install git hooks (see "If hooks stop firing" below)
lefthook install

# Install the package in editable mode (creates the doxa command)
uv sync
```

## Bootstrap with `make`

`make` is bootstrap-only in this repo. Run `make env-check` first on a new
machine or shell to verify the local environment before using `just`:

```bash
make env-check   # Verify uv, python3, and just are installed
make check-uv    # Verify uv is installed
make help        # Show bootstrap commands
```

## Daily workflow with `just`

For all development, quality, test, build, and release workflows, use
`just`:

```bash
just --list              # Show all available tasks
just check               # Run code-quality checks for src/doxa_research/
just lint                # Lint src/doxa_research/
just typecheck           # Type-check src/doxa_research/
just fix                 # Auto-fix and format src/doxa_research/
just test-lint           # Lint doxa_test
just test-typecheck      # Type-check doxa_test
just test-fix            # Auto-fix and format doxa_test
just check-all           # Check src/doxa_research/ and doxa_test
just fix-all             # Fix and format src/doxa_research/ and doxa_test
just test                # Run ./doxa_test -r
just test-skip-interactive  # Run tests skipping interactive coverage
just test-vcr            # Run cassette-backed pytest coverage
just update-snapshots    # Regenerate pytest snapshot files
just clean               # Remove local build and cache artifacts
just install             # Sync dependencies with uv
just build               # Build distribution packages
just publish-test        # Publish to TestPyPI
just publish             # Publish to PyPI
```

## Running tests

```bash
# Quick manual smoke check of the CLI itself (not the regression suite)
./doxa "test prompt" --provider mock
```

Use `doxa_test` for the actual regression suite. It mixes
provider-agnostic CLI tests, mock-provider runs, interactive `pexpect`
coverage, and provider-specific tests that only run when the needed API
keys are present.

| Command | What it runs | When to use it |
|------|---------|---------|
| `just test` | Full `doxa_test` suite (`./doxa_test -r`) | Local full validation before merging |
| `./doxa_test -r` | All available tests for the current environment | Default comprehensive test run |
| `just test-skip-interactive` | Mock + provider-agnostic tests, skipping interactive `pexpect` cases | Fast CI-safe pass or non-TTY environments |
| `./doxa_test -r --interactive` | Interactive-only `pexpect` tests (`INT-*`) | Debugging terminal UI and interactive mode |
| `./doxa_test -r --provider mock` | Provider-agnostic tests plus mock-provider coverage | Fastest broad regression run with no real API keys |
| `./doxa_test -r --provider openai` | Provider-agnostic tests plus OpenAI-specific cases | Validating OpenAI integration with a real key |
| `./doxa_test -r --provider gemini` | Provider-agnostic tests plus Gemini-specific smoke cases | Validating Gemini runner wiring with a real key |
| `./doxa_test -r --all-providers` | Every provider test the suite knows about | Full provider matrix validation |
| `just test-extended` | Real-API provider contract tests (`pytest -m "extended and not extended_slow"`) | Nightly job; manual when investigating provider-API changes |
| `just test-extended-openai` / `-perplexity` / `-gemini` | Provider-scoped extended tests | Debugging one provider without running the full live contract matrix |
| `just test-live-api` | Real-API CLI workflow regression suite (`pytest -m "live_api and not extended_slow"`) | Weekly job (Sat 7pm PDT); manual when verifying user-visible streaming/file/secret behavior |
| `just test-live-api-openai` / `-perplexity` / `-gemini` | Provider-scoped live workflow tests | Debugging one provider's live CLI workflows |

`doxa_test -r` behaves like this:

- Always runs provider-agnostic tests.
- Always runs mock-provider tests because the suite auto-generates a mock key.
- Runs interactive tests unless you pass `--skip-interactive`.
- Skips OpenAI, Perplexity, and Gemini tests when their API keys are not set.

Useful commands:

```bash
# Full suite with whatever providers are available in your environment
./doxa_test -r

# Run tests skipping interactive (pexpect) tests — fast, CI-safe
./doxa_test -r --provider mock --skip-interactive
# or equivalently
just test-skip-interactive

# Run interactive tests only
./doxa_test -r --interactive

# Run the broad no-API-key path most contributors use
./doxa_test -r --provider mock

# Run OpenAI provider tests (requires API key)
./doxa_test -r --provider openai -t M8T

# Run all provider tests
./doxa_test -r --all-providers

# Run specific test pattern
./doxa_test -r -t "async" -v

# Save stdout/stderr and metadata for each test under test_outputs/
./doxa_test -r --provider mock --save-output
```

## Real-provider extended tests

The `extended` pytest marker is for live provider calls that mock tests
cannot prove. The default pytest selection excludes these tests, so they
only run when you ask for them explicitly.

Fast extended tests should stay intentional because they spend real API
budget. The current required live scenarios are:

| Scenario ID | What it proves | Cost behavior |
|------|---------|---------|
| `test_model_kind_matches_runtime_behavior[...]` | Every `KNOWN_MODELS` OpenAI, Perplexity, and Gemini model kind matches upstream runtime behavior | Immediate models complete; background models use best-effort cleanup |
| `test_ext_*_mode_*_passthrough` | OpenAI, Perplexity, and Gemini provider request settings reach the real provider-specific request shape | Non-live request-construction guard under the extended marker |
| `EXT-OAI-IMM-STREAM-TEE` | Immediate OpenAI streaming writes the same live text to stdout and an `--out` file | Completes immediately |
| `EXT-OAI-BG-JSON-AUTO-ASYNC` | Background `ask --json` auto-submits asynchronously without explicit `--async` | Cancels in cleanup |
| `EXT-OAI-BG-JSON-EXPLICIT-ASYNC` | Background `ask --async --json` returns the expected submit envelope | Cancels in cleanup |
| `EXT-OAI-BG-CANCEL-CMD` | `doxa cancel <op-id> --json` cancels a live OpenAI background job through the user-facing CLI | Cancels in test |
| `EXT-OAI-BG-ASYNC-BLOCKING-RESUME-COMPLETE` | Full lifecycle: async submit, blocking `resume`, completed checkpoint, and output file metadata | Runs to completion; opt-in with `DOXA_EXTENDED_SLOW=1` |

To run the fast live-provider extended set manually:

```bash
# Export the provider keys you want this run to cover. If openai.env
# contains shell-style assignments:
set -a
source openai.env
set +a

# If openai.env is just the raw OpenAI key instead:
export OPENAI_API_KEY="$(cat openai.env)"

# Also export PERPLEXITY_API_KEY and GEMINI_API_KEY for those provider slices.

uv run pytest -m "extended and not extended_slow" tests/extended -v
```

To run only the slow full-lifecycle tests:

```bash
DOXA_EXTENDED_SLOW=1 uv run pytest \
  -m "extended and extended_slow" \
  tests/extended \
  -v
```

The slow tests intentionally let background jobs finish so they can
validate blocking resume, final checkpoint state, result extraction, and
output-file metadata. Keep them out of routine local validation unless
you are explicitly checking those lifecycles.

## Pre-commit verification

The full verification workflow used in this repo:

```bash
make env-check
just fix
just check
./doxa_test -r
just test-lint
just test-typecheck
just test-fix
just test-lint
just test-typecheck
```

`CLAUDE.md` has a more nuanced "Fast Iteration Loop" guide for inner-loop
development — read it if you're iterating on a single failing test.

## API keys for live tests

Tests use the mock provider by default — no API keys are required for
`./doxa_test -r`.

For live provider tests set:

```bash
export OPENAI_API_KEY="sk-..."
export PERPLEXITY_API_KEY="pplx-..."
export GEMINI_API_KEY="..."
```

## Submitting a PR

1. Create a branch: `git checkout -b feat/your-feature`
2. Make your changes (tests first per TDD practice)
3. Run `just check-all` and `./doxa_test -r` — both must pass
4. Use [Conventional Commits](https://www.conventionalcommits.org/) for
   commit messages (`feat:`, `fix:`, `docs:`, `refactor:`, etc.). The
   `commit-msg` lefthook hook and commitlint CI both enforce this.
5. Push and open a PR against `main`

Releases are automated by release-please — see [RELEASE.md](RELEASE.md).
Don't hand-edit versions in `pyproject.toml`, `CHANGELOG.md`, or
`.release-please-manifest.json`.

## If hooks stop firing (post-rename gotcha)

If your local git appears to bypass all hooks on commit / push — no
ruff, no commitlint, no yamllint, no tests — check whether
`core.hooksPath` is pointing at a path that no longer exists:

```bash
git config --get core.hooksPath
ls -d "$(git config --get core.hooksPath)" 2>&1   # path must exist
```

When lefthook installs hooks, it sets `core.hooksPath` to an absolute
path (e.g. `/Users/you/c/<project>/.git/hooks`). If you ever rename the
directory containing the repo, that absolute path becomes stale; git
silently looks for hooks at the missing path and finds none — every
commit and push bypasses all hooks.

Fix:

```bash
# Option 1: unset the override so git falls back to the default in-tree
# .git/hooks/ (works if lefthook's wrappers are already there)
git config --unset core.hooksPath

# Option 2: reset the hooksPath to match the current repo location
lefthook install --force
```

Verify hooks fire again:

```bash
git commit --allow-empty -m "test: verify hooks"   # should show lefthook output
```

This trap is silent — there's no warning when a stale hooksPath
deactivates everything. After renaming the repo directory, always
run `lefthook install --force` or sanity-check with the steps above.
