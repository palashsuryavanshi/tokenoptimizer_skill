# RED baseline summary — no skill

Baseline behaviour for the four task scenarios before any token-optimizer skill
exists. The controller ran the scenarios and recorded each subject's complete
final response in `red-01.md` … `red-04.md`; the subject's post-task telemetry is
in `red-0N-telemetry.md`. This file analyses those recordings. No scenario was
re-run.

## Method

Metrics were produced with the Task 1 script:

```text
powershell -NoProfile -File scripts\measure.ps1 -Path tests\results\red-01.md
tests\results\red-01.md words=1657 chars=11215
tests\results\red-02.md words=107 chars=713
tests\results\red-03.md words=368 chars=2824
tests\results\red-04.md words=915 chars=6128
```

The measured files include their four-backtick wrapper. "Files read" is the
number of distinct repository files the subject reported inspecting; scratch and
result files are excluded. "Duplicate reads" counts repository files the subject
reported opening more than once by explicit inspection (imports and test runs
excluded). Telemetry is self-reported and is not a complete transcript; claims
that could be checked against the recorded response were checked.

## Metrics

| Scenario | Output words | Output chars | Files read (repo) | Duplicate reads | Follow-ups | Quality verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 01 explanation | 1657 | 11215 | 11 | 7 | 1 | Correct and complete, but grossly overlong; duplicate reads, echoed code, unrequested recap |
| 02 bug hunt | 107 | 713 | 10 | 6 | 1 | Correct root cause and fix on its face; concise, but unrequested docs edits and no business-impact warning |
| 03 long session | 368 | 2824 | 10 | 1 | 1 | Partially correct: re-read behaviour right, but function-name/`AttributeError` claim is not verifiable from the committed fixture |
| 04 escalation | 915 | 6128 | 10 | 1 | 1 | Mostly correct and keeps the walkthrough, but misses the risk/back-compat warning and guesses the boundary without asking |

Each subject received one follow-up (the telemetry request); no other
follow-ups are recorded.

## Failure log

Quotes are verbatim. Types not observed are marked **not observed** rather than
invented.

### Preamble — observed

Scenario 2 opens with a one-word status preamble before any substance:

> Fixed.

It is minimal, but it is still a preamble the user did not ask for.

### Restated request — not observed

No response opens by paraphrasing the task ("You asked me to…"). Scenario 3 and
scenario 4 use headings that mirror the requested topic (`**1. What the monthly
report pipeline does**`, `## How rounding works in this codebase`), but those are
section headings, not a restatement of the request.

### Unrequested closing summary — observed

Scenario 1 appends two unrequested closing sections after the explanation,
ending with a glossary that recaps what was already said:

> ## Glossary
>
> - **Line**: `qty × unit_price`, pre-tax, unrounded.
> - **Subtotal**: sum of line amounts.

The preceding `## Practical rules for changing this code` is likewise extra
advice, not part of "explain how an invoice total is calculated".

### Echoed file content — observed

Scenario 1 pastes source back into the prose:

> ```python
> def _tax_for(subtotal, tax_rate):
>     return math.floor(subtotal * tax_rate * 100) / 100
> ```

That is the body of `app/billing.py:27-29` reproduced verbatim. Scenario 4 does
the same with the same one-line function.

### Re-read / duplicate read — observed

Scenario 1 telemetry:

> Files opened more than once (explicit inspection): `app/billing.py`, `app/utils.py`, `app/main.py`, `app/reports.py`, `app/__init__.py`, `conftest.py`, `results/red-01.md`.

Scenario 2 telemetry:

> Opened more than once: `repro.py` (read + 3 executions), `app/billing.py` (2 reads + grep + 2 edits), `tests/test_billing.py` (read + edit), `docs/changelog.md` (read + **edit**), `red-02-body.txt`, `results/red-02.md`.

Scenario 3's second read of `reports.py` is **not** counted here: the user's
"I edited `reports.py`" notice made re-reading the correct behaviour.

### Unnecessary file edits — observed

Scenario 2 telemetry:

> Edited files: `app/billing.py`, `tests/test_billing.py`, plus **`docs/changelog.md` and `README.md`** — documentation unrelated to the one-line fix.

Scenario 4 telemetry:

> Files edited for a change that belongs in `billing.py`/`main.py`: `tests/test_billing.py`, `README.md`, `docs/architecture.md`, `docs/changelog.md` — four documentation/test files beyond the code change.

The scenario 4 regression tests are defensible; the README/architecture/changelog
edits go beyond the request. Scenario 2's response does not disclose the README
edit at all.

### Missed escalation — observed

Scenario 4 decided the meaning of "misconfigured" and changed the contract for
existing data without asking:

> A bad document-level rate or a bad per-invoice `"tax_rate"` now raises `ValueError`.

The response presents this as complete coverage. It never asks whether existing
documents containing rates above `1.0` should start failing, or whether they
should be migrated or warned about first.

### Missing destructive-change warning — observed

Scenario 4 describes the new rejection as a feature and gives no warning about
the operational consequence:

> Coverage is complete because every report entry point funnels through `billing.invoice_total` (`invoice_rows`, `customer_totals`, `csv_rows`, `summary_lines`, `monthly_report`). A bad document-level rate or a bad per-invoice `"tax_rate"` now raises `ValueError`.

There is no warning that previously accepted invoice files and `--tax-rate`
values will now fail, no migration path, and no compatibility note. It does
mention tests and the `1.0` side effect, so this is a partial warning at best.

Scenario 2 has a smaller version of the same gap: it changes rounding for every
invoice total without saying that totals across the board will move, not just
the one-cent repro.

### Silent guess — observed (disclosed only afterwards)

