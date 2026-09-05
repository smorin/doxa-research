# P42 - Shorten the Doxa Skill Description to Action-Scoped Triggers

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)
- **Related:** `plugins/doxa-research/skills/doxa-research/SKILL.md` (the
  skill whose frontmatter `description` this project rewrites)
- **Related:** Eric Provencher, "Rethinking skills and prompts for GPT-6
  Astra" (https://x.com/i/article/2095989703967125509) — the guidance
  behind the new shape
- **Related:** Claude Code docs, Skills → skill listing budget — the
  listing is capped at 1% of the context window and descriptions are
  dropped from the least-used skills first

**Status:** `[~]` In progress.

**Goal**: Rewrite the `doxa-research` skill description to one shape —
what it does, "use when" a specific action, "not for" its one sibling
collision (`guided-research`) — from 535 to 328 characters, keeping the
"use only when the user explicitly says Doxa" guard that prevents it
from firing on generic research requests. Plugin manifests and the
marketplace entry bump to 0.1.1. Body and CLI behavior unchanged.

### Tests & Tasks
- [x] [P42-T01] Rewrite the description; keep the explicit-Doxa guard
- [x] [P42-T02] Bump `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, and the marketplace entry to 0.1.1
- [ ] [P42-TS01] `just check` green; PR merged and main fast-forwarded
