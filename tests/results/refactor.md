# Refactor record — what the blind gate broke, and what was closed

The green run failed the blind quality gate twice before it passed. This file is
the Task 4 record of those two refactors: the violations quoted from the gate,
the counter added for each, the re-runs, and the final blind verdict.

Sources, in precedence order:

1. `gate-round1.md`, `gate-round2.md`, `gate-round3.md` — the verdicts. These are
   the source of record for every quote and ruling below.
2. `tests/results/green2-*.md` and `green3-*.md` — the re-run transcripts.
3. `green-summary.md` — derived metrics. Where it disagrees with a gate file, the
   disagreement is noted rather than smoothed over.
4. `git show be1d26e`, `e859745`, `6d6d1e2` — the exact edits.

Skill size across the refactor: 392 words (original) → 546 (`be1d26e`) → 581
(`e859745`) → 578 (`6d6d1e2`). The body stayed under the 600-word ceiling the
whole time, so no rule had to be cut to fit.

**Which bytes were gated.** Round 3 judged the skill at `e859745` (581 words).
`6d6d1e2` then changed one rule line from shell-specific filters (`head`, `tail`,
`grep`) to "request only needed lines or fields", plus two summary paragraphs. The
final 578-word file was not re-gated; the only behavioural text changed is that one
line, and the rule is semantically the same. This is a small, disclosed
verification gap, not a verdict change.

## Step 1 — violations observed in rounds 1 and 2

### Round 1 — 1/4 green (scenario 03 only)

**Scenario 01 (red better)** — the answer was under-researched and then asserted
something false:

> Missing in green: the real `--tax-rate` bug — `command_summary` never passes
> `args.tax_rate`, so `summary` and `report` can disagree.

> Green asserted something false: "every printed amount comes from these two
> billing functions... which keeps the monthly report and the summary in
> agreement" — contradicted by the `--tax-rate` case.

> Red was the only answer that named the rounding-location issue (tax truncated
> separately, total never rounded) as a distinct cause.

Rule that should have prevented it: search may locate, but a claim about how a
file is used requires reading it; and an unverified claim must be stated as such
or left out. Neither rule existed at commit `41e97b7` — the skill's only reading
rule was "Locate before loading", and "Never cut" treated evidence as test or
build output.

**Scenario 02 (red better)** — the evidence and test were cut:

> Missing in green: no regression test (14 tests = pre-existing only), no
> changelog entry, and the tax arithmetic (5.09745 → 5.09 vs 5.10) implied rather
> than shown.

Rule that should have prevented it: "work cheap" saves prose and needless reads,
never the work a task needs; a fix is evidenced by the failing value before and
the passing value after, from a command or test.

**Scenario 03 (green won)** — a minor miss inside a win:

> Missing in green: indirect helper deps (`pad`→`truncate`,
> `normalize_customer_name`→`collapse_spaces`) beyond `collapse_spaces`.

Rule that should have prevented it: when the answer depends on how code is used —
call sites, imports, side effects — read the file rather than reasoning from the
names.

**Scenario 04 (red better)** — the admitted hole was documented, not closed:

> Missing in green: it closed no gap for the CLI path it admits is broken —
> `--tax-rate 1.5 summary` still silently ignores the flag, so a rate above 1.0
> does not raise there. Also no docs/changelog update, no guard against
> NaN/inf/non-numeric.

> Green only documented that hole as a caveat.

Rule that should have prevented it: the request defines the behaviour, not a file
list; every path the behaviour passes through must be fixed or explicitly
reported.

### Round 2 — 1/4 green (scenario 02 only)

**Scenario 03 (red better)** — the user's own rename broke a call site:

> "The user's mid-task rename `csv_rows` → `export_csv_rows` ... A never notices
> the rename, though both correctly rename the CSV column."

> Missing in green: that `app/main.py` still calls `reports.csv_rows`, so
> `export` raises `AttributeError`. Red caught the regression caused by the
> concurrent edit; green did not.

> Cause: nothing in the skill asks the agent to check the call sites of what
> changed — the user's change included.

Rule that should have prevented it: after any change — yours or the user's —
check the call sites and imports of what changed.

**Scenario 04 (red better)** — same class of failure, now at the entry point:

> Missing in green: no guard on `invoice_total` for direct callers, no mention
> that `command_summary` ignores `--tax-rate` (the CLI bypass red fixes), no
> explicit statement that floor rounding is unchanged and the repro still shows
> 65.06 vs 65.07.

> Cause: the "request defines the behaviour" line did not say to apply a guard
> where the value enters, or to close every path the behaviour passes through.

