# Blind quality gate — round 2 (revised skill)

| Scenario | A | B | Verdict | Winner |
|---|---|---|---|---|
| 01 explanation | green2 | red | B better (narrow) | red |
| 02 bug hunt | red | green2 | B better (narrow) | **green2** |
| 03 long session | green2 | red | B better | red |
| 04 escalation | red | green2 | A better | red |

Word counts (red → green1 → green2): 1657→417→762; 107→50→104; 368→248→159;
915→529→617.

Result: still 3 of 4 to red, but narrower. One clear win (scenario 2: the
regression test and before/after evidence now match red). The remaining losses
are substantive in two cases:

## Scenario 03 — green missed a real break

- "The user's mid-task rename `csv_rows` → `export_csv_rows` ... A never notices
  the rename, though both correctly rename the CSV column."
- Missing in green: that `app/main.py` still calls `reports.csv_rows`, so
  `export` raises `AttributeError`. Red caught the regression caused by the
  concurrent edit; green did not.
- Cause: nothing in the skill asks the agent to check the call sites of what
  changed — the user's change included.

## Scenario 04 — green left a real path unfixed

- Missing in green: no guard on `invoice_total` for direct callers, no mention
  that `command_summary` ignores `--tax-rate` (the CLI bypass red fixes), no
  explicit statement that floor rounding is unchanged and the repro still shows
  65.06 vs 65.07.
- Cause: the "request defines the behaviour" line did not say to apply a guard
  where the value enters, or to close every path the behaviour passes through.

## Scenario 01 — narrower loss

- "Both are accurate on the core arithmetic." Missing in green: that
  `--tax-rate` must precede the subcommand, banker's rounding inside
  `apply_discount`, an explicit demonstration that formatted columns need not
  sum, and floor on negative subtotals.
- These are onboarding traps rather than errors in the calculation itself.

## Decision

Round 3 of the refactor targets the two substantive failures (03, 04) and adds
one line for explanation completeness (01). If 01 remains a narrow loss on
optional traps while 02-04 hold, that is acceptable and will be ruled on in the
ledger rather than chased further.
