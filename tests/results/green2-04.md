````
Tax rates outside `0..1` now raise `ValueError`; valid rates behave exactly as before. All tax arithmetic funnels through `billing._tax_for`, so one guard covers `invoice_total`, `invoice_rows`, the CSV rows, customer totals and report summaries. Tests: 19 passed (5 new).

## How rounding works here

Money is binary `float` everywhere (docs/architecture.md:107, docs/architecture.md:240-241). No `Decimal` is used in application code; `repro.py` imports it only as an oracle (repro.py:5, repro.py:19-23).

**1. Tax is floored, not rounded to nearest.** `billing._tax_for` (app/billing.py:43-46) computes `math.floor(subtotal * tax_rate * 100) / 100`. `math.floor` truncates toward negative infinity, so the tax is always rounded *down* to a whole cent. It runs on the raw float product, before any display formatting. `invoice_total` (app/billing.py:49-53) adds that floored tax to an unrounded subtotal, so the returned total carries the same downward bias. `repro.py` demonstrates the gap: 3 × 19.99 = 59.97, 8.5% = 5.09745, floor → 5.09, total 65.06, whereas `Decimal(...).quantize(..., ROUND_HALF_UP)` gives 65.07 (repro.py:12-28). That one-cent difference is pre-existing and is *not* part of this change.

**2. Discounts use Python's `round`.** `apply_discount` (app/billing.py:56-66) does `round(line["unit_price"] * factor, 2)` per line, deliberately at unit level (docs/architecture.md:127-130). `round` on floats is banker's rounding (half-to-even) applied to the nearest binary float, so a nominal half-cent such as 2.675 can become 2.67 rather than 2.68.

**3. Customer aggregates round once, after summing.** `reports.customer_totals` (app/reports.py:36-52) accumulates unrounded subtotals and totals per normalised customer, sorts, then applies `round(..., 2)` once to each (app/reports.py:50-51). This matches the documented intent of not penalising many small invoices through repeated rounding (docs/architecture.md:146-149).

**4. Display formatting rounds separately, at the edge.** `utils.money` (app/utils.py:34-38) uses `f"{value:,.2f}"`; `reports.csv_rows` uses the same `:.2f` format for subtotal, tax and total (app/reports.py:67-69); `summary_lines` (app/reports.py:126-131) and `main.command_summary` (app/main.py:34-37) call `money`. These conversions round half-to-even on the stored binary value. They are terminal: no rounded string feeds back into arithmetic.

The layers therefore disagree by design: tax is floor-rounded, per-line discounts and aggregate totals are `round()`-rounded, and presentation is format-rounded. Every path is float-based, so a value that is mathematically exactly half a cent is resolved by its binary representation plus the rounding mode of that layer.

Rates enter as fractions: `DEFAULT_TAX_RATE = 0.085` (app/billing.py:11); docs/architecture.md:123-125 and README.md:73 both say `0.085` means 8.5 percent. Per-invoice overrides are read in `invoice_rows` (app/billing.py:96), `customer_totals` (app/reports.py:39), `csv_rows` (app/reports.py:59) and `summary_lines` (app/reports.py:123), and all of them call `invoice_total`. Before this change, a rate of `8.5` produced `100 + 850 = 950.00` for a $100 invoice; `1.085` produced a 208.5% total. Nothing rejected it.

## The change

- `app/billing.py:12` adds `MAX_TAX_RATE = 1.0`.
- `app/billing.py:28-40` adds `validate_tax_rate`, which raises `ValueError` unless the rate is finite and within `0..1`.
- `app/billing.py:45` calls it from `_tax_for`, the single choke point for tax computation. Consequently `invoice_total`, `invoice_rows`, `reports.customer_totals`, `reports.csv_rows`, `reports.summary_lines` and the CLI all reject a bad document-level or per-invoice rate without extra call-site checks. `1.0` itself remains valid.
- `tests/test_billing.py` adds five regressions: above-one, negative, exactly-one, per-invoice override through `invoice_rows`, and the reporting path through `reports.csv_rows`.

Negative and non-finite rates are now rejected too, slightly beyond the literal "above 1.0" request; previously a negative rate silently reduced an invoice, and `nan` slipped through every comparison.

## Evidence

Old effective result for a $100 invoice at `8.5`: `950.0` (verified by evaluating `100 + 100*8.5`).

New result:

```
ValueError: tax rate must be a fraction between 0 and 1, got 8.5; 8.5% is 0.085, not 8.5
```

Through the CLI with a per-invoice `tax_rate` of `1.085`, `python -m app.main summary bad-tax.json` prints the same `error:` message and exits `1`.

`python -m pytest -q` → `19 passed in 0.04s` (14 existing + 5 new). The existing 8.5% invoice still returns `65.06`, and the new exact-1.0 test returns `200.0`.

Files changed: `app/billing.py`, `tests/test_billing.py`. No docs were edited.
````
