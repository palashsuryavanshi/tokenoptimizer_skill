````markdown
## Change

A tax rate above `1.0` now raises before any invoice arithmetic runs: `billing.validate_tax_rate` (`app/billing.py:28`) raises `ValueError("tax rate must not exceed 1.0 (got ...)")`, `invoice_total` calls it before touching the lines (`app/billing.py:47`), and `main` calls it before dispatch (`app/main.py:110`). Exactly `1.0` remains legal; above it does not.

Concretely, `invoice_total([{"qty": 1, "unit_price": 100.0}], 1.085)` used to return `208.5` — `100` plus `108.5` tax, or 2.085× the invoice. It now raises. Through the CLI, `--tax-rate 1.085` exits `1` and prints `error: tax rate must not exceed 1.0 (got 1.085)` to stderr.

Placing the guard in `invoice_total` closes every calculation path, because `invoice_rows`, `customer_totals`, `csv_rows`, `summary_lines` and `monthly_report` all funnel through it, including per-invoice `tax_rate` values read from JSON. The extra call in `main` also rejects a bad global `--tax-rate` when there are no invoices to calculate, where the arithmetic guard would never run.

Files changed: `app/billing.py`, `app/main.py`, `tests/test_billing.py`, `tests/test_main.py` (new), and `README.md` (one sentence documenting the ceiling).

Evidence: `python -m pytest -q` → `18 passed in 0.05s` (14 pre-existing plus 4 new). The new tests are `test_invoice_total_rejects_tax_rate_above_one`, `test_invoice_total_accepts_tax_rate_of_exactly_one`, `test_invoice_rows_rejects_per_invoice_tax_rate_above_one`, and `test_cli_rejects_tax_rate_above_one`.

Caveats: negative rates are still accepted, because only the `> 1.0` case was in scope; they would produce negative, floored tax. Separately, `command_summary` ignores the global `--tax-rate` entirely (`app/main.py:31` calls `billing.invoice_rows(invoices)` without `args.tax_rate`), a pre-existing bug I did not change; the new validation means it at least rejects an out-of-range value instead of silently ignoring it.

## How rounding works

Rounding is not centralised. Four different mechanisms appear, and they do not agree with each other.

### 1. Tax is floored to the cent

`app/billing.py:40-42`:

```python
def _tax_for(subtotal, tax_rate):
    return math.floor(subtotal * tax_rate * 100) / 100
```

This is a floor after multiplying by 100, so it always moves the tax down to the next cent (toward negative infinity, for negative subtotals). It is not half-up, half-even, or commercial rounding. For `3 × 19.99` at `0.085`, the product prints as `509.745`; `math.floor` gives `509`, so tax is `5.09`. The exact tax is `5.09745`, and half-up would give `5.10`.

Floor also combines badly with binary floats. `_tax_for(0.29, 1.0)` multiplies to `28.999999999999996`, floors to `28`, and returns `0.28` instead of `0.29`. `_tax_for(2.9, 0.1)` has the same failure. So the result is a cent multiple by construction, but not a correctly rounded one, and the error can be a cent low even when the exact product lands on a cent boundary.

### 2. The total itself is never rounded

`invoice_total` (`app/billing.py:45-50`) adds the floored tax to an unrounded subtotal. `subtotal_for` and `invoice_total` both simply sum `qty * unit_price`; there is no per-line rounding there (unlike discounts). If prices carry more than two decimals, the total carries more than two decimals: `1 × 1.005` at `0.085` returns `1.085`, with `0.08` tax. Only presentation hides it — `utils.money(1.085)` prints `$1.08`.

The same leakage appears in `invoice_rows`: `tax` is stored as `total - subtotal`, not as the value `_tax_for` returned. For the `59.97` invoice the stored tax is `5.090000000000003`; the raw tax was `5.09`, and only `display_total` is formatted. Any caller reading the dict rather than the display string sees the float residue.

### 3. Discounts use half-even `round`

`apply_discount` (`app/billing.py:53-63`) applies `round(line["unit_price"] * factor, 2)` per unit, then the subtotal sums the already-rounded prices. Python's `round` is half-even and operates on the binary value, so `round(2.675, 2)` is `2.67`, not `2.68`; a `0%` discount still rewrites a `2.675` price to `2.67`. Discounting the subtotal instead would produce a different number by a cent or more. The architecture doc calls this deliberate because promotions are advertised per unit (`docs/architecture.md:127-130`).

### 4. Presentation uses two more, different rules

- `csv_rows` formats each amount with `f"{value:.2f}"` (`app/reports.py:67-69`). That is half-even on the binary value too: `f"{2.675:.2f}"` is `"2.67"`. `tax` is derived as `total - subtotal`, so the CSV shows the floored tax only after subtraction and formatting.
- `utils.money` uses `f"${value:,.2f}"` (`app/utils.py:34-38`), the same rule. It backs `display_total`, `summary_lines`, and the CLI `summary` output.
- `customer_totals` accumulates unrounded subtotals and totals per customer, sorts on the unrounded total, then applies `round(..., 2)` once to each accumulated subtotal and total (`app/reports.py:48-51`). This is the one place deliberately rounded after aggregation, so many small invoices are not penalised by repeated rounding — but it is still half-even, and it does not emit a tax column.
- `format_table`/`utils.pad` do no numeric rounding. They truncate text that exceeds the column width (`app/utils.py:187-192`), so a long amount is cut, not rounded.

### What this means end to end

`repro.py` demonstrates the visible consequence. For `3 × 19.99` at `0.085` it prints:

```
subtotal=59.97 tax=5.09 total=65.06 expected=65.07
```

The `65.07` is `Decimal` half-up applied once to the combined amount; the code instead floors the tax component and adds it to the subtotal. That one-cent gap is the floor-versus-half-up difference, not a config error, and it remains after this change: the requested work was the rate guard, not a rounding rewrite.

The report paths also differ in aggregation, not just formatting. `summary_lines` sums each invoice's already-floored total and then formats once, so the footer tax is the sum of per-invoice floored taxes, which need not equal `_tax_for(grand_subtotal, rate)`. `monthly_report` composes the same `csv_rows` body and `summary_lines` footer. `customer_totals` follows a separate accumulate-then-round path. The pipeline therefore agrees with the invoice screen on how each invoice total is computed (`invoice_total` is the single source), but it does not guarantee ledger-grade half-up behaviour, exact decimal arithmetic, or that a tax recomputed from a report subtotal matches the report's tax line.

No rounding behaviour was changed: `_tax_for` still floors, `invoice_total` still returns an unrounded sum, and the reproduction still prints `65.06` versus `65.07`.
````
