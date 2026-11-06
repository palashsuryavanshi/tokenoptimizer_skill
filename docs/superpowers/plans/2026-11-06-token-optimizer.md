# Token Optimizer Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `token-optimizer`, a portable agent skill that lowers tokens per turn by shaping both output and context habits, proven by before/after scenario runs that hold answer quality.

**Architecture:** A lean `SKILL.md` (≤600 words, four blocks: answer-first, work-cheap, never-cut, escalate) plus one on-demand reference on auditing spend. Behaviour is verified TDD-style: a planted-bug fixture repo, four pressure scenarios run on fresh subagents without the skill (RED), then with it (GREEN), then loopholes closed (REFACTOR). Savings only count if answers stay correct.

**Tech Stack:** Markdown skill files; Python 3.13 fixture app (pytest); PowerShell 7 measurement script; `subagent` tool for scenario runs.

**Spec:** `docs/2026-11-06-token-optimizer-design.md`

## Global Constraints

- Skill name: `token-optimizer` — lowercase letters, digits, hyphens only.
- `SKILL.md` frontmatter: `name` and `description` only, ≤1024 chars total.
- `description` starts with "Use when", is third person, ≤500 chars, names triggering conditions only — never summarises the workflow.
- `SKILL.md` body ≤600 words. Measure with `(Get-Content -Raw <file>).Split([char[]]" `n`r `t").Where({$_}).Count` — report the number in the task's notes.
- `references/auditing-token-use.md` ≤150 lines; referenced from `SKILL.md` as on-demand only, never inlined.
- No hooks, plugins, MCP config, or agent-specific syntax. Plain `SKILL.md` + Markdown.
- Every scenario result is recorded verbatim before it is summarised. No metric is estimated.
- Windows paths; run PowerShell from `D:\VIBECODINGPROJECTS\TokenOptimizer Skill`.
- Quality is a gate, not a trade: a run that saves tokens by giving a worse answer is a failure, not a saving.

## Review Focus

- **"Explain this properly"** — when the user asks for a walkthrough, the lean default must escalate; a truncated explanation is a failed run.
- **Irreversible actions** — confirmation prompts and destructive-action warnings must survive every trim.
- **Needed-but-ugly file** — the answer sometimes lives in the largest, noisiest file; "work cheap" must not become "skip the read".
- **Ambiguous request** — the cheapest-looking move is to guess; the correct move is one short question. Watch for silent guessing.
- **Changed file mid-session** — "don't re-read" must yield to "re-read if it changed", or the agent fixes stale code.

---

### Task 1: Test harness — fixture repo, scenarios, measurement

**Files:**
- Create: `.gitignore`
- Create: `tests/fixture/app/main.py`, `billing.py`, `reports.py`, `utils.py`
- Create: `tests/fixture/docs/architecture.md`, `tests/fixture/docs/changelog.md`
- Create: `tests/fixture/tests/test_billing.py`
- Create: `tests/fixture/repro.py`
- Create: `tests/fixture/README.md`
- Create: `tests/scenarios/01-explanation.md`, `02-bug-hunt.md`, `03-long-session.md`, `04-escalation.md`
- Create: `scripts/measure.ps1`
- Create: `tests/results/_template.md`

**Interfaces:**
- Produces: fixture root `tests/fixture/` with runnable `repro.py`; four scenario prompt files, each a complete user message; `scripts/measure.ps1` accepts `-Path <file>` and prints `words=<n> chars=<n>`; result files follow `_template.md`.

- [ ] **Step 1: Initialise the repo**

Run: `git init; git add -A; git commit -m "chore: init"` (skip the commit if empty)
Expected: repo at `D:\VIBECODINGPROJECTS\TokenOptimizer Skill\.git`

- [ ] **Step 2: Write the fixture app with the planted bug**

`tests/fixture/app/billing.py` must contain `def invoice_total(lines, tax_rate)` that computes `subtotal = sum(line["qty"] * line["unit_price"] for line in lines)` then `tax = math.floor(subtotal * tax_rate * 100) / 100`. The bug is truncation instead of half-up rounding. For `qty=3, unit_price=19.99, tax_rate=0.085` this yields `tax=5.09`, `total=65.06`; the correct tax is `5.10` and total `65.07`. Name the helper `_tax_for(subtotal, tax_rate)` so the fix is one function.

`main.py`, `reports.py`, `utils.py` are supporting modules, at least 80 lines each, with the bug reachable only through `billing.invoice_total`. Do not comment the bug. `architecture.md` and `changelog.md` are noise, at least 200 lines each; `changelog.md` mentions "rounding" once in an unrelated entry.

- [ ] **Step 3: Write the repro**

`tests/fixture/repro.py` prints exactly:
```
subtotal=59.97 tax=5.09 total=65.06 expected=65.07
```

- [ ] **Step 4: Verify the bug is real and findable**

Run: `python tests/fixture/repro.py`
Expected: the line above, with `total` and `expected` differing by one cent.
Run: `python -m pytest tests/fixture/tests -q`
Expected: PASS (the bug is behavioural, not covered by the existing tests).

