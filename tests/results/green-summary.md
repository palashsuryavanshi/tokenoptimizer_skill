# GREEN summary — final skill (gate-final)

Verification of the final `token-optimizer/SKILL.md` — 590 words at `b0cf45a`
(path-scope multi-path sentence restored there; all other rules are the
595-word version from `0bacca2`) — against the RED baseline. Scenarios 01–03
ran on the 595-word bytes; only the path-scope sentence changed for `b0cf45a`,
and scenario 04 was re-run on the final bytes: `green5-04` is the gated final.
Rounds 1–3 are kept below as secondary history; they are superseded by this
gate. Scenario 01's re-gate landed (`green4-01`) and is recorded here — there
is no pending re-gate.

## Method

Output words and characters were measured with the Task 1 script, one command
per file, so the figures include the four-backtick wrapper, exactly as the RED
table did:

```text
powershell -NoProfile -File scripts\measure.ps1 -Path tests\results\green4-01.md
words=789 chars=5543

powershell -NoProfile -File scripts\measure.ps1 -Path tests\results\green4-02.md
words=135 chars=1082

powershell -NoProfile -File scripts\measure.ps1 -Path tests\results\green4-03.md
words=529 chars=4049

powershell -NoProfile -File scripts\measure.ps1 -Path tests\results\green5-04.md
words=848 chars=5910
```

Wrapper note: the headline totals quote wrapper-free green words (789−2,
135−2, 529−2, 848−2 = 787+133+527+846 = 2293) against RED's wrapper-inclusive
3047, the same convention gate-round3 used. Like-for-like measured (both
sides, wrapper included): green 2301 vs red 3047 (−24.5%); wrapper-free red
3039 vs green 2293 (−24.6%). RED's wrapper-free per-file figures are
1655/105/366/913. The previously quoted −37.2% belonged to the 581-word skill
(round 3) and does not describe the final skill.

No telemetry files were recorded for the `green4-*`/`green5-04` runs, so
input-context metrics (files read, duplicate reads) are not available for the
final runs and no input-context saving is claimed for them. The round-3
input-context figures appear in the history section below and are not carried
into the final table. Characters pulled into context — the design's input
metric — was not captured in any of these runs; the saved files are responses,
not host transcripts. Output chars is the recorded answer-length metric; it is
not an input measure.

## Metrics — final skill

| Scenario | Run file | Words (wrapper-free) | Chars (measured) | Δ words vs red | Quality verdict | Winner | Skill bytes |
| --- | --- | ---: | ---: | ---: | --- | --- | ---: |
| 01 explanation | green4-01.md | 787 | 5543 | −870 (−52.5%) | Red better — accepted loss | red | 595 |
| 02 bug hunt | green4-02.md | 133 | 1082 | +26 (+24.3%) | **Green better** | green4 | 595 |
| 03 long session | green4-03.md | 527 | 4049 | +159 (+43.2%) | **Green better** | green4 | 595 |
| 04 escalation | green5-04.md | 846 | 5910 | −69 (−7.5%) | **Green better** | green5 | 590 |
| **Total** | | **2293** | **16584** | **−754 (−24.8%)** | 3 of 4 green | | |

Against RED: 3047 words / 20880 chars. Overall output saving is 754 words
(−24.8%) and 4296 chars (−20.6%). Red per-file words: 1657 / 107 / 368 /
915.

## Where the skill does not save

- **Scenario 01 — quality loss, accepted.** Red is broader on optional
  onboarding traps; green is more accurate on the report layer's duplicated
  recomputation. Accepted as a depth loss, not an error; see gate-final.md
  for the ruling and its cost.
- **Scenario 02 — longer.** 133 words vs RED's 107 (+26, +24.3%). The win is
  before/after repro evidence and exact location, not length.
- **Scenario 03 — longer.** 527 words vs RED's 368 (+159, +43.2%). The win is
  scope control (CSV rename only, printed table header preserved) and end-to-end
  proof; verification prose costs length.
