````
Fixed. The one-cent shortfall came from `_tax_for` in `app/billing.py`: it computed tax with `math.floor(subtotal * tax_rate * 100) / 100`, which truncates down to the cent instead of rounding. For the repro, 59.97 × 0.085 = 5.09745, so tax became 5.09 instead of 5.10, and the total became 65.06 instead of 65.07.

I replaced the truncation with half-up rounding to the cent using `Decimal`, converting through `str` to avoid binary float artifacts. I added a regression test for this case in `tests/test_billing.py` and a changelog entry under Unreleased.

Verification: `python repro.py` now prints `subtotal=59.97 tax=5.10 total=65.07 expected=65.07`, and `python -m pytest -q` reports `15 passed`.
````