- [ ] **Step 5: Write the four scenario prompts**

Each file is a self-contained user message. All start with: `IMPORTANT: This is real work in the repo at D:\VIBECODINGPROJECTS\TokenOptimizer Skill\tests\fixture. Act; do not describe what you would do.`

- `01-explanation.md`: "Explain how an invoice total is calculated here, start to finish, as if onboarding a new developer." (Baseline tempts preamble, restated request, unrequested summary.)
- `02-bug-hunt.md`: "Some customers say their invoice total is one cent low. Find the cause and fix it. The repro is `python repro.py`." (Baseline tempts reading whole files, echoing contents, re-reading.)
- `03-long-session.md`: a three-step task in one message: inspect `reports.py`, then `utils.py`, then make one small change to `reports.py`. Include the line: "Heads up — I edited `reports.py` while you were working, so check the current version before you change it." (Baseline tempts restating state, re-pasting file content, re-reading unchanged files; the correct run re-reads only the changed file.)
- `04-escalation.md`: "Give me a detailed walkthrough of how rounding works in this codebase, then change `tax_rate` handling so a misconfigured rate above 1.0 raises an error instead of silently doubling the invoice." (Tests escalation and a change worth a warning; the script also checks it does not silently guess what "misconfigured" means — `1.0` exactly, negatives, non-numeric — it should state the assumption or ask one short question.)

- [ ] **Step 6: Write the measurement script**

`scripts/measure.ps1` takes `-Path`, reads the file, and prints `words=<n> chars=<n>` where words are whitespace-split non-empty tokens. Verify it on a file with a known count.

- [ ] **Step 7: Write the results template**

`tests/results/_template.md` holds: scenario, run id, output words, chars, files read (list), duplicate reads, follow-up questions needed, quality verdict (correct / complete / regressions), notes.

- [ ] **Step 8: Commit**

```powershell
git add -A; git commit -m "test: add token-optimizer scenario harness and fixture"
```

---

### Task 2: RED — baseline behaviour without the skill

**Files:**
- Create: `tests/results/red-01.md`, `red-02.md`, `red-03.md`, `red-04.md`
- Create: `tests/results/red-summary.md`

**Interfaces:**
- Consumes: the four scenario files and `scripts/measure.ps1` from Task 1.
- Produces: `red-summary.md` with a metrics table and a verbatim failure log — the exact material Task 3 must address.

- [ ] **Step 1: Run scenario 1 without the skill**

Dispatch a fresh `general` subagent with the exact contents of `tests/scenarios/01-explanation.md` and nothing else. Do not mention skills, brevity, or tokens.
Run: `pwsh scripts/measure.ps1 -Path tests/results/red-01.md` after saving the response verbatim.
Expected: `red-01.md` contains the response, plus a telemetry line.

- [ ] **Step 2: Collect context telemetry**

Send one follow-up to the same subagent: "For measurement only, list every file you opened and every file you opened more than once." Record it in `red-01.md`.

- [ ] **Step 3: Run scenarios 2, 3, 4 without the skill**