Rule that should have prevented it: guard where the value enters, and close every
path — including the CLI — or report each broken path.

**Scenario 01 (narrower loss)** — accuracy was fixed, depth was not:

> Missing in green: that `--tax-rate` must precede the subcommand, banker's
> rounding inside `apply_discount`, an explicit demonstration that formatted
> columns need not sum, and floor on negative subtotals.

> These are onboarding traps rather than errors in the calculation itself.

Rule that should have prevented it: when an explanation is the deliverable, cover
how it is invoked, the whole path, and the traps a newcomer hits.

### One complaint deliberately not countered

Both round 1 and round 3 flagged a missing changelog/docs update in scenario 04.
The refactor did not add a "write a changelog" rule; line 32 instead says "Keep
unrelated docs out of the diff", and line 46 requires disclosing a breaking
change. Round 3 still lists "no docs/changelog update" as missing, yet green won
that scenario narrowly. This is a judge preference the skill chose not to buy, not
an unnoticed loophole.

## Step 2 — the counter added for each, by owning block

Counters are quoted from the final `token-optimizer/SKILL.md` with their line
numbers. "Covers" names the Step 1 violations above.

### Answer first

- **line 12** — "Evidence is part of the answer, not detail. For a fix, state the
  cause, what changed, and proof it works: the failing value before, the passing
  value after, with the command or test that produced them. Name every file you
  changed." Covers R1-02 (missing before/after evidence).

### Work cheap

- **line 18** — "Save prose and needless reads — never the work a task needs. Add
  the regression test a change warrants, run it, show the result, and finish the
  behaviour the user asked for." Covers R1-02 (no regression test; test counts
  unchanged).
- **line 21** — "Search locates; it does not answer. If the answer depends on how
  a file is used — exports, call sites, side effects — read it." Covers R1-01
  (searched `reports.py` then claimed agreement) and R1-03 (helper deps inferred
  from names).
- **line 30** — "After any change — yours or the user's — check the call sites
  and imports of what changed; fix or report the breakage." Covers R2-03 (the
  user's `csv_rows` rename).
- **line 32** — "The request defines the behaviour, not a file list. Apply a
  guard or behaviour change where the value enters, and close every path the
  behaviour passes through, including the CLI; fix or report each broken path.
  Keep unrelated docs out of the diff, and name any file you change beyond the
  request." Covers R1-04 (CLI flag silently ignored) and R2-04 (direct caller
  unguarded, CLI bypass).

### Never cut

- **line 38** — "Caveats that make the answer safe are not detail: shared state
  changing beyond what the user named, a breaking change for existing data or
  callers, and any claim you have not verified. State it or leave the claim out —
  never guess." Covers R1-01's false claim.

### Escalate

- **line 44** — "When an explanation is the deliverable, cover how it is invoked,
  the whole path, and the traps a newcomer hits — not only the happy path."
  Covers R2-01 (optional traps, invocation order, module boundaries).

No counter was added outside these four blocks, and no block outside them was
touched. The four blocks are the ones the brief names (answer-first, work-cheap,
never-cut, escalate).

## Step 3 — the re-runs

Each round re-ran all four scenarios, not only the failing ones, so a fix in one
scenario could not silently regress another. Each round also re-ran the blind
comparison.

| Phase | Transcripts | What it fixed |
|---|---|---|
| Round 2 (`be1d26e`, 546 words) | `green2-01.md` … `green2-04.md` | Closed the evidence/test gap. Scenario 02 became a green win: "the regression test and before/after evidence now match red" (`gate-round2.md`). The false agreement claim in 01 was gone: "Both are accurate on the core arithmetic" (`gate-round2.md`). Scenario 04 remained a substantive loss. |
| Round 3 (`e859745`, 581 words) | `green3-01.md` … `green3-04.md` | Closed the call-site and entry-point gaps. Scenario 03 became a green win after `app/main.py:51` was fixed to call `reports.export_csv_rows`; scenario 04 became a green win after `invoice_total` was guarded and `command_summary` passed `args.tax_rate`. |

Plainly: **round 2 closed the evidence and test gaps; round 3 closed the
call-site and entry-point gaps.** Round 3 also added the explanation-completeness
line, but that did not close scenario 01.

**Naming deviation.** The brief asks for re-runs named `refactor-NN.md`. The
controller wrote `green2-*.md` and `green3-*.md` instead, to keep the phase naming
used by `red-*` and `green-*`. No `refactor-NN.md` exists; the transcripts are
equivalent and are the files the gate judged.

## Step 4 — the final blind gate (3/4)

`gate-round3.md`, same blind method as round 1 (fresh judges, A/B order
randomised):

