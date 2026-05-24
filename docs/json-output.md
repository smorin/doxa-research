# JSON output (`--json`) — envelope contract

Every data/action admin command in doxa-research supports `--json` for scripted
consumption. The output is a single JSON object on stdout; the exit code
indicates success (0) or failure (non-zero).

## Envelope shapes

**Success:**

    {"status": "ok", "data": {...}}

**Error:**

    {"status": "error", "error": {"code": "STRING_CODE", "message": "...",
                                   "details": {...}?}}

`details` is optional and code-specific.

## Error codes (catalog)

| Code | Used by | Exit | Meaning |
|---|---|---|---|
| `OPERATION_NOT_FOUND` | `status`, `resume`, `cancel` | 6 | Op ID not in checkpoint store |
| `OPERATION_FAILED_PERMANENTLY` | `resume` | 7 | Permanent failure |
| `JSON_REQUIRES_NONINTERACTIVE` | `init` | 2 | `init --json` without `--non-interactive` |
| `EDITOR_FAILED` | `config edit` | 1 | `$EDITOR` exited non-zero |
| `UNSUPPORTED_SHELL` | `completion` | 2 | Shell name not in {bash, zsh, fish} |
| `INSTALL_REQUIRES_TTY` | `completion --install` | 2 | non-TTY + no `--force` + no `--manual` |
| `INSTALL_FILE_PERMISSION` | `completion --install` | 1 | Can't write to rc file |
| `KEY_NOT_FOUND` | `config get` | 1 | Config key doesn't exist |
| `INVALID_LAYER` | `config get --layer` | 2 | Click choice validation |
| `PROVIDER_FAILURE` | `ask`, `resume` | 1 | Upstream provider error |
| `API_KEY_MISSING` | `ask`, `resume`, `providers check` | 1 | Required key not set |
| `INTERRUPTED` | any | 130 | SIGINT during `--json` run |

## Per-command schemas (sketch)

**`init --json --non-interactive`:**

    {"status": "ok",
     "data": {"path": "...", "created": true|false, "target": "project"|"user"|"hidden"}}

**`ask --json`:**

Immediate-mode runs return the result inline. Background-mode runs submit and
return an operation ID without blocking.

    {"status": "ok",
     "data": {"status": "completed"|"submitted",
              "operation_id": "..."?,
              "result": "..."?}}

**`status OP_ID --json`:**

    {"status": "ok",
     "data": {"operation_id": "...", "status": "running"|"completed"|...,
              "mode": "...", "prompt": "...",
              "providers": {...}, "output_paths": {...}}}

**`list --json`:**

    {"status": "ok",
     "data": {"count": N,
              "operations": [{"operation_id": "...", "status": "...", ...}, ...]}}

**`providers list --json`:**

    {"status": "ok",
     "data": {"providers": [{"name": "openai", "key_set": true}, ...]}}

**`providers models --json`:**

    {"status": "ok",
     "data": {"providers": {"openai": {"models": ["o3", ...]}}}}

**`providers check --json`:**

    {"status": "ok",
     "data": {"complete": true|false, "missing": ["openai", ...]}}

**`config get KEY --json`:**

    {"status": "ok",
     "data": {"key": "general.default_mode", "value": "thinking", "source": "user"}}

**`config set KEY VALUE --json` / `config unset KEY --json`:**

    {"status": "ok",
     "data": {"key": "test.key", "path": "...", "changed": true|false}}

**`config list --json`:**

    {"status": "ok",
     "data": {"config": {...}, "layer": "merged"}}

**`config path --json`:**

    {"status": "ok",
     "data": {"path": "...", "exists": true|false}}

**`config edit --json`:**

    {"status": "ok",
     "data": {"path": "...", "editor": "..."}}

**`config profiles list --json`:**

    {"status": "ok",
     "data": {"profiles": [{"name": "fast", "active": true|false, ...}, ...]}}

**`config profiles show NAME --json` / `config profiles current --json`:**

    {"status": "ok",
     "data": {"name": "fast", "profile": {...}, "source": "user"}}

