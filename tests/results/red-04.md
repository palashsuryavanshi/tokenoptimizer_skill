````
## How rounding works in this codebase

Money is stored as plain Python floats everywhere in the application. There is no `Decimal` in production code; `repro.py` imports `Decimal` only to compute its own expected value.

### The one place tax is rounded

`billing._tax_for` (`app/billing.py`) is the single rounding point for invoice tax:

```python
return math.floor(subtotal * tax_rate * 100) / 100
```

That is truncation toward negative infinity at the cent. It is not round-half-up and not round-half-even. For a positive subtotal it always rounds the tax down, so the customer never pays a fraction of a cent and the business absorbs up to $0.0099 per invoice. The grand total is never rounded as a whole; only the tax component is rounded, and `invoice_total` then adds it to the raw float subtotal.

Worked example from `repro.py`: three units at 19.99 give `subtotal = 59.97`. At 8.5%, `59.97 * 0.085 = 5.09745`; `floor(509.745) / 100 = 5.09`; `total = 65.06`. The reproducer computes its expected value differently: it multiplies the subtotal by `1 + tax_rate` and quantizes the total with `ROUND_HALF_UP`, so `59.97 * 1.085 = 65.06745` becomes `65.07`. The one-cent gap is therefore a rounding-model mismatch (floor the tax versus round the total half-up), not a floating-point bug. A single 19.99 line shows the same thing: tax `1.69915` floors to `1.69`, total `21.68`, where half-up would give `1.70` and `21.69`.

### Everywhere else

- `line_total` and `subtotal_for` do no rounding at all: they multiply `qty * unit_price` and sum the raw floats.
- `apply_discount` rounds at the line level with `round(line["unit_price"] * factor, 2)`. Python's `round` is half-to-even and operates on the binary float, so a mathematical half such as `2.675` becomes `2.67`. This happens before tax, because the promotion is advertised per unit.
- `reports.customer_totals` accumulates unrounded subtotals and totals per customer, then rounds `subtotal` and `total` once at the end with `round(..., 2)` (again half-to-even). Rounding after accumulation is deliberate so a customer with many small invoices is not penalised by repeated rounding, but it means a customer row can differ by a cent from the sum of the individually displayed invoice totals.
- `reports.csv_rows` and `reports.summary_lines` format amounts with `f"{value:.2f}"`, which rounds half-to-even on the binary value at the display boundary.
- `utils.money` formats with `f"${value:,.2f}"`; it is presentation only and has the same half-to-even-on-binary behaviour. `format_percent` is likewise formatting only.
- `billing.invoice_rows` does not round either: `subtotal` is raw, `tax` is `total - subtotal` (the floored tax, possibly with float noise such as `5.090000000000003`), and `display_total` goes through `utils.money`.

The rule of thumb: arithmetic is float and mostly unrounded; discounts round unit prices half-to-even; tax is floored down to the cent; customer aggregation rounds once after summing; presentation rounds half-to-even to two decimals. Consequences: each invoice can under-collect up to just under one cent of tax, any external check that uses half-up can disagree by one cent, and long chains of float additions can accumulate representation error. Empty invoices short-circuit cleanly because a zero subtotal yields zero tax.

## The `tax_rate` change

The problem: a tax rate is a fraction, but nothing rejected values above `1.0`. A misconfigured `1.5` on a $100 invoice produced $250, and even `1.0` doubled it. `validate_lines` never looked at `tax_rate`, so the bad value flowed straight into the arithmetic.

What I changed:

1. `app/billing.py`
   - Added `MAX_TAX_RATE = 1.0` beside `DEFAULT_TAX_RATE`.
   - Added a public `validate_tax_rate(tax_rate)` helper. It rejects booleans and non-numeric values with `ValueError("tax rate must be a number")`, rejects NaN and infinity with `"tax rate must be a finite number"`, and rejects `tax_rate < 0 or tax_rate > 1.0` with a message such as `tax rate must be between 0 and 1 (got 1.5); tax rates are fractions, so 8.5% is 0.085`. On success it returns the rate unchanged.
   - Called the helper at the top of both `invoice_total` and `_tax_for`, so direct calls are guarded as well as any path that computes tax. `1.0` remains valid because it legitimately means 100% tax; the request was specifically that values above `1.0` raise.
2. `app/main.py`
   - `command_summary` was calling `billing.invoice_rows(invoices)` and silently ignoring the global `--tax-rate`. It now passes `args.tax_rate`. Without that fix, `--tax-rate 1.5 summary` would still have used the 8.5% default and bypassed the guard entirely.
3. `tests/test_billing.py` — added six regression tests: `invoice_total` rejects `1.5`, rejects a negative rate, accepts `1.0`, `invoice_rows` rejects a per-invoice `"tax_rate": 1.5`, and `validate_tax_rate` returns a good rate. The full suite is 19 tests, all passing.
4. Documentation: added an Unreleased changelog entry and updated the tax-rate notes in `docs/architecture.md` and `README.md`.

Coverage is complete because every report entry point funnels through `billing.invoice_total` (`invoice_rows`, `customer_totals`, `csv_rows`, `summary_lines`, `monthly_report`). A bad document-level rate or a bad per-invoice `"tax_rate"` now raises `ValueError`. The CLI already catches `ValueError` and maps it to exit code 1 with an `error:` prefix, so the user sees the message and no total is printed. Verified against the CLI:

```text
python -m app.main --tax-rate 1.5 report invoices.json --year 2026 --month 3
error: tax rate must be between 0 and 1 (got 1.5); tax rates are fractions, so 8.5% is 0.085
exit code 1
```

`--tax-rate 1.0` still succeeds and doubles the invoice by design.

What I deliberately did not change is the floor-based tax rounding. `repro.py` still prints `total=65.06 expected=65.07`. Switching to `Decimal` with `ROUND_HALF_UP`, or rounding the tax half-up consistently, would remove that discrepancy, but it changes collected amounts and the existing expectations, so it deserves a separate decision and test update.
````
