# Release Guide

Doxa Research releases are automated by **release-please** (version bumps + changelog + tag + GitHub Release) and **publish.yml** (TestPyPI → PyPI via OIDC trusted publishing). Humans author conventional commits; everything downstream is automatic.

## Table of Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Versioning](#versioning)
- [Release Checklist](#release-checklist)
- [Step-by-Step Release Process](#step-by-step-release-process)
- [CI/CD Pipeline](#cicd-pipeline)
- [OIDC Trusted Publishing Setup](#oidc-trusted-publishing-setup)
- [Local Build & Publish](#local-build--publish)
- [Troubleshooting](#troubleshooting)

---

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                        Release Pipeline                         │
│                                                                 │
│  conventional commit on main                                    │
│       │                                                         │
│       ▼                                                         │
│  release-please.yml                                             │
│       │   opens/updates "Release PR" (bump + CHANGELOG.md)      │
│       │                                                         │
│  merge Release PR                                               │
│       │                                                         │
│       ├── release-please creates tag  v X.Y.Z                   │
│       └── release-please creates GitHub Release                 │
│                │                                                │
│                ▼                                                │
│  publish.yml (triggered by tag push)                            │
│       ├── build:  uv build  →  dist/*.whl + dist/*.tar.gz       │
│       ├── publish-testpypi: uv publish --trusted-publishing ... │
│       └── publish-pypi:     uv publish --trusted-publishing ... │
└────────────────────────────────────────────────────────────────┘
```

### Toolchain

| Concern | Tool | Details |
|---------|------|---------|
| Commit-msg lint | `commitlint` (local hook + CI) | Enforces Conventional Commits |
| Version bumping | `release-please` | Inferred from commit types (`feat!` → major, `feat` → minor, `fix` → patch) |
| Changelog | `release-please` | Generates `CHANGELOG.md` from conventional commits |
| Tag + GitHub Release | `release-please` | Created automatically on Release PR merge |
| Build backend | `uv_build` | PEP 517 backend, bundled with uv |
| Package manager | `uv` | Dependency resolution, venv, lock file |
| Build | `uv build` | Produces wheel (`.whl`) and source dist (`.tar.gz`) |
| Publish | `uv publish` | Uploads to PyPI/TestPyPI via OIDC |
| Task runner | `just` | Wraps uv commands for local convenience |
| CI/CD | GitHub Actions | Test, lint, typecheck, commitlint, release-please, publish |
| Auth | OIDC trusted publishing | No stored API tokens — GitHub mints short-lived tokens |

### Key Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Project metadata + version (bumped by release-please) |
| `src/doxa_research/__init__.py` | Package `__version__` (bumped by release-please via `x-release-please-version`) |
| `.release-please-manifest.json` | release-please's authoritative version per package |
| `release-please-config.json` | release-please behavior + changelog sections |
| `commitlint.config.mjs` | Allowed commit types / header length |
| `package.json` + `bun.lock` | Bun dev dependency on `@commitlint/*` |
| `uv.lock` | Locked dependency graph (committed to repo) |
| `.github/workflows/ci.yml` | Tests, lint, typecheck on push/PR |
| `.github/workflows/commitlint.yml` | Validates commit messages on PR |
| `.github/workflows/release-please.yml` | Opens/merges Release PRs |
| `.github/workflows/publish.yml` | Builds + publishes on `v*` tag push |
| `justfile` | Local task automation (`just build`, `just publish`) |
| `Makefile` | Environment dependency checks (`make env-check`) |
| `CHANGELOG.md` | Release notes (maintained by release-please) |

---

## Prerequisites

**Required for contributing:**
- [uv](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- [just](https://github.com/casey/just) — `brew install just`
- [bun](https://bun.sh/) — required for commitlint (`brew install bun`)
- Git

**Bootstrap the full toolchain in one shot:**
```bash
just install-dev   # uv sync + bun install + lefthook install + gitleaks
```

**Verify your environment:**
```bash
make env-check   # checks uv, python3, just, bun
```

**Commit message format:** all commits must follow [Conventional Commits](https://www.conventionalcommits.org/). The local `commit-msg` hook (lefthook) and the `commitlint` CI job both enforce this. Allowed types: `feat`, `fix`, `perf`, `refactor`, `deps`, `docs`, `test`, `ci`, `chore`, `build`, `style`, `revert`. `deps` is reserved for dependabot bumps (auto-generated via `.github/dependabot.yml`'s `commit-message: prefix: deps` block) and routes to the `Dependencies` CHANGELOG section; humans use `chore` for routine maintenance.

---

## Versioning

Doxa Research uses [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`.

Versions are bumped **automatically** by release-please from conventional-commit types since the last release:

| Commit pattern | Bump |
|----------------|------|
| `feat!:` or `BREAKING CHANGE:` footer | `MAJOR` |
| `feat:` | `MINOR` |
| `fix:`, `perf:`, `refactor:`, `deps:`, `chore:`, `docs:`, `ci:`, `test:`, etc. | `PATCH` |

You do **not** edit `pyproject.toml` or `src/doxa_research/__init__.py` version fields directly. release-please updates them in the Release PR.

**Version surfaces (maintained by release-please):**

```toml
# pyproject.toml — package version
[project]
version = "2.5.0"
```

```python
# src/doxa_research/__init__.py — Python __version__
__version__ = "2.5.0"  # x-release-please-version
```

The CLI reads `DOXA_VERSION` from `src/doxa_research/config.py`, which re-exports `__version__` — so there is one source of truth.

Git tags follow `v{version}` (e.g., `v2.5.0`). release-please creates the tag on Release PR merge; the tag push triggers `publish.yml`.

---

## Release Checklist

A maintainer approves/merges a Release PR. Before merging, verify:

- [ ] All CI checks pass on `main` (green CI, green commitlint)
- [ ] The Release PR's diff shows the expected next version
- [ ] The generated `CHANGELOG.md` entry reads correctly (all `feat:`/`fix:`/... commits since the last tag appear in their groups; nothing surprising is missing)

Merging the Release PR triggers the tag + GitHub Release + publish. Nothing else to do locally.

---

## Step-by-Step Release Process

### 1. Land work as conventional commits on main

Normal development, just with disciplined commit messages:

```bash
git commit -m "feat: add perplexity citation parser"
git commit -m "fix: handle empty response from deep-research API"
git push origin main
```

The local `commit-msg` hook rejects malformed messages before they land. CI's `commitlint` job double-checks on every PR.

### 2. Wait for the Release PR to appear / update

`release-please.yml` runs on every push to `main`. It opens (or updates) a single PR titled something like **`chore(main): release 2.6.0`**. Its diff shows:

- `pyproject.toml` version bumped
- `src/doxa_research/__init__.py` `__version__` bumped
- `.release-please-manifest.json` version bumped
- `CHANGELOG.md` — new section for the incoming version, grouped by commit type

### 3. Review and merge the Release PR

Confirm the diff looks right (especially the changelog entry and the bump level). Merge the PR via the GitHub UI using a standard merge or squash — release-please handles the tag either way.

### 4. Automatic tag, GitHub Release, and publish

On merge, release-please:

1. Creates the `vX.Y.Z` tag on the merge commit
2. Creates a GitHub Release with the changelog section as the body

The tag push triggers `publish.yml`:

1. **Build** — `dist/*.whl` and `dist/*.tar.gz`
2. **Publish to TestPyPI** — [test.pypi.org](https://test.pypi.org/project/doxa-research/)
3. **Publish to PyPI** — [pypi.org/project/doxa-research/](https://pypi.org/project/doxa-research/)

Each publish job requires approval if the environment has reviewers configured.

### 5. Verify the release

```bash
uvx doxa-research==2.6.0 --version
# or
pip install doxa-research==2.6.0
doxa --version
```

---

## CI/CD Pipeline

### `ci.yml` — Continuous Integration

Triggered on every push to `main` and every pull request targeting `main`.

```
push/PR to main
    │
    ├── lint (ubuntu-latest)
    │       uv run ruff format --check src/doxa_research/
    │       uv run ruff check src/doxa_research/
    │
    ├── typecheck (ubuntu-latest)
    │       uv run ty check src/doxa_research/
    │
    ├── yamllint (ubuntu-latest)
    │       uvx yamllint -c .yamllint .
    │
    ├── actionlint (ubuntu-latest)
    │       actionlint
    │
    └── test (matrix: macOS + Ubuntu × Python 3.11, 3.12, 3.13)
            chmod +x doxa-research doxa_test
            ./doxa_test -r --provider mock
```

Jobs run in parallel. The `test` matrix runs 6 combinations (2 OS × 3 Python versions). Typecheck is a required check — failures block the pipeline.

### `publish.yml` — Release Publishing

Triggered only on tag pushes matching `v*` (e.g., `v2.5.0`, `v2.6.0`).

```
push tag v*
    │
    └── build (ubuntu-latest)
            astral-sh/setup-uv@v5
            uv build
            upload artifact: dist/
                │
                └── publish-testpypi (environment: testpypi)
                        permissions: id-token: write
                        uv publish --trusted-publishing always
                        --publish-url https://test.pypi.org/legacy/
                            │
                            └── publish-pypi (environment: pypi)
                                    permissions: id-token: write
                                    uv publish --trusted-publishing always
```

Jobs are sequential: `build → publish-testpypi → publish-pypi`. A failure at any stage stops the pipeline.

---

## OIDC Trusted Publishing Setup

Doxa Research uses [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/) via OpenID Connect (OIDC). No API tokens are stored as GitHub secrets — GitHub Actions mints a short-lived OIDC token that PyPI accepts directly.

### How It Works

1. The workflow requests an OIDC token from GitHub (`id-token: write` permission)
2. `uv publish --trusted-publishing always` presents the token to PyPI
3. PyPI validates the token against the registered trusted publisher configuration
4. If valid, the upload is accepted

### Initial Setup (one-time, per maintainer)

After a repository owner transfer, register the new GitHub Actions identity as
a trusted publisher on both PyPI and TestPyPI before the next release.

**On TestPyPI** ([test.pypi.org/manage/account/publishing/](https://test.pypi.org/manage/account/publishing/)):

| Field | Value |
|-------|-------|
| PyPI Project Name | `doxa-research` |
| Owner | `smorinlabs` |
| Repository name | `doxa-research` |
| Workflow filename | `publish.yml` |
| Environment name | `testpypi` |

**On PyPI** ([pypi.org/manage/account/publishing/](https://pypi.org/manage/account/publishing/)):

| Field | Value |
|-------|-------|
| PyPI Project Name | `doxa-research` |
| Owner | `smorinlabs` |
| Repository name | `doxa-research` |
| Workflow filename | `publish.yml` |
| Environment name | `pypi` |

### GitHub Environments

Two GitHub environments must exist in the repository settings ([Settings → Environments](https://github.com/smorinlabs/doxa-research/settings/environments)):

- **`testpypi`** — used by the `publish-testpypi` job
- **`pypi`** — used by the `publish-pypi` job

Optionally add required reviewers to the `pypi` environment for an approval gate before production publishing.

---

## GitHub App Setup for release-please

> **Canonical guide**: see [RELEASE-PLEASE-APP.md](RELEASE-PLEASE-APP.md) for the full, step-by-step setup with field-level guidance, security considerations, key-rotation procedure, multi-repo onboarding, and troubleshooting. The summary below is the quick reference.

`release-please.yml` uses a GitHub App to authenticate tag pushes. This is necessary because tags pushed with the default `GITHUB_TOKEN` do **not** retrigger `push`-triggered workflows — so `publish.yml` would never fire on release. A GitHub App installation token does retrigger them.

This is one-time setup, per repo.

### Step 1: Create the GitHub App

Go to [GitHub → Settings → Developer settings → GitHub Apps → New GitHub App](https://github.com/settings/apps/new) (or create it under the org that owns this repo):

| Field | Value |
|-------|-------|
| App name | `release-please-smorinlabs` |
| Homepage URL | `https://github.com/smorinlabs/doxa-research` |
| Webhook | Deselect **Active** (no webhook needed) |
| Repository permissions → Contents | **Read and write** |
| Repository permissions → Pull requests | **Read and write** |
| Where can this GitHub App be installed? | **Only on this account** |

Click **Create GitHub App**.

### Step 2: Generate a private key

On the App's settings page, scroll to **Private keys** and click **Generate a private key**. A `.pem` file downloads. Keep it safe — you'll paste its contents into a repo secret.

### Step 3: Install the App on the repo

On the App's settings page, click **Install App** → pick the account/org → **Only select repositories** → choose `doxa-research` → **Install**.

### Step 4: Add the Client ID and private key to the repo

Go to [Settings → Secrets and variables → Actions](https://github.com/smorinlabs/doxa-research/settings/secrets/actions):

- **Secret** `RELEASE_PLEASE_CLIENT_ID` — the Client ID shown on the App's settings page.
- **Secret** `RELEASE_PLEASE_PRIVATE_KEY` — the full contents of the `.pem` file, including the `-----BEGIN ... PRIVATE KEY-----` / `-----END ... PRIVATE KEY-----` lines.

The workflow reads `secrets.RELEASE_PLEASE_CLIENT_ID` and
`secrets.RELEASE_PLEASE_PRIVATE_KEY`. Provision both through the `repo-secrets`
workflow so their values come from the `smorinlabs` 1Password references.

### Step 5: Verify

The next push to `main` runs `release-please.yml`. In the workflow run, the **Create App Token** step must succeed; the **release-please** step then uses that token. On Release-PR merge, the tag push triggers `publish.yml` as expected.

### Why not use `GITHUB_TOKEN`?

GitHub deliberately blocks the default `GITHUB_TOKEN` from triggering subsequent workflows on the events `push`, `pull_request`, etc., to prevent infinite-loop scenarios. A GitHub App installation token is treated as a separate actor, so writes made with it **do** trigger downstream workflows. A classic/fine-grained PAT also works but requires managing a long-lived personal token; the App route has no long-lived token (the installation token is short-lived and minted per run) and the App identity is auditable as a separate actor.

---

## Local Build & Publish

These commands are available for testing builds or publishing manually (e.g., from a maintainer's machine with a token).

```bash
# Build wheel + source distribution
just build
# Output: dist/doxa-research-2.6.0-py3-none-any.whl
#         dist/doxa-research-2.6.0.tar.gz

# Publish to TestPyPI (for validation)
UV_PUBLISH_TOKEN=<your-testpypi-token> just publish-test

# Publish to PyPI
UV_PUBLISH_TOKEN=<your-pypi-token> just publish
```

To inspect a built distribution before publishing:

```bash
uvx twine check dist/*
```

---

## Troubleshooting

### Build fails: `uv_build` not found

Ensure uv is up to date. `uv_build` is distributed as part of uv's bundled backend — it does not need to be installed separately.

```bash
uv self update
uv build
```

### Publish fails: `403 Forbidden` on PyPI

The OIDC trusted publisher is not configured, or the environment name / workflow filename does not match exactly what was registered on PyPI. Verify:

1. The workflow file is named `publish.yml` (not `publish.yaml`)
2. The environment in the workflow job matches the environment registered on PyPI (`pypi` / `testpypi`)
3. The repository owner (`smorin`) and name (`doxa-research`) match exactly

### Publish fails: `400 File already exists`

A distribution with this version already exists on PyPI. PyPI does not allow overwriting. You must bump the version and release again.

### Tag was pushed but workflow did not trigger

Confirm the tag matches the `v*` pattern (e.g., `v2.6.0` not `2.6.0`). Check the Actions tab — filter by the `Publish` workflow.

### TestPyPI publish succeeds but PyPI job is blocked

If the `pypi` GitHub environment has required reviewers configured, you must approve the deployment from the Actions UI before the job runs.

### Version on PyPI doesn't match `pyproject.toml`

The build is stamped with whatever version is in `pyproject.toml` at the time `uv build` runs. release-please keeps `pyproject.toml` and `src/doxa_research/__init__.py` in sync — if they're out of sync, suspect a hand-edit that bypassed the Release PR.

### Release PR does not appear after landing a `feat:`/`fix:` commit

Check the `release-please` workflow run in the Actions tab. Common causes:
- The commit was authored directly against `main` with a message release-please does not parse (e.g., missing type prefix).
- The `release-please-config.json` or `.release-please-manifest.json` file is malformed — validate JSON.
- The workflow's `contents: write` / `pull-requests: write` permissions were removed.

### Release PR merged but `publish.yml` did not fire

`release-please.yml` is configured to mint a GitHub App installation token (see [GitHub App Setup for release-please](#github-app-setup-for-release-please)) because the default `GITHUB_TOKEN` does **not** retrigger `push`-triggered workflows. If `publish.yml` doesn't fire:

1. Check that the **Create App Token** step in the `release-please` workflow run succeeded. Failures there mean `secrets.RELEASE_PLEASE_CLIENT_ID` or `secrets.RELEASE_PLEASE_PRIVATE_KEY` is missing/wrong, or the App isn't installed on this repo — rerun the `repo-secrets` provisioning step and verify the org App installation.
2. Confirm the App has **Contents: Read and write** permission (needed to push tags).
3. As a last-resort fallback, change `publish.yml` to trigger on `release: types: [published]` instead of `push.tags`, since release-please also creates the GitHub Release.

### Commit rejected locally with `subject may not be empty` / `type may not be empty`

Your commit message does not match Conventional Commits. Prefix with one of the allowed types (`feat:`, `fix:`, `chore:`, etc.) followed by a space and a short subject. Example: `fix: correct perplexity citation offset`.
