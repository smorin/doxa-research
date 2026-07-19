# Doxa CLI Workflows

Use the live CLI help as the authority. The commands below describe the current
workflow but provider model names and available modes can change.

## Resolve and preflight

Prefer a persistent install:

```bash
uv tool install doxa-research
doxa --version
```

If `doxa` is not on `PATH`, `doxa-research` is an equivalent executable. For a
one-off run, `uvx doxa-research` is acceptable after the user approves network
access and ephemeral package execution.

Preflight without exposing key values:

```bash
doxa providers check --json
doxa modes list --kind background --json
doxa modes list --name all_deep_research --json
```

Do not use `--show-secrets`, and do not pass `--api-key-openai`,
`--api-key-perplexity`, or `--api-key-gemini`. Resolve credentials through the
environment or Doxa configuration.

## Choose a mode

| Goal | Starting point | Verify before use |
| --- | --- | --- |
| OpenAI + Perplexity + Gemini | `all_deep_research --combined` | All three providers have usable credentials |
| OpenAI only | `deep_research --provider openai` | `deep_research` is background-kind |
| Perplexity only | `perplexity_deep_research` | Provider and model in the live mode definition |
| Gemini only | `gemini_deep_research` | Provider and model in the live mode definition |

If a mode or provider combination fails preflight, inspect `doxa modes list
--name <mode> --json` and select a compatible live definition. Do not override a
model from memory merely to bypass Doxa's validation.

## Submit one prompt file

Allocate a dedicated directory first:

```bash
mkdir -p research/topics/http-semantics/doxa/00-landscape
doxa ask \
  --mode all_deep_research \
  --prompt-file research/topics/http-semantics/prompts/00-landscape.prompt.md \
  --output-dir research/topics/http-semantics/doxa/00-landscape \
  --combined \
  --async \
  --json \
  > research/topics/http-semantics/doxa/00-landscape/submit.json
```

The JSON submission envelope is the durable record for the operation ID. Keep
the prompt file and the framing file unchanged.

For a blocking single-provider run, omit `--async` and choose the appropriate
provider-pinned mode. Background modes write auto-named files under the output
directory; `--out` and `--append` are for immediate modes and must not be used.

## Submit several prompt files

Use one operation and directory per prompt. Submit a bounded approved batch
asynchronously, record each `submit.json`, then monitor by operation ID. Do not
start three Doxa processes against the same destination directory.

One Doxa `all_deep_research` operation already creates parallel provider work.
Three prompt files therefore produce three Doxa operations and up to nine paid
provider requests, plus combined report generation where configured.

## Monitor and recover

```bash
doxa status OPERATION_ID --json
doxa resume OPERATION_ID --async --json
doxa resume OPERATION_ID --json
doxa list --all --json
```

- `status` is read-only.
- `resume --async` performs one provider status pass, saves newly completed
  results, and exits.
- `resume` without `--async` enters the polling loop until terminal state or
  interruption.
- Never resubmit an operation merely because it is queued or slow.
- Use `doxa cancel OPERATION_ID --json` only when cancellation is explicitly
  requested or already covered by the agreed interrupt policy.

## Verify and promote artifacts

For every operation, verify:

1. terminal state from `status` or `resume`;
2. the providers that completed, failed, or were skipped;
3. a non-empty report for every completed provider;
4. a non-empty combined report when `--combined` was requested;
5. metadata for prompt, mode, provider/model, operation ID, and creation time;
6. direct citation links in the research content where the prompt required them.

Keep raw provider and combined outputs in the Doxa run directory. If the
repository expects a canonical path such as `00-landscape.md`, copy the selected
combined report there only after verifying that the destination does not exist
or obtaining approval to replace it. Record partial provider failures next to
the decision; a combined report does not make a failed provider successful.

## Failure handling

| Failure | Response |
| --- | --- |
| Missing credentials | Report the provider and credential source expected; never request the key value in chat |
| Mode/provider mismatch | Inspect the live mode definition and choose a compatible mode |
| Quota or billing error | Stop new submissions for that provider and preserve other successful results |
| Timeout or interruption | Resume the recorded operation ID instead of resubmitting |
| Partial multi-provider failure | Keep successful reports, report the gap, and ask whether a focused retry is worth the additional cost |
| Output collision | Select a new run directory; never merge auto-named outputs from distinct operations by hand |