**`config profiles add NAME --json` / `config profiles remove NAME --json`:**

    {"status": "ok",
     "data": {"name": "fast", "path": "...", "changed": true|false}}

**`config profiles set NAME KEY VALUE --json` / `config profiles unset NAME KEY --json`:**

    {"status": "ok",
     "data": {"name": "fast", "key": "general.default_mode", "changed": true|false}}

**`config profiles set-default NAME --json` / `config profiles unset-default --json`:**

    {"status": "ok",
     "data": {"default_profile": "fast"|null, "changed": true|false}}

**`modes list --json`:**

    {"status": "ok",
     "data": {"modes": [{"name": "thinking", "kind": "immediate", ...}, ...]}}

**`modes set-default NAME --json` / `modes unset-default --json`:**

    {"status": "ok",
     "data": {"default_mode": "deep_research", "wrote": true, "path": "..."}}

    {"status": "ok",
     "data": {"removed": true|false, "reason": "NOT_FOUND"?, "path": "..."}}

**`completion <shell> --install --json`:**

    {"status": "ok",
     "data": {"shell": "bash", "action": "written"|"preview"|"skipped",
              "path": "/.../.bashrc", "message": "..."}}

**`resume OP_ID --json` (snapshot — never advances state):**

    {"status": "ok",
     "data": {"operation_id": "...", "status": "running"|"recoverable_failure"|...,
              "mode": "...", "prompt": "...", "last_error": "..."|null,
              "retry_count": N}}

`recoverable_failure` is an envelope-data state mapped from on-disk
`status="failed"` + `failure_type` not equal to `"permanent"`. The
COMMAND succeeded (`status:"ok"`); `data.status` describes the
operation. To advance/retry, run `doxa-research resume OP_ID` WITHOUT `--json`.

**`cancel OP_ID --json`:**

    {"status": "ok",
     "data": {"status": "ok",
              "operation_id": "...",
              "providers": {"openai": {"status": "cancelled"|"completed"|...}}}}

Already-terminal operations return the same outer envelope with
`data.status="already_terminal"` and a `data.previous` terminal state.

Missing operations emit `OPERATION_NOT_FOUND` with exit 6, matching `status`
and `resume`.

## Non-blocking guarantee (Option E)

`--json` is non-blocking and snapshot-shaped:

  * `ask --json` immediate-mode: synchronous; full result inline.
  * `ask --json` background-mode: auto-async — submit + return op-id envelope.
  * `resume --json`: pure snapshot; never polls; never advances state.

Tests assert these complete within 5 seconds.

## Uninstalling completion

The completion `--install` writes a fenced block:

    # >>> doxa-research completion >>>
    eval "$(_DOXA_COMPLETE=bash_source doxa-research)"
    # <<< doxa-research completion <<<

Remove with one sed invocation:

    sed -i '/# >>> doxa-research completion >>>/,/# <<< doxa-research completion <<</d' ~/.bashrc

A real `--uninstall` flag is a future PR.

## `config validate [PATH] --json`

**Success envelope** — exit 0:

```json
{
  "status": "ok",
  "data": {
    "path": "<resolved path>",
    "checks": ["schema"]
  }
}
```

(`checks` is `["schema", "drift"]` when PATH resolves to the shipped starter template.)

**Error envelope** — exit 1. Error codes:

| code | When |
|---|---|
| `FILE_NOT_FOUND` | PATH does not exist, is not a regular file, or could not be opened (also: no PATH and no user-tier config file). |
| `TOML_PARSE_ERROR` | File is not valid TOML. `details.path` is the resolved file path; line/column appear in the human `message` from `tomllib`. |
| `SCHEMA_VALIDATION` | File parses but fails `UserConfigFile.model_validate`. `details.errors` is the full Pydantic error list. |
| `DRIFT_MISSING_KEY` | Drift check: template missing a `StarterField` path. `details.path` and `details.expected`. |
| `DRIFT_VALUE_MISMATCH` | Drift check: value at a `StarterField` path differs from schema default. `details.path`, `details.expected`, `details.actual`. |
| `PACKAGE_DATA_MISSING` | `importlib.resources` could not resolve the shipped template (broken wheel). |
