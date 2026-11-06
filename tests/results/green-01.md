````markdown
**A total is `sum(qty × unit_price)` plus `tax`, where tax is `subtotal × rate` truncated to the cent — no fees, no per-line tax, no currency conversion.**

## The path

1. **Load** — `main.py:16` reads the JSON and accepts either `{"invoices": [...]}` or a bare list. No arithmetic here.
2. **Pick the rate** — a per-invoice `tax_rate` wins, else the CLI `--tax-rate`, else `DEFAULT_TAX_RATE = 0.085` (`billing.py:11`, `billing.py:79`).
3. **Subtotal** — `subtotal_for` (`billing.py:22`) sums `qty * unit_price` over the lines as plain floats. `line_total` (`billing.py:15`) is the single-line equivalent, but it defaults missing fields to 0 while `subtotal_for` raises `KeyError`; the multiplication is duplicated rather than shared.
4. **Tax** — `_tax_for` (`billing.py:27`) computes `math.floor(subtotal * tax_rate * 100) / 100`. This truncates to the cent, never rounds up.
5. **Total** — `invoice_total` (`billing.py:32`) returns `subtotal + tax` as an unrounded float whose tax component is already cent-truncated.
6. **Row** — `invoice_rows` (`billing.py:70`) recomputes subtotal and total (the sums run twice), derives `tax` as `total - subtotal`, and formats `display_total` with `utils.money` (`utils.py:34`, `${value:,.2f}`).

Discounts belong before step 3: `apply_discount` (`billing.py:39`) copies each line and rounds the discounted unit price to the cent, so quantity multiplies an already-rounded price. The original lines are untouched.

## Consumers

- `reports.csv_rows` (`reports.py:55`) calls the same pair and formats to 2dp.
- `summary_lines` (`reports.py:119`) sums `subtotal_for`/`invoice_total` across invoices.
- `customer_totals` (`reports.py:30`) accumulates raw floats per normalised customer name and rounds once at the end (`reports.py:50`), avoiding repeated cent rounding.
- `command_summary` (`main.py:28`) sums `invoice_rows`; `command_report` and `command_export` go through `reports`.

Every printed amount comes from these two billing functions, which is what keeps the monthly report and the summary in agreement.

## Worked example

`3 × 19.99 = 59.97`; tax `floor(59.97 × 0.085 × 100) / 100 = floor(509.745) / 100 = 5.09`; total `65.06`. `repro.py` prints exactly that, against an expected `65.07` computed by rounding the total half-up.

## Things that bite

- **Tax truncates.** `_tax_for` floors instead of rounding half-up, so a total can land a cent below what an accountant expects — that is the open discrepancy. Fix it in `_tax_for` and every consumer above inherits the change.
- **Money is float** (`docs/architecture.md:240`). Rounding happens only at display and in `customer_totals`.
- **Validation is off the calculation path.** `validate_lines` (`billing.py:52`) runs only from `command_validate` (`main.py:57`), so a summary will include a qty of 0 or a negative price; a missing key raises `KeyError`, not `ValueError`.
- **Empty invoices** total to 0.0 because `sum([])` is 0; only validation rejects them.
````
