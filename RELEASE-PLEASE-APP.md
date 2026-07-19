# GitHub App Setup for release-please

This document is the canonical step-by-step guide for creating, configuring, and installing the GitHub App that powers the `release-please.yml` workflow. It supersedes the brief setup section in [RELEASE.md](RELEASE.md#github-app-setup-for-release-please).

## Why a GitHub App at all?

The `release-please.yml` workflow needs to push a tag (e.g. `v3.0.2`) when a Release PR merges. That tag push must trigger `publish.yml` so the artifact reaches PyPI. There is exactly one obstacle:

**The default `secrets.GITHUB_TOKEN` cannot trigger other workflows.** GitHub designed this constraint to prevent infinite workflow loops (`workflow A pushes → triggers workflow A → pushes again …`). If release-please pushed tags using the default token, `publish.yml` would never fire and nothing would publish.

A GitHub App installation token *is* a different actor — pushes signed by it DO trigger downstream workflows. So we create an App once, install it on each repo that needs release-please, and the workflow mints a short-lived installation token at run time. No long-lived secret, no PAT, no manual token rotation.

## One App, many repos

A single GitHub App can be installed on as many repos as you want. **Recommended pattern: one App per user (or org), reused across all repos that use release-please.**

| Reused across repos | Per-repo setup |
|---|---|
| The App registration (name, permissions, owner) | The App's installation on the specific repo |
| The App Client ID | The `RELEASE_PLEASE_CLIENT_ID` repo secret (same value across repos) |
| The App's private key (one `.pem`) | The `RELEASE_PLEASE_PRIVATE_KEY` repo secret (same contents, stored per-repo) |
| The `release-please.yml` workflow shape | The workflow file itself (each repo has its own copy) |

The organization-owned `release-please-smorinlabs` App is installed for all
`smorinlabs` repositories. For each repository, provision the two repository
secrets through the `repo-secrets` workflow.

## Initial setup — creating the App

This is a one-time action per GitHub account (NOT per repo). If the App already exists, skip to "Per-repo installation".

### Step 1 — Open the App creation form

Go to **https://github.com/organizations/smorinlabs/settings/apps/new**.

### Step 2 — Fill in the form

Below is each field, what to enter, and why.

#### GitHub App name

`release-please-smorinlabs`.

The name must be globally unique on GitHub. Suffix with a number if the name is taken.

#### Description

Free text. Something like:

```
This is the app used to release projects with release-please, including:
- doxa-research
```

Only visible to you in App settings; doesn't affect behavior.

#### Homepage URL

Any valid URL. Examples that work fine:
- `https://github.com/smorinlabs/`
- `https://github.com/smorinlabs/doxa-research`

GitHub requires SOMETHING here but doesn't otherwise use it.

#### Callback URL

**Leave empty.** Callback URLs are for OAuth flows; release-please doesn't use OAuth.

#### Identifying and authorizing users — three checkboxes

| Checkbox | Action |
|---|---|
| Expire user authorization tokens | **Unchecked** |
| Request user authorization (OAuth) during installation | **Unchecked** |
| Enable Device Flow | **Unchecked** |

None of these apply to release-please.

#### Post installation — Setup URL & Redirect on update

**Leave Setup URL empty. Leave "Redirect on update" unchecked.** No post-install handoff is needed.

#### Webhook — UNCHECK Active ⚠️

This is the most commonly-missed step.

The **Active** checkbox in the Webhook section is **on by default**. Uncheck it.

release-please does NOT use webhooks. It polls GitHub's API when the workflow runs. With webhooks active, GitHub demands a Webhook URL (which we don't have) and the form fails validation.

Once Active is unchecked, the Webhook URL and Secret fields below it become irrelevant — ignore them.

#### Repository permissions — set ONLY these three

Scroll to **Repository permissions**. You'll see a long list, each defaulting to **No access**. Change ONLY:

| Permission | Value | Why |
|---|---|---|
| **Contents** | Read and write | release-please pushes tags, modifies `CHANGELOG.md`, `pyproject.toml`, `src/<pkg>/__init__.py`, manifest file |
| **Pull requests** | Read and write | release-please opens, updates, and (after merge) closes the Release PR |
| **Issues** | Read and write | release-please occasionally creates/links issues during release coordination; granting avoids edge-case failures |

