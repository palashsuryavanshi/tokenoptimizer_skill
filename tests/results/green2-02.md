````
Fixed: tax was truncated to the cent at `app/billing.py:27` (`math.floor(subtotal * tax_rate * 100) / 100`), so 5.09745 became 5.09 and the total 65.06. It now multiplies `Decimal(str(subtotal))` by `Decimal(str(tax_rate))` and quantizes with `ROUND_HALF_UP`, giving tax 5.10 and total 65.07.

Before: `subtotal=59.97 tax=5.09 total=65.06 expected=65.07`
After: `subtotal=59.97 tax=5.10 total=65.07 expected=65.07`

Every report path (`invoice_rows`, `reports.csv_rows`, `customer_totals`, `summary_lines`) calls `invoice_total`, so all inherit the fix. `apply_discount` still uses Python's `round()` on line prices, and `customer_totals` uses it on accumulated report totals; neither is the truncated-tax path, and I left both unchanged.

Changed files: `app/billing.py` and `tests/test_billing.py` (added `test_invoice_total_rounds_tax_half_up_instead_of_truncating`). `python -m pytest tests -q`: 15 passed.
````
