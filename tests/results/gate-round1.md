# Blind quality gate — round 1

Judged by four fresh subagents. Each saw two answers labelled A and B, with the
order randomised, and did not know which came from the skill. Mapping:

| Scenario | A | B | Verdict | Winner |
|---|---|---|---|---|
| 01 explanation | red | green | A better | **red** |
| 02 bug hunt | green | red | B better | **red** |
| 03 long session | red | green | B better | **green** |
| 04 escalation | green | red | B better | **red** |

Result: 3 of 4 green answers are worse. The skill saved output words
(1657→417, 107→50, 368→248, 915→529) but lost substance. This is a failed
GREEN, not a saving.

## Scenario 01 — red better

- Missing in green: the real `--tax-rate` bug — `command_summary` never passes
  `args.tax_rate`, so `summary` and `report` can disagree. Also missing: the fact
  that independently rounded CSV/footer cells need not add up; that
  `apply_discount` uses banker's `round` so even 0% can move a price; floor's
  behaviour on negative subtotals; and the per-invoice rate expression used in
  `reports.py`.
- Green asserted something false: "every printed amount comes from these two
  billing functions... which keeps the monthly report and the summary in
  agreement" — contradicted by the `--tax-rate` case.
- Red was the only answer that named the rounding-location issue (tax truncated
  separately, total never rounded) as a distinct cause.

## Scenario 02 — red better

- Missing in green: no regression test (14 tests = pre-existing only), no
  changelog entry, and the tax arithmetic (5.09745 → 5.09 vs 5.10) implied rather
  than shown.
- Red added a regression test (15 passed) and showed the concrete numbers.

## Scenario 03 — green better

- Green named the real side effect of editing the shared `CSV_COLUMNS` (it also
  feeds `format_table`, so the printed table header changes) and stuck to
  verifiable facts.
- Red buried that consequence and added an unverified `AttributeError` claim.
- Missing in green: indirect helper deps (`pad`→`truncate`,
  `normalize_customer_name`→`collapse_spaces`) beyond `collapse_spaces`.

## Scenario 04 — red better

- Missing in green: it closed no gap for the CLI path it admits is broken —
  `--tax-rate 1.5 summary` still silently ignores the flag, so a rate above 1.0
  does not raise there. Also no docs/changelog update, no guard against
  NaN/inf/non-numeric.
- Red fixed the silent-ignore path in `command_summary` and showed CLI-level
  evidence (`error: … exit code 1`). Green only documented that hole as a caveat.

## Diagnosis

Two causes, both in the skill's wording:

1. **"Work cheap" was read as "do less work."** Scenario 01 searched
   `reports.py` instead of reading it and then made a claim about it that was
   false. Scenario 04 left the CLI path unfixed because it stayed "inside the
   requested scope" instead of finishing the requested behaviour.
2. **"Answer first / only detail needed" was read as "drop evidence and
   caveats."** Scenario 02 dropped the regression test and the arithmetic.
   Scenario 04 dropped the breaking-change warning the skill itself asks for.

Neither is a length problem. Both are content problems: the skill must save
words and needless reads, never work product, evidence, or the caveat that makes
an answer safe to act on.
