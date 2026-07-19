# doxa-research

The `doxa-research` skill operates Doxa's command-line workflows for approved,
fully formed research prompts. It selects compatible deep-research modes,
preflights configured providers, starts paid work with an explicit cost boundary,
records operation IDs, monitors or resumes background jobs, and preserves raw
provider and combined reports.

**Triggers on:** explicit Doxa requests such as "use Doxa", "run this through
Doxa", "fan this out through Doxa", and "resume/check this Doxa job", plus
approved workflows that have already selected Doxa as their execution engine.

**Arguments:** prompt file or files, requested provider/mode when specified,
output location, and async/blocking preference.

## Install

Install Doxa's CLI first:

```bash
uv tool install doxa-research
doxa init
```

Install the skill for Claude Code:

```text
/plugin marketplace add smorin/doxa-research
/plugin install doxa-research@doxa-research
```

Install the skill for Codex:

```bash
codex plugin marketplace add smorin/doxa-research --ref main
codex plugin add doxa-research@doxa-research
```

Other installation modes:

| Mode | When | How |
| --- | --- | --- |
| Plugin (recommended) | You want versioned installation and updates | Use the Claude Code or Codex commands above |
| Dev symlink | You want edits in a clone to load next session | Clone `https://github.com/smorin/doxa-research`, then link `plugins/doxa-research/skills/doxa-research` into `~/.claude/skills/doxa-research` and `~/.agents/skills/doxa-research` |
| Direct copy | Marketplace access is unavailable | Copy `plugins/doxa-research/skills/doxa-research/` into the tool's user skills directory |

## Example session

> Run the three `.prompt.md` files under `research/topics/` through Doxa's
> multi-provider deep-research mode. Keep every provider report and a combined
> report, and do not overwrite the prompt or framing files.
>
> The skill reads the research constraints, preflights Doxa and its providers,
> reports that three prompts can create up to nine paid provider requests,
> submits three separately tracked operations, monitors them, verifies their
> outputs, and returns exact report paths plus any partial failures.

## Boundary with guided-research

`guided-research` owns question shaping, prompt lineage, research decomposition,
and downstream decision records. `doxa-research` begins only after the prompts
are approved and ends after verified raw reports are handed back to that
decision workflow.