**Leave every other Repository permission at "No access."** Specifically:
- `Workflows` — do NOT grant; would let the App modify CI configs
- `Administration` — do NOT grant; never needed
- `Secrets` — do NOT grant; the App must not read repo secrets

The principle of least privilege: only what release-please needs and nothing more.

#### Organization permissions

**Leave ALL Organization permissions at "No access."** Not relevant for a personal-account repo.

#### Account permissions

**Leave ALL Account permissions at "No access."** Not relevant.

#### Subscribe to events

**Leave every event checkbox unchecked.** Since webhooks are off (Step 7), subscriptions don't do anything anyway, but leaving them unchecked is cleaner.

#### Where can this GitHub App be installed?

**Only on this account** (`smorinlabs`).

A public App ("Any account") can be installed by strangers. Private automation Apps should stay scoped to the account that owns them.

### Step 3 — Click "Create GitHub App"

You're taken to the App's settings page. **Note the Client ID** displayed near
the top. `actions/create-github-app-token@v3` accepts this value through its
`client-id` input.

### Step 4 — Generate a private key

On the same settings page, scroll to **Private keys**.

Click **Generate a private key**.

A `.pem` file downloads to your browser, named like
`release-please-smorinlabs.YYYY-MM-DD.private-key.pem`.

**Treat this file as a credential.** Anyone with its contents can act as the App.

Open the file in a text editor. It is a standard PEM-encoded RSA private key — a header line, then many lines of base64-encoded key data, then a matching footer line.

You'll paste the entire file contents (header, body, and footer) into the per-repo secret in the next phase.

After you've stored it in GitHub Secrets for each repo, delete the local file:

```bash
rm ~/Downloads/release-please-smorinlabs.*.private-key.pem
```

## Per-repo setup

Do this for every repo where you want release-please to drive releases.

### Step 5 — Install the App on the repo

From the App's settings page, click **Install App** in the left sidebar, or
visit `https://github.com/organizations/smorinlabs/settings/installations`.

The current `smorinlabs` installation grants access to all repositories, so a
new or transferred repository is covered automatically. If that policy changes
to selected repositories, add `doxa-research` explicitly.

### Step 6 — Add `RELEASE_PLEASE_CLIENT_ID` as a repo secret

Open: `https://github.com/<owner>/<repo>/settings/secrets/actions`

Click **New repository secret**:

| Field | Value |
|---|---|
| Name | `RELEASE_PLEASE_CLIENT_ID` |
| Secret | the Client ID from Step 3 |

Click **Add secret**. Although a Client ID is not a private credential on its
own, the repository's canonical provisioning workflow stores both App inputs in
the same secret namespace.

### Step 7 — Add `RELEASE_PLEASE_PRIVATE_KEY` as a repo secret ⚠️

**THIS IS A SECRET, NOT A VARIABLE.** Adding it to the wrong store is the most
common and most damaging setup mistake; see "Store both workflow inputs as
repository secrets" below.

Open: `https://github.com/<owner>/<repo>/settings/secrets/actions`

Note the URL ends in `/secrets/actions` (NOT `/variables/actions`).

Click **New repository secret**:

| Field | Value |
|---|---|
| Name | `RELEASE_PLEASE_PRIVATE_KEY` |
| Secret | the ENTIRE contents of the `.pem` file from Step 4, including the `-----BEGIN RSA PRIVATE KEY-----` and `-----END RSA PRIVATE KEY-----` lines |

Click **Add secret**.

After saving, the secret name appears in the list but the value cannot be viewed. That's correct behavior — you've stored it in the encrypted store.

### Step 8 — Verify the workflow file references match

Confirm `.github/workflows/release-please.yml` looks up the correct names:

```yaml
- uses: actions/create-github-app-token@v3
  id: app-token
  with:
    client-id: ${{ secrets.RELEASE_PLEASE_CLIENT_ID }}
    private-key: ${{ secrets.RELEASE_PLEASE_PRIVATE_KEY }}
```

Both values are read from `secrets.X`. If either expression points at a missing
entry, it interpolates to an empty string and the action fails with
`Input required and not supplied: <field>`.

## Verification

### Smoke test

Push an empty commit to `main`:

```bash
git commit --allow-empty -m "chore: trigger release-please smoke test"
git push origin main
```

Watch the workflow:

```bash
gh run list --workflow=release-please.yml --limit 1
gh run watch $(gh run list --workflow=release-please.yml --limit 1 --json databaseId --jq '.[0].databaseId')
```

