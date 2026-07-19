# Publishing Doxa Research to PyPI

This guide walks through the one-time setup and recurring release process for publishing doxa-research to PyPI using OIDC trusted publishing (no API tokens required).

---

## Prerequisites

- PyPI account at https://pypi.org
- TestPyPI account at https://test.pypi.org
- Admin access to the GitHub repository

---

## One-Time Setup

### Step 1: Configure GitHub Environments

Go to **Settings → Environments** in the GitHub repo and create two environments:

| Environment | Required reviewers |
|-------------|-------------------|
| `testpypi`  | None (auto-approve) |
| `pypi`      | Optional: add yourself as required reviewer for extra safety |

### Step 2: Register Trusted Publishing on TestPyPI

1. Log in to https://test.pypi.org
2. Open the existing `doxa-research` project, then go to **Manage → Publishing**
3. Add a GitHub Actions trusted publisher with:
   - **Owner**: `smorinlabs`
   - **Repository name**: `doxa-research`
   - **Workflow filename**: `publish.yml`
   - **Environment name**: `testpypi`

### Step 3: Register Trusted Publishing on PyPI

1. Log in to https://pypi.org
2. Open the existing `doxa-research` project, then go to **Manage → Publishing**
3. Add the same GitHub Actions trusted publisher as TestPyPI but with:
   - **Environment name**: `pypi`

Keep the previous `smorin/doxa-research` publisher only until the first
organization-owned publishing verification succeeds, then remove it from both
indexes.

### Step 4: Verify `pyproject.toml` metadata

Confirm these fields are correct before first publish:

```toml
[project]
name = "doxa-research"
version = "2.5.0"          # Must match git tag: v2.5.0
authors = [{ name = "Steve Morin", email = "steve.morin@gmail.com" }]

[project.urls]
Homepage = "https://github.com/smorinlabs/doxa-research"
```

---

## Release Process

Releases are automated by **release-please**. You write conventional-commit messages; release-please opens a Release PR with the version bump and `CHANGELOG.md` update. Merging the Release PR creates the `vX.Y.Z` tag, which triggers `publish.yml`.

### Step 1: Land conventional commits on main

```bash
git commit -m "feat: add new provider"
git commit -m "fix: handle timeout on stream close"
git push origin main
```

The local `commit-msg` lefthook and the `commitlint` CI job enforce the format.

### Step 2: Wait for / review the Release PR

After each push to `main`, `release-please.yml` opens (or updates) a single PR titled `chore(main): release X.Y.Z`. Its diff bumps `pyproject.toml`, `src/doxa_research/__init__.py`, `.release-please-manifest.json`, and appends to `CHANGELOG.md`.

Verify:
- The proposed version matches the semantic weight of the commits since the last tag.
- The changelog section lists the expected features/fixes.

### Step 3: Merge the Release PR

Merge via the GitHub UI. release-please then:
1. Creates the tag `vX.Y.Z` on the merge commit.
2. Creates a GitHub Release with the changelog section as the body.

### Step 4: Monitor the publish workflow

The tag push triggers **Actions → Publish**:
1. **build** — wheel + sdist in `dist/`
2. **publish-testpypi** — https://test.pypi.org/project/doxa-research/
3. **publish-pypi** — https://pypi.org/project/doxa-research/

### Step 5: Verify the release

```bash
# Verify on TestPyPI
pip install --index-url https://test.pypi.org/simple/ doxa-research==2.6.0
doxa --version

# Verify on PyPI
uvx doxa-research==2.6.0 --version
# or
pip install doxa-research==2.6.0
doxa --version
```

---

## Quick Reference

| Value | What to use |
|-------|------------|
| PyPI project name | `doxa-research` |
| GitHub owner | `smorin` |
| GitHub repo | `doxa-research` |
| Workflow file | `publish.yml` |
| TestPyPI environment | `testpypi` |
| PyPI environment | `pypi` |
| Tag format | `v2.6.0` |

---

## Local Build (Optional)

To build locally without publishing:
```bash
make build
ls dist/
# doxa-research-2.6.0-py3-none-any.whl
# doxa-research-2.6.0.tar.gz
```

To publish manually (requires API token):
```bash
uv publish --token pypi-...
```

---

## Manual Fallback (uv + `.pypirc`)

> ⚠️ **EMERGENCY ONLY. DO NOT USE FOR NORMAL RELEASES.**
>
> The CI path (`publish.yml` triggered by tag push) is the canonical
> publisher. Using laptop builds creates a permanent obstacle: laptop
> wheels and CI wheels are NOT bit-reproducible (different file mtimes,
> macOS xattrs, uv versions). Once you upload a wheel under filename
> `doxa_research-X.Y.Z-py3-none-any.whl` from a laptop, neither PyPI nor
> TestPyPI will EVER accept a re-upload under that same filename — even
> after deletion. You lock the registry to that exact byte-blob forever.
> The only recovery is to bump to a new version (see CHANGELOG entry for
> v3.0.1 for the post-mortem of when this happened).
>
> When to actually use this path:
> - CI is down for an extended period and a hot-fix release must ship
> - OIDC trusted publisher is misconfigured and can't be fixed quickly
> - You are intentionally publishing a non-tag pre-release for testing

Use this path only when OIDC trusted publishing is unavailable (CI down,
release-please blocked, urgent laptop publish). The primary path remains
release-please → `publish.yml`.

### One-time setup

1. Create your tokens (if you don't already have them):
   - PyPI:     https://pypi.org/manage/account/token/
   - TestPyPI: https://test.pypi.org/manage/account/token/
2. Copy the template and fill in tokens:
   ```bash
   cp .pypirc.template .pypirc
   chmod 600 .pypirc
   $EDITOR .pypirc
   ```
   `.pypirc` is gitignored. The `check-pypirc` recipe enforces mode `0600`
   and refuses to publish otherwise.

### Publish

```bash
# Dry run / sanity: TestPyPI
just publish-test-manual

# Real release: PyPI
just publish-manual
```

Both recipes:
1. Run `check-pypirc` (existence + perms guard).
2. Parse the matching token out of `.pypirc` with Python `configparser`.
3. `rm -rf dist/` then `uv build` (clean wheel + sdist).
4. `uv publish --token <token>` (TestPyPI uses `--publish-url
   https://test.pypi.org/legacy/`).

Tokens never appear on the command line as literals — they're read from
`.pypirc` and passed to `uv publish` via `--token`. `uv publish` is used
(not `twine`) for tool-stack consistency with the OIDC path.
