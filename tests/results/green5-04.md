````
**Fixed:** a `tax_rate` above `1.0` now raises instead of inflating the bill. `invoice_total([{"qty": 1, "unit_price": 100.0}], 8.5)` previously returned `950.0` (tax `850.0` on a `$100` invoice — a 9.5x total, not 2x); it now raises `ValueError: tax rate must be a fraction between 0 and 1 (got 8.5); pass 0.085 for 8.5%`. `0.085` still returns `108.5`, `1.0` returns `200.0`.

## How rounding works

Rounding is not centralised. Six sites apply two rules (floor, and half-to-even), and `app/` contains no `Decimal` at all — `repro.py` is the only file that imports it, which is why its "expected" number disagrees with the app.

1. **Tax is floored, once per invoice** — `billing._tax_for`, `app/billing.py:44`: `math.floor(subtotal * tax_rate * 100) / 100`. The tax is truncated down to whole cents; it is not rounded half-up and the subtotal is not quantised. On `3 × 19.99 = 59.97` at 8.5%, the tax is `5.09745 → 5.09`, total `65.06`. `repro.py` prints `subtotal=59.97 tax=5.09 total=65.06 expected=65.07`; the expected value comes from `Decimal` half-up on the total, so the two disagree by exactly the discarded half-cent. Floor can only lose money, so the error is at most one cent per invoice and always in the customer's favour — except for a negative subtotal, where `floor` moves toward −∞: `-59.97` yields tax `-5.10`, whereas truncation toward zero would give `-5.09`. `invoice_total` does not validate lines, so negative unit prices reach it; `validate_lines` is opt-in and `summary`, `report` and `export` never call it.

2. **Discounts round at the unit, half-to-even on the binary float** — `billing.apply_discount`, `app/billing.py:63`: `round(unit_price * factor, 2)`. Python's `round` is half-to-even, and the tie direction depends on the float's stored bits: `round(2.675, 2) == 2.67`, `round(10.75 * 0.9, 2) == 9.68`, `round(0.5) == 0` but `round(1.5) == 2`. Discounted prices are fixed per line before tax, so the discount compounds with the tax floor, and applying it twice compounds for real (the input list is copied, but the caller's new list is already discounted).

3. **Displayed tax is derived, not the floored value** — `billing.invoice_rows`, `app/billing.py:103`: `"tax": total - subtotal`. For the 3×19.99 invoice that is `5.090000000000003`, not `5.09`. `utils.money` hides it; a consumer doing arithmetic on the row does not.

4. **Customer totals round after accumulation** — `reports.customer_totals`, `app/reports.py:50-51`: totals are summed unrounded at the invoice level, then `round(..., 2)` once per customer. `docs/architecture.md:148` calls this deliberate ("a customer with many small invoices is not penalised by repeated rounding"). That is true of the final `round`, but every input total already lost up to a cent inside `_tax_for`, so repeated truncation is still in the number. Ties in the descending sort keep document order, since `sorted` is stable.

5. **Every printed amount rounds again** — `reports.csv_rows` (`app/reports.py:67-69`), `utils.money` (`app/utils.py:37`), `utils.format_percent` (`app/utils.py:51`) all use `f"...{x:.2f}"`, which rounds half-to-even on the stored float. So the displayed cent can differ from the stored value: `money(1.0050000000000001)` is `$1.01`, while the literal `1.005` formats as `1.00` because it is stored just below the tie. Subtotal and total keep sub-cent tails (`qty=3, unit_price=0.335` gives `1.0050000000000001` and total `1.0850000000000002`); only tax is cent-quantised.

What this does not guarantee: no existing test pins the truncation (`test_invoice_total_adds_tax` uses a clean 0.1 rate and `pytest.approx`), there is no property test, `customer_totals`, `summary_lines` and `monthly_report` have no direct tests, and nothing reconciles the sum of per-invoice totals against a single recomputation. The 65.06/65.07 mismatch is real, not a flake.

## The `tax_rate` change

`billing.validate_tax_rate` (`app/billing.py:16`) rejects anything where `not 0 <= rate <= 1`, which also catches `nan` and `inf`, and returns the rate on success — the same validate-and-return shape as `validate_lines`. It is called at the top of `billing.invoice_total` (`app/billing.py:49`), the one function every arithmetic path funnels through: `invoice_rows` (including per-invoice overrides), `reports.csv_rows`, `customer_totals`, `summary_lines`, `monthly_report`, and the CLI commands. Negative rates are rejected too; they are the same misconfiguration and previously reduced the bill (`-0.01` on `$100` gave `$99.00`).

The CLI needed a separate guard: `main.main` validates `args.tax_rate` before dispatch (`app/main.py:110`). Without it, a document whose invoices all carry their own `tax_rate` never consults the flag — the pre-fix test run showed `--tax-rate 8.5 summary` exiting `0` and printing `Total: $108.50`, silently ignoring the bad flag.

Files changed: `app/billing.py` (`MAX_TAX_RATE`, `validate_tax_rate`, guard in `invoice_total`), `app/main.py` (CLI guard), `tests/test_billing.py` (4 tests: above 1.0 rejected, 1.0 accepted, negative rejected, per-invoice override rejected), `tests/test_cli.py` (new, exits 1 with a `tax rate` message), plus one line each in `README.md` and `docs/changelog.md` recording the fraction rule.

Proof, before → after:

- `invoice_total([{qty: 3, unit_price: 19.99}], 8.5)` → `569.71` before; now `ValueError` (recorded from a pre-fix probe).
- `--tax-rate 8.5 summary` → exit `0` before; now `error: tax rate must be a fraction between 0 and 1 (got 8.5); pass 0.085 for 8.5%`, exit `1`.
- `--tax-rate 0.085 report ... --year 2026 --month 3` → `Total: $108.50`, exit `0`, unchanged.
- `python -m pytest -q` → `19 passed in 0.04s`. All 5 new tests failed before the change (4 billing, 1 CLI).

Breaking change: any stored document or caller using percentage-style rates (`8.5`) now errors instead of billing. Migrate by dividing those values by 100.
````
