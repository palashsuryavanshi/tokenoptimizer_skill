# Token Optimizer — Agent Skill

A portable agent skill that lowers token usage per turn by shaping both output style and context habits — without reducing answer quality.

## What It Does

When loaded, the skill guides the agent to:

- **Answer first** — open with the result, then only the detail needed to act on it. No preamble, no recap, no unrequested summaries.
- **Work cheap** — locate before loading, read slices not whole files, cite `path:line` instead of pasting content, filter output at the source, use scratch files for repeated state, delegate broad exploration to subagents.
- **Never cut** — correctness, working code, tests and their output, required caveats, safety confirmations, and anything explicitly asked for are never trimmed.
- **Escalate** — full detail when the user asks for an explanation, when the action is risky or irreversible, when ambiguity would cause rework, or when the reasoning is the deliverable.

## Verified Results

| Scenario | Baseline | With Skill | Quality |
|----------|----------|------------|---------|
| Explanation | 1,657 words | 787 words | Baseline better (disclosed) |
| Bug hunt | 107 words | 133 words | **Skill better** |
| Long session | 368 words | 527 words | **Skill better** |
| Escalation task | 915 words | 846 words | **Skill better** |

Overall output reduction: **~25%** (3,047 → 2,293 words) on a planted-bug fixture with blind quality gates. The skill was developed TDD-style: RED baseline → GREEN (three rounds, two failures) → REFACTOR → final gate.

## Install

Copy the `token-optimizer/` folder into your agent's skills directory:

```bash
# OpenCode / cross-runtime
cp -r token-optimizer ~/.agents/skills/

# Claude Code (also works)
cp -r token-optimizer ~/.claude/skills/
```

Or add this line to a project's instructions file for guaranteed always-on:

```
# Load the token-optimizer skill at session start
skill: token-optimizer
```

## Structure

```
token-optimizer/
├── SKILL.md                          # Main skill (590 words)
└── references/
    └── auditing-token-use.md         # On-demand audit reference (126 lines)
```

## Requirements

- Plain Markdown — no hooks, plugins, MCP config, or agent-specific syntax
- Works with OpenCode, Claude Code, Codex, and any agent that loads skills by description

## License

MIT — use freely in any project.