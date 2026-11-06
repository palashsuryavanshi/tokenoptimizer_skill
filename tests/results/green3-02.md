````
Invoice totals were a cent low because tax was truncated, not rounded: `_tax_for` used `math.floor(subtotal * tax_rate * 100) / 100` (app/billing.py:29), so 5.09745 became 5.09 instead of 5.10.

Changed `_tax_for` to round half-up using `Decimal` strings (app/billing.py:7, app/billing.py:27-30), and added `test_invoice_total_rounds_tax_half_up` for the reported case (tests/test_billing.py:30). All callers go through `invoice_total`, so invoice rows, summary, reports and CSV export are fixed too. Updated the now-stale import note in docs/architecture.md:50.

Proof:
- `python repro.py` before: `subtotal=59.97 tax=5.09 total=65.06 expected=65.07`; after: `subtotal=59.97 tax=5.10 total=65.07 expected=65.07`.
- `python -m pytest tests -q`: 15 passed.
- CLI `summary` and `export` on the same invoice: tax $5.10, total $65.07.
````