The run should complete green in 10-15 seconds. Both steps must succeed:
- `Run actions/create-github-app-token@v3`
- `Run googleapis/release-please-action@v5`

If release-please calculates a release is due, it opens (or updates) a Release PR. If not, it exits cleanly. Either is a successful smoke test.

### What a working release-please PR looks like

A correctly-configured release-please opens a PR titled `chore(main): release X.Y.Z` authored by `app/<your-app-name>`. The branch name follows the pattern `release-please--branches--main--components--<pkg>`. The PR diff bumps:

- `pyproject.toml`
- `src/<pkg>/__init__.py` (via the `extra-files` config entry)
- `CHANGELOG.md`
- `.release-please-manifest.json`

## Store both workflow inputs as repository secrets

The Variables and Secrets stores look similar in the UI but have different
security properties. Doxa's current workflow deliberately reads both App inputs
from repository secrets.

| | Variables | Secrets |
|---|---|---|
| Storage encryption | Cleartext | libsodium sealed boxes |
| API visibility | **Values returned in API responses** | Only names returned; values never readable |
| Logs | Routinely interpolated visible into job logs | Masked (GitHub redacts the value if it appears) |
| Lookup in workflow | `${{ vars.X }}` | `${{ secrets.X }}` |
| Threat model | "Useful config someone might inspect" | "Anything an attacker could use to impersonate the project" |
| Best for | Region names, port numbers, feature flags | Client IDs used by this workflow, passwords, tokens, private keys |

**If you add either workflow input to Variables instead of Secrets:**

1. The lookup expression `${{ secrets.X }}` returns empty (different namespace).
2. The action fails with `Input required and not supplied: <field>`.
3. The variable value is readable in cleartext through the repository API:
   ```bash
   gh api repos/<owner>/<repo>/actions/variables
   ```
   Anyone with repo read access can dump the contents.

**Recovery if this happens:**

1. If the misplaced value was the private key, treat it as compromised.
2. Generate a new private key and revoke/delete the old one.
3. Delete the misplaced variable.
4. Use `repo-secrets set --repo smorinlabs/doxa-research --app release-please --overwrite` to restore both repository secrets from 1Password.
5. Delete local `.pem` files and review organization audit activity.

## Key rotation

Rotate the private key annually, on suspected leak, or after any team-member offboarding.

1. On the App's settings page → **Generate a private key** → new `.pem` downloads.
2. Update the `release-please-smorinlabs` private-key item in 1Password, then run `repo-secrets ... --overwrite` for every repository that uses the App.
3. On the App's settings page, delete the OLD private key (three-dot menu next to the existing key entry → Delete).
4. Confirm by pushing an empty commit and watching the workflow.

The Client ID does not change during rotation. Only the private key does.

## Onboarding a new repo to release-please

For each new repo where you want release-please:

1. **Reuse the existing App.** The `smorinlabs` installation currently covers all repositories; otherwise add the new repository to its selected access list.
2. **Provision both secrets** with `repo-secrets set --repo smorinlabs/REPO --app release-please`.
3. **Copy `release-please.yml`** from a working repo. Adjust nothing — the workflow file is repo-agnostic; release-please reads project metadata from `release-please-config.json` and `.release-please-manifest.json` in each repo.
4. **Copy and adapt `release-please-config.json`**:
   - Update `package-name` to the new package's distribution name
   - Update `extra-files` to point at the new package's `__init__.py` (use underscore form for Python module path, e.g. `src/<pkg>_name>/__init__.py`)
5. **Create `.release-please-manifest.json`**:
   ```json
   { ".": "0.0.0" }
   ```
   (or the current published version if the package has a history)
6. **Verify** with the smoke test (push an empty commit; watch the workflow).

## Troubleshooting

### Workflow fails in 6-9 seconds at `Run actions/create-github-app-token@v3`

The action is failing before it can do anything useful. Common causes:

| Error message | Cause | Fix |
|---|---|---|
| `Input required and not supplied: private-key` | Secret is missing or has the wrong name | Provision `RELEASE_PLEASE_PRIVATE_KEY` with `repo-secrets`; rotate first if a private key was exposed as a Variable |
| `Input required and not supplied: client-id` | Secret is missing or has the wrong name | Provision `RELEASE_PLEASE_CLIENT_ID` with `repo-secrets` |
| `Error: A JSON web token could not be decoded` | The `.pem` contents were truncated or mangled when pasted | Re-paste the entire file content including the `-----BEGIN` and `-----END` lines, no extra whitespace, no surrounding code blocks |
| `Bad credentials` | The App's private key was rotated and the secret holds the old key | Update the secret with the new `.pem` contents |

