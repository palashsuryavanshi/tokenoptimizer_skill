````
Cause: `app/billing.py:29` computed tax with `math.floor(subtotal * tax_rate * 100) / 100`, which truncates to cents instead of rounding. `59.97 * 0.085 = 5.09745` became `5.09` rather than `5.10`, so the total came out one cent low. The repro's expected value rounds half up.

Fix:
- `app/billing.py` — `_tax_for` now multiplies `Decimal(str(subtotal))` by `Decimal(str(tax_rate))` and quantizes to `Decimal("0.01")` with `ROUND_HALF_UP`; removed the now-unused `import math`. `invoice_total` and `subtotal_for` are unchanged, so every caller (`invoice_rows`, `reports.csv_rows`, `reports.summary_lines`, `main.py`) inherits the correct rounding.
- `tests/test_billing.py` — added `test_invoice_total_rounds_tax_half_up` covering the 3 x 19.99 at 8.5% case and the raw `_tax_for(59.97, 0.085)` value.

Proof:
- Before: `python repro.py` → `subtotal=59.97 tax=5.09 total=65.06 expected=65.07`
- After: `python repro.py` → `subtotal=59.97 tax=5.10 total=65.07 expected=65.07`
- `python -m pytest -q` → `15 passed in 0.05s`
- `invoice_rows(...)["display_total"]` → `$65.07`
````
