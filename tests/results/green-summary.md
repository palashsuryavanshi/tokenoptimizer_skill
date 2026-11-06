# GREEN summary — final skill (round 3)

Verification of the final `token-optimizer/SKILL.md` (578 words after the
portability edit; 581 at green-run time) against the RED
baseline. Round 3 is the run that counts; rounds 1 and 2 are recorded below for
the gate history. No scenario was re-run for this summary.

## Method

Output words and characters were measured with the Task 1 script, so the figures
include the four-backtick wrapper, exactly as the RED table did:

```text
powershell -NoProfile -File scripts\measure.ps1 -Path tests\results\green3-01.md
tests\results\green3-01.md words=785 chars=5698
tests\results\green3-02.md words=107 chars=841
tests\results\green3-03.md words=376 chars=3051
tests\results\green3-04.md words=647 chars=4745
```

Files read counts distinct repository source files the subject reported
inspecting. Excluded: the skill file, result files, directory listings, and
generated `__pycache__`/`.pyc` artifacts. The fixture contains 11 source files;
scenario 01's telemetry says "all 12" but names 10 and adds "directory listings",
so the count is 11 (the fixture total, consistent with "all"), not 12. Duplicate
reads counts repository files opened more than once unnecessarily by explicit
inspection; imports, test runs, newly created test files, and scenario 3's
user-mandated re-read of `reports.py` are excluded. Telemetry is self-reported.

Wrapper note: `gate-round3.md` quotes 783/105/374/645 and a 1907 total. Those
figures omit the two four-backtick wrapper tokens per file (8 in total). RED's
3047 includes the wrapper, so the like-for-like measured total is 1915. The
percentage saving is 37% either way.

## Metrics — round 3 (final skill)

| Scenario | Output words | Δ words | Output chars | Files read | Δ files | Duplicate reads | Δ dups | Follow-ups | Quality verdict |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 01 explanation | 785 | −872 | 5698 | 11 | 0 | 0 | −6 | 1 | Red better (narrow); accepted by ruling |
| 02 bug hunt | 107 | 0 | 841 | 11 | +1 | 4 | 0 | 1 | **Green better** |
| 03 long session | 376 | +8 | 3051 | 5 | −5 | 1 | +1 | 1 | **Green better** |
| 04 escalation | 647 | −268 | 4745 | 10 | 0 | 2 | +1 | 1 | **Green better** (narrow) |
| **Total** | **1915** | **−1132** | **14335** | **37** | **−4** | **7** | **−4** | **4** | 3 of 4 green |

Against RED: 3047 words / 20880 chars / 41 files / 11 duplicate reads. Overall
output saving is 1132 words (−37.2%) and 6545 chars (−31.3%).

## Where the skill does not save

- **Scenario 01 — input context neutral, not a regression.** The final run read
  11 repo files, the same as RED. Telemetry's "all 12" is off by one: it names 10
  files and adds "directory listings", while the fixture holds 11 source files.
  Duplicate reads fell from 6 to 0. The 52.6% output saving here is still not an
  input saving.
- **Scenario 02 — word-neutral.** 107 words before and after; the win is quality
  (regression test and before/after evidence), not length. It read one more repo
  file than RED (11 vs 10).
- **Scenario 03 — slightly longer.** 376 words against RED's 368 (+8, +2.2%; the
  gate's wrapper-free figures are 374 vs 368, +6). Verification and the added
  test cost a little prose. It re-opened `app/main.py` while editing, so duplicate
  reads rose from 0 to 1; the new `tests/test_reports.py` is excluded as a created
  file. It read five fewer files overall (5 vs 10), which is the real context
  saving.
- **Scenario 04 — duplicate reads up.** Files read are unchanged at 10, but
  duplicates rose from 1 to 2 (`app/billing.py` three reads, `app/main.py` two)
  while output fell 29.3%.

No context regression is hidden: files read improved overall (41 → 37) and
duplicates improved (11 → 7), but the improvement is concentrated in scenario
03's five-file drop and scenario 01's duplicate-read drop, not uniform.

## Quality verdicts (gate-round3.md)

### 01 explanation — red better, narrow; accepted

Both answers are accurate on the arithmetic. Green omits optional onboarding
traps: displayed/CSV cells are each rounded from the raw float so subtotal + tax
need not equal the shown total; module-boundary guidance; and the warning that
tests do not pin truncation. These are depth, not errors. The recorded ruling
accepts the gap: chasing it would add words to every session to buy optional
caveats in one scenario, with 19 words of ceiling headroom left. Cost if wrong: a
new developer misses display-level reconciliation until they hit it.

### 02 bug hunt — green better

Cause, change, and evidence are all present. Green shows a before/after repro
(`65.06` → `65.07`) plus a CLI check; RED shows only the post-fix state. Code was
verified independently: `total=65.07 expected=65.07`, 15 tests passing.

### 03 long session — green better

Green verified against the post-edit file with exact lines, explained the
rate/tax derivation, and confirmed the rename end to end (pytest plus CLI
header/row). RED left the CLI export path broken. Green exceeded the literal
"one small change to reports.py" scope by fixing `app/main.py` and adding tests,
and disclosed it — the correct behaviour. Code verified: `app/main.py:51` calls
`reports.export_csv_rows`.

### 04 escalation — green better, narrow

Green gave verifiable test evidence (before `300.0`, after `ValueError`,
`21 passed`), line-precise citations, and an explicit "8.5 is now invalid"
behaviour-change note. Missing: a docs/changelog update and a transcript of the
CLI exit code. Code verified: `command_summary` now passes `args.tax_rate` to
`billing.invoice_rows`.

## Blind gate history

| Round | Green wins | What changed for the next round |
| --- | ---: | --- |
| 1 | 1/4 (scenario 03) | "Work cheap" had been read as "do less work" and "answer first" as "drop evidence". Added: work is not prose, search is not answering, evidence is part of the answer, safe caveats are not detail, scope must not block finishing. |
| 2 | 1/4 (scenario 02) | Still missed call-site breakage after the user's rename (03), left the CLI and direct-caller paths unguarded (04), and gave a narrow explanation (01). Added: check call sites and imports after any change, guard where the value enters and close every path including the CLI, explanations cover the whole path and traps. |
| 3 | 3/4 (02, 03, 04) | Scenario 01 remains a narrow loss on optional onboarding depth; accepted by ruling. No further change. |

## What this proves, and what it does not

**Proves:** under blind judging, the final skill matches or beats the baseline on
the three tasks where earlier rounds were cutting substance (02, 03, 04), with
the code changes independently re-verified. Overall output falls from 3047 to
1915 words (−37%) and 20880 to 14335 chars (−31%), while duplicate reads fall
from 11 to 7 and files read from 41 to 37. The one quality loss is a narrow,
ruled-on depth gap, not a wrong or incomplete answer.

**Does not prove:** a saving on short tasks — scenario 02 is word-neutral at 107
words. It does not prove an input-context saving on explanation tasks — scenario
01 reads 11 files, the same as RED, so its saving is output only. Scenario 03 is
slightly longer (+8 words) and adds one duplicate open, so the win there is
quality and fewer first reads, not prose. Scenario 02 reads one more file than
RED. Telemetry is self-reported, and the summary compares one run per scenario.
