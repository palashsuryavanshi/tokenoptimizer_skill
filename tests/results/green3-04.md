````
**Answer:** `tax_rate` is now validated as a fraction in `0..1` at `app/billing.py:16` (`validate_tax_rate`, called from `_tax_for` at `app/billing.py:44`), so `2.0` raises `ValueError: tax rate must be between 0 and 1, got 2.0` instead of producing a 300.0 total on a 100.0 invoice. Every calculation path (`invoice_total`, `invoice_rows`, and therefore all report functions) funnels through `_tax_for`; the CLI maps the error to exit 1, and `validate` now reports bad per-invoice rates. 21 tests pass.

**How rounding works**

There is no single rounding policy; four different mechanisms meet.

1. **Subtotal: no rounding.** `subtotal_for` (`app/billing.py:37-39`) and `invoice_total` (`:50`) sum `qty * unit_price` as Python floats and never quantize. A price like 19.99 is already binary-inexact, and multi-line sums accumulate that error. Tests compare with `pytest.approx` for this reason.

2. **Tax: floor/truncation to cents.** `_tax_for` (`:42-45`) does `math.floor(subtotal * tax_rate * 100) / 100`. Multiplying by 100 and flooring discards the fractional cent, then dividing by 100 puts it back. This always rounds tax down for a positive subtotal — it is truncation, not nearest-cent rounding. Fractional cents never accumulate into a later carry. This is the source of the repro one-cent gap.

3. **Total: no quantization.** `invoice_total` (`:48-52`) returns `subtotal + tax`. The tax has two decimals, but the subtotal may not, so the total can carry extra precision. `invoice_rows` (`:86-108`) derives the displayed tax by subtracting subtotal from total (`:103`) rather than calling `_tax_for` again; floating subtraction can leave artifacts such as 5.090000000000003.

4. **Display: half-even formatting.** `utils.money` (`app/utils.py:34-38`) uses `f"{value:,.2f}"`; `reports.csv_rows` (`app/reports.py:67-69`) uses `f"{value:.2f}"`. Python's format rounds to nearest, ties to even, on the exact binary value, so the printed cent can differ from a decimal-hand calculation (e.g. 2.675 formats as 2.67). Formatting is the only rounding applied to a printed total; `format_table` (`app/reports.py:86-116`) only pads strings.

5. **Discounts: `round()` per unit.** `apply_discount` (`app/billing.py:63`) uses `round(unit_price * factor, 2)`, also half-even but on the binary float. Discounted unit prices are rounded before any tax is computed, deliberately per the architecture note.

6. **Customer aggregates: one round after accumulation.** `reports.customer_totals` (`app/reports.py:50-51`) sums unrounded invoice totals and rounds subtotal/total to cents once at the end. That avoids repeated rounding for many small invoices, but it means the aggregate can differ by a cent from the sum of individually displayed invoices.

**The repro and its trap.** `repro.py` computes `subtotal=3*19.99=59.97`, then tax `floor(59.97*0.085*100)/100 = 5.09`, total `65.06`. Its "expected" uses `Decimal` and `ROUND_HALF_UP` on `subtotal*(1+rate)`, giving `65.07`. The gap is methodological (per-tax truncation plus unrounded subtotal vs. one half-up calculation on the total), not a single bug; a half-up tax alone would give 5.10 and total 65.07. I left this behavior unchanged because the request was the rate guard, not a rounding-policy change.

**Other traps.** `round()` and `:.2f` are banker's rounding, not half-up. `line_total` (`:30-34`) exists but `invoice_total` recomputes the sum inline. There is no `Decimal` in the application path. Rates are fractions: `0.085` is 8.5%, `8.5` is invalid now rather than an 850% tax.

**What changed**
- `app/billing.py`: added `MAX_TAX_RATE = 1.0` and `validate_tax_rate`; `_tax_for` calls it before calculating, so `invoice_total`, `invoice_rows`, `reports.customer_totals`, `reports.csv_rows`, `reports.summary_lines` and `reports.monthly_report` all reject bad rates. Negative and NaN rates are rejected too.
- `app/main.py:31`: `summary` now passes the CLI `--tax-rate` into `invoice_rows`; previously it silently ignored it. All three calculating commands now surface the `ValueError`, which `main()` maps to `error: ...` and exit 1.
- `app/main.py:64`: `validate` checks each invoice's effective rate and reports it per invoice.
- `tests/test_tax_rate.py`: seven regression tests covering the boundary, per-invoice rates, negative/NaN, and CLI summary/validate paths.

**Proof**
```
before guard: 300.0
after guard: ValueError: tax rate must be between 0 and 1, got 2.0
python -m pytest tests -q
21 passed in 0.07s
```
The pre-change arithmetic for a 100.0 subtotal at 2.0 was `100 + floor(100*2.0*100)/100 = 300.0`; the current call raises. `repro.py` still prints `subtotal=59.97 tax=5.09 total=65.06 expected=65.07`, confirming the existing rounding path is untouched.
````