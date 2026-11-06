# Optional: always-on pointer

Agents that load skills by description pick up `token-optimizer` on their own, so
this is optional. Add it only where the agent does not auto-load by description and
you want the skill active at the start of every session.

Three lines for a project instructions file (`AGENTS.md`, `CLAUDE.md`, or similar):

```text
At the start of every session, load the token-optimizer skill.
It is installed at ~/.agents/skills/token-optimizer/SKILL.md (Windows: C:\Users\oggyt\.agents\skills\token-optimizer\SKILL.md); follow it for the session.
Read its references/auditing-token-use.md only when measuring or auditing token use.
```

Adjust the path to wherever the skill was installed. Remove these lines to return to
description-based loading; the skill works the same either way, just on demand.
