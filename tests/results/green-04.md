````
Fixed: tax rates above 1.0 now raise `ValueError` instead of inflating totals. A $100 invoice at `tax_rate=8.5` previously produced 950.00; it now fails with `tax rate must be a fraction at most 1.0 (got 8.5); use 0.085 for 8.5%`. Test suite: 18 passed (14 before).

## Rounding walkthrough

Money is float from input to output (`README.md:88`, `docs/architecture.md:107-109`). Rounding happens at four points, and only the first two affect stored or summed numbers.

1. **Line arithmetic is not rounded.** `line_total` multiplies qty by unit price (`app/billing.py:30-34`), and `subtotal_for` sums the same product (`app/billing.py:37-39`). Binary float error can accumulate here.

2. **Discounts round per line, before tax.** `apply_discount` computes `unit_price * (1 - percent/100)` and calls `round(..., 2)` on each resulting unit price (`app/billing.py:55-65`, rounding at `:63`). Python's `round` is half-even (banker's rounding), subject to float representation, so exact half-cent cases can go to the even cent. The rounded unit price then feeds all later tax and total calculations.

3. **Tax is floored to cents.** `_tax_for` is `math.floor(subtotal * tax_rate * 100) / 100` (`app/billing.py:42-45`). This always truncates downward, never half-up. `invoice_total` adds that floored tax to the unrounded subtotal (`app/billing.py:48-52`). `repro.py` shows the consequence: 3 x 19.99 = 59.97, tax at 0.085 is 5.09745 -> 5.09, total 65.06, while `ROUND_HALF_UP` expects 65.07 (`repro.py:13-23`). Because the multiply uses floats, a value mathematically at a cent boundary can land just below it and lose another cent.

4. **Customer aggregates round once, after accumulation.** `customer_totals` sums raw subtotals and totals per customer, then applies `round(..., 2)` to the two aggregates (`app/reports.py:36-52`, rounding at `:51-52`). This is deliberate (`docs/architecture.md:146-149`) and means a customer's rounded total need not equal the sum of the per-invoice rounded totals.

**Display formatting rounds at the edge only.** `utils.money` uses `f"{value:,.2f}"` (`app/utils.py:34-38`), CSV rows use the same `.2f` formatting (`app/reports.py:69-71`), and `invoice_rows` stores `display_total` from `money` (`app/billing.py:106`). `format_percent` also formats with `.2f` (`app/utils.py:49-51`). These strings never feed back into arithmetic; `.2f` uses half-even on the float being printed.

Tax-rate precedence: an invoice's own `tax_rate` overrides the function or CLI rate, which defaults to `DEFAULT_TAX_RATE = 0.085` (`app/billing.py:11`, `:96`; `app/reports.py:40`, `:61`, `:126`). The rate is a fraction, so 0.085 is 8.5%.

## What changed

- Added `MAX_TAX_RATE = 1.0` and `validate_tax_rate` (`app/billing.py:12-27`). It rejects strictly greater-than-1.0 rates with an actionable message; exactly 1.0 (100%) remains valid.
- Enforced it inside `_tax_for` (`app/billing.py:44`), which covers every `invoice_total` call, including per-invoice overrides.
- Also validate the rate parameter at `invoice_rows` (`app/billing.py:92`) and the report entry points `customer_totals`, `csv_rows`, `summary_lines`, `monthly_report` (`app/reports.py:36`, `:58`, `:123`, `:139`), so a bad CLI rate raises even when no invoice matches.
- Added tests for the boundary, per-invoice overrides, and the empty-report path (`tests/test_billing.py`). `python -m pytest tests -q` -> **18 passed**.

This is a breaking change only for rates above 100%: anyone who intentionally used them, or passed percent values such as 8.5 instead of 0.085, now gets a `ValueError` (CLI exit code 1 via `app/main.py:109-113`) instead of a doubled invoice. Negative rates still behave as before because only the upper bound was requested. Files changed: `app/billing.py`, `app/reports.py`, `tests/test_billing.py`. Caveat: `command_summary` still ignores the global `--tax-rate` (`app/main.py:31`), unchanged from before; per-invoice rates above 1.0 do raise during summary.
````