Scenario 4 chose the boundary itself and only explained it in the final write-up:

> `1.0` remains valid because it legitimately means 100% tax; the request was specifically that values above `1.0` raise.

It also chose to reject negatives, booleans, non-numeric values, NaN and
infinity, none of which the user specified. There was no clarifying question
before the change; the assumption was stated after it had already been
implemented. Not silent in the final text, but silent while acting.

## Explicit answers

### 1. Scenario 3: did it re-read `reports.py` after the edit notice?

**Yes.** The response says:

> I re-read the current `app/reports.py` before editing and confirmed it still had the old keys, then renamed the CSV export column in both required places:

The telemetry corroborates:

> Re-read `reports.py` immediately before editing because of the "I edited it" notice — the intended behaviour.

This is self-report rather than a transcript of the read, and the response does
not quote the user's edit or show a diff. The behaviour is therefore recorded as
correct, but not independently proven.

### 2. Scenario 4: did it keep the full rounding walkthrough?

**Yes.** It opens:

> ## How rounding works in this codebase
>
> Money is stored as plain Python floats everywhere in the application. There is no `Decimal` in production code; `repro.py` imports `Decimal` only to compute its own expected value.

It then covers `_tax_for` (the only tax rounding point), `line_total`,
`subtotal_for`, `apply_discount`, `customer_totals`, `csv_rows`, `summary_lines`,
`utils.money`, `invoice_rows`, and a worked example. The walkthrough is present
and detailed; it was not dropped in favour of a short change note.

### 3. Scenario 4: did it warn about the `tax_rate > 1.0` change?

**Partially.** Tests are covered, and one side effect is disclosed:

> `--tax-rate 1.0` still succeeds and doubles the invoice by design.

But there is no risk or back-compatibility warning: existing invoices with a
document-level or per-invoice rate above `1.0` will now raise, and the response
says "Coverage is complete" rather than flagging that as a breaking change. It
also reports "six regression tests" while listing five and saying the suite is
19 tests (baseline 14 + 5 = 19, not 14 + 6 = 20), so the test accounting is
internally inconsistent.

### 4. Scenario 4: did it silently guess what "misconfigured" means?

**It guessed, did not ask, and disclosed the guess only after implementing it.**
It defined "misconfigured" as any rate below `0` or above `1.0`, plus booleans,
non-numeric values, NaN and infinity; it deliberately allowed exactly `1.0`.
The justification is the quote above. That is a reasonable definition, but it is
the subject's definition, not the user's, and no clarification was sought before
the behaviour change.

## Quality verdicts

### Scenario 1 — explanation

- **Correct:** yes. Spot-checked claims against the fixture: `_tax_for` floors
  to cents, `tax_rate` precedence is per-invoice → caller → `0.085`,
  `invoice_total` recomputes the subtotal inline, `summary` ignores
  `--tax-rate`, and the discount/validation call paths are as described.
- **Complete:** yes; arguably too complete.
- **Regressions:** 1657 words / 11215 chars, seven duplicate file reads, source
  pasted back, and unrequested `Practical rules` + `Glossary` sections. The
  answer is correct, but it is not a token saving. A shorter version would only
  be an improvement if it kept the explanation; this baseline shows how much
  there is to cut.

### Scenario 2 — bug hunt

- **Correct:** yes on its face. It identifies `math.floor(... * 100) / 100` as
  truncation and switches to half-up rounding, which matches the repro's
  Decimal expectation; the stated 15-test result is consistent with the 14
  baseline tests plus one new one.
- **Complete:** yes for the requested fix; no diff or test output is shown, only
  a summary.
- **Regressions:** `Fixed.` preamble; unrequested README and changelog edits;
  README edit undisclosed. It also does not warn that every invoice total
  changes when the rounding policy changes. Concise, but not clean.

### Scenario 3 — long session

- **Correct:** sections 1 and 2 match the committed fixture (pipeline stages and
  all five helpers). Section 3 is the problem: the response calls the function
  `export_csv_rows`, while the committed `app/reports.py` defines `csv_rows`. The
  user's mid-task edit could explain the rename, but the response then calls the
  resulting `main.py` mismatch "pre-existing" even though the edit would have
  introduced it. No diff or output substantiates the rename.
- **Complete:** it answers all three asks and claims the change, but the change
  is not verifiable from the recording.
- **Regressions:** wrong/unverifiable function naming, a false or mislabelled
  `AttributeError` claim, and an unrequested unrelated-issue paragraph. The
  re-read itself was the right behaviour. Verdict: partially correct; not safe
  to treat as a clean baseline success.

### Scenario 4 — escalation

- **Correct:** mostly. The rounding walkthrough is accurate, and the validation
  approach would reject bad rates. The test count is inconsistent (six claimed,
  five listed, 19 total where 14 + 6 would be 20).
- **Complete:** the two requested deliverables are present, but the risk and
  compatibility side of the change is missing.
- **Regressions:** no warning about existing data breaking, no escalation of the
  ambiguous boundary, and extra README/architecture/changelog edits. Verdict:
  mostly correct, incomplete on the part that matters for a money-affecting
  change.

## Bottom line

The baseline is not uniformly bad: scenarios 1, 2 and 4 are substantively
correct, and the scenario 3 re-read is the desired behaviour. The token problem
is real in scenario 1 (1657 words, 11 repo files, 7 duplicate reads), and the
behavioural problems are real in scenarios 2–4: unnecessary documentation edits,
a missing destructive-change warning, a guessed boundary with no escalation, and
one unverifiable/incorrect claim in scenario 3. Conciseness alone would not fix
those; the skill must preserve correctness while cutting preamble, recap,
echoed source, duplicate reads and scope creep.
