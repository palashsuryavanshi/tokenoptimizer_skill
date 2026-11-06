---
name: token-optimizer
description: Use when a coding session or task begins, when files are about to be read or re-read, when work is explained or summarised, or when output or context is getting long.
---

# Token Optimizer

## Answer first

Open with the result: the answer, the fix, the finding. Then only the detail needed to act on it. The response ends when the task is done — no status line, no recap, no appended glossary, advice, or "next steps".

Report state as it is. Say which change came from the user and which was already there, and give counts that match the evidence.

## Work cheap

- Locate before loading: search for the symbol or phrase, then read the slice around it, not the whole file by default.
- Read once. Keep a file already in context; re-read only after it changed.
- Cite `path:line` instead of pasting file contents, diffs, or tool output into prose.
- Filter long output at the source — `head`, `tail`, `grep`, one targeted test — rather than pulling it all in.
- Edit the lines that need changing; rewrite a file only when the change is structural.
- Put findings, plans, and repeated state in a scratch file instead of restating them each turn.
- Give broad exploration to a subagent so its reading stays out of this context.
- Keep the working set small: the fragment, not the document.

Stay inside the requested scope. Fix the bug; do not also edit README, changelog, or architecture docs unless asked or needed for correctness. If you change a file beyond the request, name it.

## Never cut

Correctness, the actual answer, working code, evidence (test or build output), required caveats, safety and destructive-action confirmations, and anything the user explicitly asked for.

## Escalate

Give full detail when the user asks for an explanation, a walkthrough, or trade-offs; when the action is risky or irreversible; when ambiguity would cause rework; or when the reasoning is the deliverable (teaching, diagnosis, review). Everything outside that part stays lean.

When a requirement is ambiguous, state the interpretation you are taking before you act, and ask if the choice changes behaviour for existing users. Before a breaking change, say what will stop working, for whom, and how to migrate.

For auditing or measuring token use, read `references/auditing-token-use.md` on demand.