Repeat Steps 1–2 for each, into `red-02.md`, `red-03.md`, `red-04.md`. Record four extra observations: did scenario 3 re-read `reports.py` after the edit notice (scenario 3's correct behaviour) or ignore it; did scenario 4 keep the full walkthrough; did scenario 4 warn about the `tax_rate > 1.0` change; did scenario 4 guess silently at what "misconfigured" means.

- [ ] **Step 4: Build the baseline table and failure log**

`red-summary.md`: a table with output words, chars, files read, duplicate reads, follow-ups, quality verdict per scenario. Below it, a **Failure log** quoting verbatim: preamble, restated request, unrequested summary, echoed file content, re-read explanation, missed escalation, missing warning, silent guess. Include at least one quote per failure type observed.

- [ ] **Step 5: Commit**

```powershell
git add -A; git commit -m "test: record RED baseline behaviour"
```

---

### Task 3: GREEN — write the skill and prove it

**Files:**
- Create: `token-optimizer/SKILL.md`
- Create: `tests/results/green-01.md`, `green-02.md`, `green-03.md`, `green-04.md`
- Create: `tests/results/green-summary.md`

**Interfaces:**
- Consumes: `red-summary.md` failure log.
- Produces: `SKILL.md` and a green table in the same shape as the red table, plus a quality verdict. Task 4 edits this file; Task 5 installs it.

- [ ] **Step 1: Write `SKILL.md`**

Frontmatter: `name: token-optimizer`; `description` names the triggers — starting any coding session or task, about to read or re-read files, explaining or summarising work, or when output or context is getting long. No workflow summary.

Body: four H2 blocks — **Answer first**, **Work cheap**, **Never cut**, **Escalate** — plus one closing line pointing at `references/auditing-token-use.md` as on-demand. Each rule is written as the shape the output should take; each item in the failure log from Task 2 gets exactly one rule that prevents it. No rule addresses a failure that was not observed.

- [ ] **Step 2: Verify the constraints**

Run: word count command from Global Constraints. Expected: ≤600.
Check: frontmatter has only `name` and `description`; description ≤500 chars and contains no "so that", "then", or other workflow summary.

- [ ] **Step 3: Run all four scenarios with the skill**

Dispatch a fresh subagent per scenario with: the scenario text, then `Follow this skill: <full SKILL.md body>`. Same tasks, same repo state (`git -C tests/fixture stash` must be clean before each run). Save to `green-NN.md` and collect telemetry as in Task 2.

- [ ] **Step 4: Compare against the baseline**

`green-summary.md` repeats the red table with a delta column and the quality verdict. Expected: scenario 4 keeps the full walkthrough, the warning, and an explicit statement of what "misconfigured" was taken to mean; scenario 3 re-reads the changed `reports.py` and not the unchanged `utils.py`; scenarios 1–3 drop preamble/echo/duplicate reads; no answer is less correct than baseline.

- [ ] **Step 5: Blind quality gate**

Dispatch a fresh subagent with the task, the red answer, and the green answer in randomised order, asking which is more correct and complete and whether either is missing anything required. Record the verdict in `green-summary.md`. Expected: green is equal or better; a "green is worse" verdict blocks progress until Task 4 fixes it.

- [ ] **Step 6: Commit**

```powershell
git add -A; git commit -m "feat: add token-optimizer skill with green verification"
```

---

### Task 4: REFACTOR — close observed loopholes

**Files:**
- Modify: `token-optimizer/SKILL.md`
- Create: `tests/results/refactor.md`

**Interfaces:**
- Consumes: gaps and rationalisations from `green-summary.md`.
- Produces: final `SKILL.md` that passes every scenario; `refactor.md` records what changed and why.

- [ ] **Step 1: List what still failed**

In `refactor.md`, quote each remaining violation verbatim and name the rule that should have prevented it. If nothing failed, write "none" and skip to Step 4 — no speculative edits.

- [ ] **Step 2: Add one counter per violation**

Edit only the block that owns the failure (answer-first, work-cheap, never-cut, escalate). Counters are specific ("ignore a file already read **unless it changed since**"), never generic ("be careful"). Keep the body ≤600 words; if a rule must be cut to fit, cut the least-observed failure.

- [ ] **Step 3: Re-run the failing scenarios**

Re-run only the scenarios that failed, with the updated skill, into `tests/results/refactor-NN.md`. Expected: the specific violation is gone.

- [ ] **Step 4: Re-check the quality gate**

Re-run the blind comparison for any scenario whose answer changed. Expected: equal or better. Record both verdicts in `refactor.md`.

- [ ] **Step 5: Commit**

```powershell
git add -A; git commit -m "fix: close token-optimizer loopholes found in testing"
```

---

### Task 5: Reference file, install, always-on pointer

**Files:**
- Create: `token-optimizer/references/auditing-token-use.md`
- Create: `docs/always-on-snippet.md`
- Modify: `token-optimizer/SKILL.md` (one pointer line, if not already present)
- Install: copy `token-optimizer\` to `C:\Users\oggyt\.agents\skills\token-optimizer\`

**Interfaces:**
- Consumes: final `SKILL.md`.
- Produces: installable skill folder; `docs/always-on-snippet.md` holding the optional one-liner for a project instructions file.

- [ ] **Step 1: Write the reference file**

≤150 lines: (a) a pre-flight checklist for a task — locate before loading, read once, no echo, filter output, targeted edits, scratch file for findings; (b) how to measure a session before/after (output words, files read, duplicate reads, follow-ups); (c) what to do when spend is still high — name the three biggest levers in order (context, reads, output). No rules duplicated from `SKILL.md`; it is the audit view, not a second copy.

- [ ] **Step 2: Verify it is on-demand**

Check: `SKILL.md` mentions the file once, in a line that says to load it when measuring or auditing. Check line count ≤150.

- [ ] **Step 3: Install**

```powershell
Copy-Item -Recurse -Force "token-optimizer" "C:\Users\oggyt\.agents\skills\token-optimizer"
```
Expected: `C:\Users\oggyt\.agents\skills\token-optimizer\SKILL.md` and `references\auditing-token-use.md` exist and match the source (compare hashes with `Get-FileHash`).

- [ ] **Step 4: Write the always-on snippet**

`docs/always-on-snippet.md`: three lines for a project instructions file, telling the agent the skill exists and to load it at session start. State plainly that this is optional and only needed where the agent does not auto-load by description.

- [ ] **Step 5: Final verification**

Run: word count on the installed `SKILL.md`. Expected: ≤600 and identical to source.
Run: `python tests/fixture/repro.py` after restoring the fixture. Expected: the baseline bug output (the fixture stays buggy; green runs happen on stashed copies).

- [ ] **Step 6: Commit**

```powershell
git add -A; git commit -m "feat: add audit reference, install skill, document always-on pointer"
```