| Scenario | Verdict | Reason recorded |
|---|---|---|
| 01 explanation | **red better** | Both accurate; green omits optional traps. |
| 02 bug hunt | **green better** | "Nothing required — cause, change, and evidence are all present." |
| 03 long session | **green better** | Exact post-edit lines, rate/tax derivation, rename verified end to end; red left the CLI export path broken. |
| 04 escalation | **green better (narrow)** | Before `300.0` → after `ValueError`, `21 passed`, line-precise citations, explicit "8.5 is now invalid" note. |

Code was re-verified after the runs: scenario 02's repro is `total=65.07
expected=65.07` with 15 tests passing; scenario 03's `app/main.py:51` calls
`reports.export_csv_rows`; scenario 04's `command_summary` passes `args.tax_rate`
to `billing.invoice_rows`.

### Scenario 01 ruling and cost

The gate accepted the loss:

> **Ruling: accept.** The remaining gap is extra depth on one explanation task,
> not a wrong or incomplete answer to what was asked. Chasing it would add words
> to every session to buy optional caveats in one scenario, and the skill is
> already 19 words under its ceiling. Cost if wrong: a new developer onboarding
> from this answer misses display-level reconciliation until they hit it.

The "19 words under its ceiling" refers to the 581-word gated version; the final
file is 578, i.e. 22 under. The cost is unchanged and is the honest price of the
ruling: a newcomer may not learn that displayed/CSV cells are each rounded from
the raw float, so subtotal + tax need not equal the shown total and the footer can
disagree with the visible column sum.

## Step 5 — round summary

| Round | Green wins | What changed | What it fixed |
|---|---:|---|---|
| 1 | 1/4 (03) | Baseline skill. | — |
| 2 | 1/4 (02) | `be1d26e`: evidence includes before/after proof; work cheap never cuts the test; search is not reading; never-cut caveats include unverified claims; the request defines behaviour, not file list. | Evidence and test gaps. 02 turned green; 01's false claim disappeared; 01 narrowed, 04 remained a substantive loss. |
| 3 | 3/4 (02, 03, 04) | `e859745`: check call sites and imports after any change, including the user's; guard where the value enters and close every path including the CLI; explanations cover invocation, whole path, and newcomer traps. | Call-site and entry-point gaps. 03 and 04 turned green; 01 remained a narrow loss. |

## What the refactor did NOT fix

- **Scenario 01 is still a loss**, narrow and ruled-on: the answer omits
  display-level rounding traps, module-boundary guidance, and the warning that
  tests do not pin truncation. It is accurate on the arithmetic and answers what
  was asked. Chasing it would cost words in every session.
- **Scenario 02 is word-neutral.** 107 words before and after (measured); the win
  is the regression test and before/after evidence, and it read one more repo file
  than red (11 vs 10). No prose saving.
- **Scenario 03 is not word-neutral.** It is slightly longer: 376 vs 368 measured
  (+8), 374 vs 368 by the gate's wrapper-free count (+6). The win is quality and
  five fewer first reads (5 vs 10), with one extra duplicate read. The task
  framing that "02 and 03 are word-neutral" is only true for 02; the file is the
  source.
- **Scenario 04 is narrow and still misses a changelog** and a CLI exit-code
  transcript. Duplicate reads rose from 1 to 2 while output fell 29.3%.
- **Input context did not improve uniformly.** Files read fell 41 → 37 overall and
  duplicate reads 11 → 7, but the gain is concentrated in scenario 03's five-file
  drop and scenario 01's duplicate-read drop.
- **The final 578-word bytes were not re-gated** after `6d6d1e2`; only the
  platform-neutral output-filtering line changed.

## Verification performed for this record

- Checked all three refactor commits and their diffs against the claims above
  (`be1d26e` 9+/2−, `e859745` 10+/6−, `6d6d1e2` one rule line plus summary).
- Measured word counts with `scripts/measure.ps1` and
  `Measure-Object -Word`: 392 / 546 / 581 / 578.
- Re-read every quoted passage in the gate files; quotes are verbatim.
- **Count disagreement, noted:** `gate-round3.md` reports 783/105/374/645 and a
  1907 total; the measured files are 785/107/376/647, total 1915. The gate
  subtracts the two wrapper tokens from the green3 files but not from red, so its
  per-scenario deltas are 2 words low. The verdicts and the ~37% saving are
  unaffected. `green-summary.md` measures both sides consistently, which is why it
  says 1915.
- **Other disagreement, noted:** the gate's scenario-01 ruling counts "19 words
  under its ceiling" at the gated 581 words; the final file is 578 (22 under).
