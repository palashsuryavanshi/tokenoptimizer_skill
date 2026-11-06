````
Fixed: `_tax_for` truncated the tax to the cent with `math.floor` instead of rounding half-up, so any tax whose third decimal was 5 or more came out a cent low (app/billing.py:27). It now rounds via `Decimal`/`ROUND_HALF_UP` (app/billing.py:29-32).

`python repro.py` now prints `subtotal=59.97 tax=5.10 total=65.07 expected=65.07`; all 14 tests pass.
````