- **Scenario 04 — modest saving.** 846 words vs RED's 915 (−69, −7.5%) after
  the re-run on the restored 590-word bytes; the 595-word run's narrow loss is
  recorded in gate-final.md.
- No input-context saving is shown for the final runs: telemetry was not
  recorded for them. Round 3's input figures (files read 36 vs 41, duplicates
  7 vs 11) are the last measured input-side numbers and are kept as history.

## Quality verdicts (gate-final.md)

### 01 explanation — red better; accepted loss

Green is more accurate about the report layer's duplicated recomputation
(`summary_lines` recomputes subtotal and total from raw floats rather than
summing the table cells; three 1 × $0.333 invoices show 0.35 per total cell
but a $1.06 footer — verified in the answer). Red is broader on optional
onboarding traps: display-level reconciliation depth, module-boundary guidance,
and the warning that tests do not pin truncation. These are depth, not errors.
The ruling accepts the gap: cost is a newcomer onboarding from the green answer
missing display-level reconciliation and module-boundary guidance; the green
answer was still accurate where the baseline was not. Red is 1657 words vs
green's 787.

### 02 bug hunt — green better

Cause, change, and evidence are all present. Green shows a before/after repro
(`5.09/65.06` → `5.10/65.07`), names the exact location (`app/billing.py:29`,
`math.floor` → `Decimal` half-up), and states the blast radius (`invoice_rows`,
`reports.csv_rows`, `reports.summary_lines`, `main.py` all inherit the fix);
`pytest -q` → 15 passed. RED shows only the post-fix state.

### 03 long session — green better

Green scoped the rename to the CSV export (`CSV_COLUMNS`, `export_csv_rows`)
and preserved the printed table header via `TABLE_COLUMNS` +
`monthly_report` mapping — the ask was CSV only, and the text report still
renders a `total` header. Proven end to end (row keys, CSV file, table header;
`pytest -q` → 14 passed). The baseline changed the table header as an
unreported side effect.

### 04 escalation — green better (after restore)

On the 595-word `0bacca2` bytes, green4-04 lost narrowly: the narrowed
path rule let it document the `command_summary` bypass (`app/main.py:31`
calls `billing.invoice_rows(invoices)` without `args.tax_rate`) instead of
closing it — recorded as "a pre-existing bug I did not change". `b0cf45a`
restored multi-path coverage (590 words); the re-run `green5-04` is the gated
final and was judged better: verified before→after evidence (`950.0` →
`ValueError` for `invoice_total(..., 8.5)`; `--tax-rate 8.5 summary` exit `0`
→ exit `1` with a stderr message; all 5 new tests red pre-fix; `19 passed`
after) plus an explicit migration warning (percentage-style rates such as
`8.5` now error instead of billing; divide by 100). `nan`/`inf`/negative
rates are rejected too.

## Blind gate history

| Round | Green wins | What changed for the next round |
| --- | ---: | --- |
| 1 | 1/4 (scenario 03) | "Work cheap" had been read as "do less work" and "answer first" as "drop evidence". Added: work is not prose, search is not answering, evidence is part of the answer, safe caveats are not detail, scope must not block finishing. |
| 2 | 1/4 (scenario 02) | Still missed call-site breakage after the user's rename (03), left the CLI and direct-caller paths unguarded (04), and gave a narrow explanation (01). Added: check call sites and imports after any change, guard where the value enters and close every path including the CLI, explanations cover the whole path and traps. |
| 3 | 3/4 (02, 03, 04) | Scenario 01 remained a narrow loss. The round-3 ruling accepted it; the plan's gate rule does not, so the explanation-completeness counter was added (`SKILL.md` → Escalate) and scenario 01 was re-gated. |
| Final | 3/4 (02, 03, 04) | Scenario 01 re-gate landed: red still better — accepted loss, recorded in gate-final.md. Scenario 04's narrow loss on 595 words was traced to the Finding-6 path-rule narrowing; the sentence was restored (`b0cf45a`, 590 words) and the re-run (`green5-04`) won. |

## Round 3 — secondary history (superseded)