### Workflow succeeds but no PR opens

This is normal if there are no release-worthy commits since the last release. The Conventional Commits rules:

- `fix:`, `perf:`, `refactor:` → patch bump
- `feat:` → minor bump (or patch with `bump-patch-for-minor-pre-major: true` before 1.0)
- `feat!:` or any commit with `BREAKING CHANGE:` footer → major bump
- `chore:`, `docs:`, `test:`, `ci:` → NO release

If you want every commit to trigger a release, set `"hidden": false` on every `changelog-sections` entry in `release-please-config.json` (this is unusual). Most projects gate releases behind `fix:`/`feat:` commits only.

### `release-please` runs but the Release PR's version bump is wrong

The version in the Release PR is computed from:
1. The `.release-please-manifest.json` baseline
2. Plus the highest bump implied by commits since the last release tag

If the manifest is out of sync with reality (e.g., the project was manually released without using release-please), edit `.release-please-manifest.json` to match the most recent published version and commit. The next release-please run will use the corrected baseline.

### The Release PR opens but merging it doesn't trigger `publish.yml`

This is exactly what the App token solves. Symptom: tag is created but no `Publish to PyPI` workflow run appears.

Possible causes:
- The workflow's tag-push step is being signed by `GITHUB_TOKEN` instead of the App token (a misconfigured release-please workflow). Confirm `release-please.yml` passes `token: ${{ steps.app-token.outputs.token }}` to the release-please action.
- `publish.yml` is missing or has a typo in its tag pattern. Confirm `on.push.tags` includes a glob like `v*` and that the tag matches.

## Security considerations

### What the App CAN do

With Contents, Pull requests, and Issues at "Read and write", the App can:
- Read any code in the installed repo
- Push branches (not directly to `main` — branch protection still applies to App writes if configured)
- Open, update, and close PRs
- Create, update, and close issues
- Create and push tags

It **cannot**:
- Modify repo settings, branch protection, or workflows
- Read or modify secrets
- Trigger Actions to run with elevated permissions
- Act outside the repos where it's explicitly installed

### What "leaked private key" actually means

A leaked private key means an attacker can mint installation tokens. The blast radius equals the App's installed scope. For `release-please-smorinlabs`, which is installed for all organization repositories, an attacker could:

- Push malicious code to a branch and open a PR (would still need the PR to be merged, which requires a human)
- Open issues, comment on PRs
- Push branches and tags that triggers downstream workflows like `publish.yml` — which is where the real risk lives. If the attacker can push a `v9.9.9` tag, the publish workflow will try to release that version to PyPI. This is mitigated by:
  - The `pypi` GitHub environment's required-reviewer protection (you have to approve every PyPI publish)
  - The `Validate tag matches package version` step in `publish.yml` (tag must match `pyproject.toml`)

### Rotation cadence

The community-standard cadence is **annual rotation**, plus immediate rotation on any suspected leak. Calendar reminder recommended.

### Audit trail

Use the `smorinlabs` organization audit log first, then review repository side effects:

```bash
# Branches that exist in the repo (should all be recognizable):
gh api "repos/<owner>/<repo>/branches" --paginate | jq '.[].name'

# PRs opened by the App:
gh pr list --author 'app/<your-app-name>' --state all

# Commits on main, scan for App-authored:
git log --pretty=format:'%h %an <%ae> %s' -50
```

If the only PRs opened by the App are the legitimate release PRs, and the only branches are `release-please--branches--*` (plus your own branches), the App's behavior is consistent with the expected workflow.

## Related documentation

- [RELEASE.md](RELEASE.md) — overall release process; assumes the App is already set up
- [PUBLISH.md](PUBLISH.md) — PyPI publishing details (token-based fallback path, etc.)
- [release-please-config.json](release-please-config.json) — per-package release rules
- [.github/workflows/release-please.yml](.github/workflows/release-please.yml) — the workflow that consumes the App credentials
- Upstream: [googleapis/release-please-action](https://github.com/googleapis/release-please-action)
- Upstream: [actions/create-github-app-token](https://github.com/actions/create-github-app-token)
