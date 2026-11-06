# Token Optimizer — design

2026-11-06 · Status: awaiting approval

## Intent

An agent skill that, once installed, fires on ordinary work and lowers the tokens a
session costs — without making the answers worse. It targets both what the agent
*writes* (chat prose, narration, summaries) and what the agent *pulls into context*
(file reads, tool output, re-derivation), because in a coding session the second is
the much larger cost.

Success looks like: the same task, done as well as before, for noticeably fewer
tokens, so subscription/rate limits are reached later.

## Why this shape

Most of the bill in a coding session is **input**: the conversation so far, every
file read, every tool result, re-sent on each turn. Trimming chat prose is the
smallest lever. The durable savings come from not pulling in what you don't need,
not re-reading what is already in context, and not echoing content back.

## Goals

- G1 Cut tokens per turn while holding answer correctness and completeness.
- G2 Change both output style and working habits (context discipline).
- G3 Cost almost nothing itself: a lean body, heavy material loaded on demand.
- G4 Be portable: plain `SKILL.md`, no hooks, plugins, or agent-specific syntax.
- G5 Be testable: measurable before/after, with a quality gate.

## Non-goals

- Not a hook, plugin, proxy, or runtime enforcement layer.
- Not prompt compression, model routing, caching, or context-window surgery.
- Not a "be terse" personality that strips needed detail.
- Not applied to code itself: code stays readable, comments stay where they earn
  their place, tests still get written and run.

## Anti-goals (failure even if tokens drop)

- Under-answering causes a follow-up, a re-explanation, or rework.
- Skipping a read the task actually needed, producing a wrong fix.
- Being terse where the explanation *is* the deliverable (teaching, debugging
  narrative, trade-off advice).
- Silent failures: an ambiguous task done wrong is cheaper per turn and far more
  expensive overall.

## Constraints

- Frontmatter: `name`, `description` only. Description starts "Use when...", states
  triggering conditions, never summarises the workflow.
- Body budget: SKILL.md ≤ ~600 words (~800 tokens) — it loads on every trigger.
- Reference file ≤ ~150 lines, loaded only when auditing/measuring.
- No destructive-action shortcuts: confirmations and safety warnings are never
  trimmed.
- Must not require any specific agent.

## Approaches considered

- **A. Style guide only** — trims preamble, restating, closing summaries. Near-zero
  risk, small savings. (Rejected: misses the dominant input cost.)
- **B. Context discipline only** — locate before loading, slice reads, no re-reads,
  no echo, subagents for broad exploration. Large savings, but leaves the visible
  chatter and its follow-up cost untouched. (Rejected as incomplete.)
- **C. Both, one lean skill, with an escalation rule** — chosen. Biggest savings,
  and the escalation rule is what protects quality.

## The design

One skill, three rule blocks plus one brake. Each rule is phrased as the shape the
output/turn should take, not as a list of prohibitions.

### 1. Answer first

State the answer/result in the first sentence, then only the detail the reader
needs to act. No preamble, no restating the request, no narration of tool calls, no
recap of what was just done, no "next steps you might want". Stop at done.

### 2. Work cheap (context discipline)

- Locate before loading: search/glob, then read the relevant slice — not the whole
  file by default.
- Read once. A file already in context stays read unless it changed.
- Don't echo file contents, diffs, or tool output back into prose; cite `path:line`.
- Filter long output at the source (head/tail/grep) instead of pulling it all in.
- Prefer targeted edits over rewriting whole files.
- Put findings and plans in a scratch file when they'd otherwise be repeated in
  chat or re-derived.
- Hand broad exploration to a subagent so its reading stays out of the main context.
- Keep the working set small: paste the relevant fragment, not the document.

### 3. Never cut

Correctness, the actual answer, working code, evidence (test/build output), required
caveats, safety and destructive-action confirmations, and anything the user
explicitly asked for.

### 4. Escalate to full detail when

- the user asks for an explanation, a walkthrough, or trade-offs;
- the decision is risky or irreversible;
- an ambiguity would cause rework;
- the reasoning itself is the deliverable (teaching, diagnosis, review).

Escalation is scoped to the part that needs it — the rest stays lean.

## Files

```
token-optimizer/
  SKILL.md                          # behaviour, ~550 words
  references/auditing-token-use.md  # measurement + pre-flight checklist, on demand
```

## Verification (TDD for skills)

Three scenarios, run on fresh subagents, with and without the skill:

1. **Output scenario** — "explain how X works in this codebase". Baseline usually
   produces preamble + restated request + unrequested summary.
2. **Context scenario** — a bug hunt in a repo where the naive path reads whole
   files, re-reads them, and echoes contents.
3. **Long-session scenario** — a multi-step task where baseline keeps restating
   state and re-pasting content.

Metrics per scenario: output word count, number of file reads, characters pulled
into context, files read more than once, follow-up questions needed. Quality gate:
an independent read of the answer checks correctness and completeness against the
baseline — savings only count if the answer holds.

RED: record baseline behaviour verbatim. GREEN: re-run with the skill. REFACTOR:
add counters for any rationalisation the skill fails to prevent.

## Deliverables and paths

- Source of truth: `D:\VIBECODINGPROJECTS\TokenOptimizer Skill\token-optimizer\`
- Design + test notes: `docs\` alongside it.
- Install: copy `token-optimizer\` into `C:\Users\oggyt\.agents\skills\` (covers
  OpenCode and other cross-runtime agents); optionally also `~\.claude\skills\`.
- Optional one-liner for a project's instructions file, for guaranteed always-on.

## Left to the builder

Exact wording and final word counts; the concrete test prompts and how to capture
the metrics; whether the always-on pointer is offered as a separate snippet.