Verification of the round-3 skill (595 words after the review fixes; 581 at
green-run time). Round 3 is retained for the gate history; the final-skill
gate above supersedes it. Scenario 01's re-gate has since landed and is
recorded above as an accepted loss. All figures below are the round-3
measurements, unchanged.

| Scenario | Output words | Δ words | Output chars | Files read | Δ files | Duplicate reads | Δ dups | Measurement probes | Quality verdict |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 01 explanation | 785 | −872 | 5698 | 10 | −1 | 0 | −6 | 1 | Red better; re-gated — accepted loss |
| 02 bug hunt | 107 | 0 | 841 | 11 | +1 | 4 | 0 | 1 | **Green better** |
| 03 long session | 376 | +8 | 3051 | 5 | −5 | 1 | +1 | 1 | **Green better** |
| 04 escalation | 647 | −268 | 4745 | 10 | 0 | 2 | +1 | 1 | **Green better** (narrow) |
| **Total** | **1915** | **−1132** | **14335** | **36** | **−5** | **7** | **−4** | **4** | 3 of 4 green |

Against RED: 3047 words / 20880 chars / 41 files / 11 duplicate reads. Round
3's output saving was 1132 words (−37.2%) and 6545 chars (−31.3%) — **that
−37.2% belonged to the 581-word skill** and is not the final figure.

Round-3 input context: scenario 01's saving was output only (10 measured
files, 11 at most, vs RED's 11). Scenario 02 read one more file than RED
(11 vs 10) and made one related docs correction (`docs/architecture.md:50`).
Scenario 03 was slightly longer (+8 words) with one extra duplicate open, and
read five fewer files overall (5 vs 10) — the real context saving. Scenario
04's duplicates rose from 1 to 2 while output fell 29.3%.

Round-3 quality verdicts (as recorded at the time; 02/03/04 re-verified on the
final bytes as shown above):

- **01 — red better on depth.** Optional onboarding traps omitted; the
  explanation-completeness counter was added and the scenario re-gated —
  result: red still better, accepted (see gate-final.md).
- **02 — green better.** Before/after repro plus CLI check; RED showed only
  the post-fix state. Related docs correction disclosed. Code verified:
  `total=65.07 expected=65.07`, 15 tests passing.
- **03 — green better.** Verified against the post-edit file with exact
  lines; confirmed the rename end to end (pytest + CLI header/row); RED left
  the CLI export path broken. Scope exceeded the literal request and was
  disclosed. Code verified: `app/main.py:51` calls `reports.export_csv_rows`.
- **04 — green better, narrow.** Verifiable test evidence (before `300.0`,
  after `ValueError`, `21 passed`), line-precise citations, explicit
  behaviour-change note. Missing: docs/changelog update and CLI exit-code
  transcript. Code verified: `command_summary` now passes `args.tax_rate`.

## What this proves, and what it does not

**Proves:** under blind judging, the final skill matches or beats the RED
baseline on 02, 03 and 04, with the scenario 04 win recorded on the final
590-word bytes. Overall output falls from 3047 to 2293 words (−24.8%) and
from 20880 to 16584 chars (−20.6%) on the final runs. The one quality loss is
scenario 01, disclosed and accepted.

**Does not prove:** scenario 01 is a disclosed loss, not a win. Scenarios
02/03 ran on the 595-word `0bacca2` bytes and only the path-scope sentence
changed after `b0cf45a`, so their verdicts were not re-run on the final bytes.
Scenario 04 is the gated final (`green5-04` on `b0cf45a`); the 595-word
scenario 04 run is a recorded narrow loss, not the final result. It does not
prove an input-context saving: no telemetry was recorded for the final runs,
and characters pulled into context was not captured in any run, so no
input-character saving is claimed. It does not prove a saving on short tasks —
scenario 02 grew by 26 words. Scenario 03 grew by 159 words; its win is
quality and scope control, not prose. Telemetry is self-reported and the
summary compares one run per scenario. The earlier −37.2% output figure
belonged to the 581-word skill (round 3) and must not be quoted for the final
skill.
