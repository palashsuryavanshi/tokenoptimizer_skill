# Blind quality gate — final skill

| Scenario | Run file | Words | Verdict | Winner | Skill bytes |
|---|---|---:|---|---|---|
| 01 explanation | green4-01.md | 787 | Red better — accepted loss | red | 595 |
| 02 bug hunt | green4-02.md | 133 | Green better | **green4** | 595 |
| 03 long session | green4-03.md | 527 | Green better | **green4** | 595 |
| 04 escalation | green5-04.md | 846 | Green better | **green5** | 590 |

Words are wrapper-free (red 1657/107/368/915; final as shown).
Measured with the four-backtick wrapper the final files are 789/135/529/848 =
2301. Skill bytes: scenarios 01–03 ran on the 595-word `0bacca2`; only the
path-scope sentence changed for `b0cf45a` (590 words), and scenario 04 was
re-run on those bytes — `green5-04` is the gated final. The 595-word scenario
04 run (`green4-04`) lost narrowly and is kept as the record of that loss.

Final totals: red 3047 vs final 787+133+527+846 = **2293 (−24.8%)**.
Chars (measured, both sides, wrapper included): red 20880 vs final 16584
(−20.6%). Wrapper note: red's 3047 includes the wrapper and the green figures
do not, matching gate-round3's convention; like-for-like measured totals are
2301 (−24.5%), and wrapper-free red is 3039 vs 2293 (−24.6%). The earlier
**−37.2%** figure belonged to the 581-word skill (round 3) and does not
describe this gate.

## Scenario 01 — red better; accepted loss

- Green is more accurate about the report layer's duplicated recomputation:
  `summary_lines` recomputes subtotal and total from the raw invoices rather
  than summing the table cells, so a report whose cells each show 0.35 can
  print a $1.06 footer (verified in the answer: three 1 × $0.333 invoices).
- Red is broader on optional onboarding traps (display-level reconciliation
  depth, module-boundary guidance, truncation not pinned by tests).

**Ruling: accept.** The remaining gap is extra depth on one explanation task,
not a wrong answer to what was asked, and the green answer was still accurate
where the baseline was not. Cost of the accepted loss: a newcomer onboarding
from the green answer misses display-level reconciliation and module-boundary
guidance. Red is 1657 words vs green's 787, so the gap is bought with more
than double the prose. Chasing it would add words to every session to buy
optional caveats in one scenario.

## Scenario 02 — green better

- Before/after repro evidence (`5.09/65.06` → `5.10/65.07`), exact location
  (`app/billing.py:29`, `math.floor` → `Decimal` half-up quantize), and
  blast radius (`invoice_rows`, `reports.csv_rows`, `reports.summary_lines`,
  `main.py` all inherit the fix; `repro.py`'s half-up expected value now
  matches; `pytest -q` → 15 passed). RED shows only the post-fix state.

## Scenario 03 — green better

- Scoped the rename to the CSV export (`CSV_COLUMNS` ends `invoice_total`,
  `export_csv_rows` emits the `"invoice_total"` key) and preserved the printed
  table header via `TABLE_COLUMNS` + `monthly_report` mapping, so the text
  report still renders a `total` header — the ask was CSV only. Proven end to
  end: row keys, CSV file and table header all shown; `pytest -q` → 14 passed.
- The baseline changed the table header as an unreported side effect.

## Scenario 04 — green better (after restore)

History of this scenario across the gate:

- Round 3 (581-word skill): green won narrowly.
- Review Finding 6 narrowed the path rule ("…close every path… unless the
  user asks") → 595-word `0bacca2`. Re-gate: **narrow loss** (`green4-04`).
  The narrowed rule let it document the `command_summary` bypass
  (`app/main.py:31` calls `billing.invoice_rows(invoices)` without
  `args.tax_rate`) instead of closing it — recorded as "a pre-existing bug I
  did not change", with only an out-of-range backstop from the new validation.
- `b0cf45a` restored multi-path coverage (close every path the requested
  behaviour passes through, including the CLI; fix or report each broken
  path) → 590 words. Re-run `green5-04`, judged **better**:
  verified before→after evidence (`invoice_total([{"qty": 1, "unit_price": 100.0}], 8.5)`
  → `950.0` before, `ValueError` after; `--tax-rate 8.5 summary`
  exit `0` before, exit `1` with stderr message after; all 5 new tests red
  pre-fix and `19 passed` after) plus an explicit migration warning: any stored
  document or caller using percentage-style rates (`8.5`) now errors instead
  of billing — migrate by dividing by 100. `nan`/`inf`/negative rates are
  rejected too.
