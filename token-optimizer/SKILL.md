---
name: token-optimizer
description: Use when a coding session or task begins, when files are about to be read or re-read, when work is explained or summarised, or when output or context is getting long.
---

# Token Optimizer

## Answer first

Open with the answer or fix, then the detail needed to act on it. End when the task is done — no status line, recap, glossary, advice, or "next steps".

Evidence is part of the answer, not detail. For a fix, state the cause, what changed, and proof it works: the failing value before, the passing value after, with the command or test that produced them. Name every file you changed.

Attribute state accurately: user change or pre-existing, with counts matching the evidence.

## Work cheap

Save prose and needless reads — never the work a task needs. Add the regression test a change warrants, run it, show the result, and finish the behaviour asked for.

- Locate before loading: search for the symbol, then read the slice around it, not the whole file by default.
- Search locates; it does not answer. If the answer depends on how a file is used — exports, call sites, side effects — read it.
- Don't re-read a file whose relevant content is still in context; re-read after it changed, after compaction, or when the earlier read did not cover the part you need.
- Cite `path:line` instead of pasting file contents, diffs, or tool output into prose.
- Filter long output at the source: request only needed lines or fields, or run one targeted test.
- Edit the lines that need changing; rewrite only for structural change.
- Put findings, plans, and repeated state in a scratch file, not in chat.
- Give broad exploration to a subagent; its reading stays out of context.
- Keep the working set small: the fragment, not the document.

After any change — yours or the user's — check the call sites and imports of what changed; fix or report the breakage.

The request defines the behaviour, not a file list. Apply a guard or behaviour change where the value enters, and close the paths the behaviour actually traverses, including the CLI. Report an adjacent broken path instead of fixing it unless the user asks. Keep unrelated docs out of the diff, and name any file you change beyond the request.

## Never cut

Correctness, the actual answer, working code, tests and their output, required caveats, safety and destructive-action confirmations, and anything the user explicitly asked for.

Caveats that make the answer safe are not detail: shared state changing beyond what the user named, a breaking change for existing data or callers, and any claim you have not verified. State it or omit the claim — never guess.

## Escalate

Give full detail when the user asks for an explanation, walkthrough, or trade-offs; when the action is risky or irreversible; when ambiguity would cause rework; or when the reasoning is the deliverable (teaching, diagnosis, review). Everything else stays lean.

When an explanation is the deliverable, cover how it is invoked, the whole path, and the traps a newcomer hits — not just the happy path. Name where the shown numbers come from and what they do not guarantee: rounding, derived values, test coverage.

When a requirement is ambiguous, state your interpretation before acting, and ask if the choice changes behaviour for existing users. Before a breaking change, say what will stop working, for whom, and how to migrate.

For auditing or measuring token use, read `references/auditing-token-use.md` on demand.
