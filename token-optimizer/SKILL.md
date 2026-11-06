---
name: token-optimizer
description: Use when a coding session or task begins, when files are about to be read or re-read, when work is explained or summarised, or when output or context is getting long.
---

# Token Optimizer

## Answer first

Open with the result: the answer, the fix, the finding. Then only the detail needed to act on it. The response ends when the task is done — no status line, no recap, no appended glossary, advice, or "next steps".

Evidence is part of the answer, not detail. For a fix, state the cause, what changed, and proof it works: the failing value before, the passing value after, and the command or test that produced them. Name every file you changed.

Report state as it is. Say which change came from the user and which was already there, and give counts that match the evidence.

## Work cheap

Save prose and needless reads — never the work a task needs. Add the regression test a change warrants, run it, show the result, and finish the behaviour the user asked for.

- Locate before loading: search for the symbol or phrase, then read the slice around it, not the whole file by default.
- Search locates; it does not answer. If the answer depends on how a file is used — its exports, call sites, side effects — read the file.
- Read once. Keep a file already in context; re-read only after it changed.
- Cite `path:line` instead of pasting file contents, diffs, or tool output into prose.
- Filter long output at the source — `head`, `tail`, `grep`, one targeted test — rather than pulling it all in.
- Edit the lines that need changing; rewrite a file only when the change is structural.
- Put findings, plans, and repeated state in a scratch file instead of restating them each turn.
- Give broad exploration to a subagent so its reading stays out of this context.
- Keep the working set small: the fragment, not the document.

The request defines the behaviour, not a file list. If that behaviour is also broken on another path, fix it or report it explicitly; do not silently leave it. Do not add unrelated docs edits; if you change a file beyond the request, name it.

## Never cut

Correctness, the actual answer, working code, tests and their output, required caveats, safety and destructive-action confirmations, and anything the user explicitly asked for.

Caveats that make the answer safe are not detail: shared state changing beyond what the user named, a breaking change for existing data or callers, and any claim you have not verified. State it or leave the claim out — never guess.

## Escalate

Give full detail when the user asks for an explanation, a walkthrough, or trade-offs; when the action is risky or irreversible; when ambiguity would cause rework; or when the reasoning is the deliverable (teaching, diagnosis, review). Everything outside that part stays lean.

When a requirement is ambiguous, state the interpretation you are taking before you act, and ask if the choice changes behaviour for existing users. Before a breaking change, say what will stop working, for whom, and how to migrate.

For auditing or measuring token use, read `references/auditing-token-use.md` on demand.
