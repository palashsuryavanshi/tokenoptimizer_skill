# Blind quality gate — round 3 (final skill)

| Scenario | A | B | Verdict | Winner |
|---|---|---|---|---|
| 01 explanation | red | green3 | A better | red |
| 02 bug hunt | green3 | red | A better | **green3** |
| 03 long session | red | green3 | B better | **green3** |
| 04 escalation | green3 | red | A better (narrow) | **green3** |

Output words (red → green1 → green2 → green3): 1657→417→762→783; 107→50→104→105;
368→248→159→374; 915→529→617→645.
Totals: red 3047 → final 1907 (−37%).

Code verified independently after the runs: scenario 2 repro is
`total=65.07 expected=65.07` with 15 tests passing; scenario 3's `app/main.py:51`
now calls `reports.export_csv_rows`; scenario 4's `command_summary` now passes
`args.tax_rate` to `billing.invoice_rows`.

## Scenario 01 — red still better

- Both accurate on the arithmetic. Missing in green: the trap that displayed/CSV
  cells are each rounded from the raw float, so subtotal + tax can fail to equal
  the shown total and the report footer can disagree with the visible column sum;
  also the module-boundary guidance and the warning that tests do not pin
  truncation.
- These are optional onboarding traps, not errors.

**Ruling: accept.** The remaining gap is extra depth on one explanation task, not
a wrong or incomplete answer to what was asked. Chasing it would add words to
every session to buy optional caveats in one scenario, and the skill is already
19 words under its ceiling. Cost if wrong: a new developer onboarding from this
answer misses display-level reconciliation until they hit it.

## Scenario 02 — green better

- "Nothing required — cause, change, and evidence are all present." Green shows a
  before/after repro plus a CLI check; red shows only the post-fix state.

## Scenario 03 — green better

- Green verified against the post-edit file with exact lines, explained the
  rate/tax derivation, and confirmed the rename end to end (pytest + CLI
  header/row). Red left the CLI export path broken.
- Green exceeded the literal "one small change to reports.py" scope by fixing
  `main.py` and adding tests, and disclosed it — the correct behaviour.

## Scenario 04 — green better, narrowly

- Green gave verifiable test evidence (before `300.0`, after `ValueError`,
  `21 passed`), line-precise citations, and an explicit "8.5 is now invalid"
  behaviour-change note.
- Missing in green: no docs/changelog update and no transcript of the CLI exit
  code.
