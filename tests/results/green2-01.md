``
**An invoice total is `subtotal + tax`, where `subtotal = Σ(qty × unit_price)` and `tax = floor(subtotal × tax_rate × 100) / 100`.** Amounts are Python floats throughout, and tax is truncated down to whole cents rather than rounded half-up. That is why the bundled reproduction prints `subtotal=59.97 tax=5.09 total=65.06 expected=65.07` (`repro.py:13-28`).

## 1. The data arrives through the CLI

`app/main.py:16-25` loads a JSON document with `utils.read_json`. It accepts either `{"invoices": [...]}` or a bare list, and only checks that the result is a list. There is no schema validation at load time. The four commands then select an invoice path: `summary`, `report`, `export`, and `validate` (`main.py:28-71`). The document-level default tax rate is `0.085` (`billing.py:11`); the CLI exposes a global `--tax-rate` with that default (`main.py:77-78`).

`load_invoices` does not call `billing.validate_lines`; only the `validate` command does (`main.py:57-71`). So `summary`, `report`, and `export` compute on whatever lines they are given, and a missing `qty` or `unit_price` surfaces as a `KeyError` rather than the friendly `ValueError` that `validate_lines` produces (`billing.py:52-67`).

## 2. Line amount and subtotal

`billing.line_total` (`billing.py:15-19`) returns `qty * unit_price`, defaulting each missing field to zero. `billing.subtotal_for` (`billing.py:22-24`) sums the same product over all lines, but indexes the fields directly. `invoice_total` repeats that sum inline (`billing.py:34`) instead of calling `subtotal_for`; the arithmetic is identical, just duplicated.

Nothing is rounded at line or subtotal level. A quantity of 3 at 19.99 contributes `59.97` as a float, and all line amounts are accumulated at full float precision.

## 3. Tax

`_tax_for` (`billing.py:27-29`) is the only taxpayer:

```
math.floor(subtotal * tax_rate * 100) / 100
```

For the example, `59.97 × 0.085 = 5.09745`; multiplying by 100 and flooring gives 509, so tax is `5.09`. Half-up rounding would give `5.10`. This floor is the source of the reported one-cent discrepancy.

Rate precedence is: a per-invoice `tax_rate` overrides the rate passed into the calculation, which defaults to `DEFAULT_TAX_RATE`. That lookup appears in `invoice_rows` (`billing.py:79`), `customer_totals` (`reports.py:39`), `csv_rows` (`reports.py:59`), and `summary_lines` (`reports.py:122-125`). One caveat: `command_summary` calls `billing.invoice_rows(invoices)` without forwarding `args.tax_rate` (`main.py:31`), so `--tax-rate` has no effect on `summary`. I verified that `--tax-rate 0.2 summary` still produced the 8.5% numbers. `report` and `export` do forward the CLI rate (`main.py:44`, `main.py:51`).

## 4. Adding it up

`invoice_total` simply returns `subtotal + tax` (`billing.py:32-36`). An empty line list returns `0.0`, since the sum and tax are both zero.

From there the calculation fans out:

- `invoice_rows` packages `subtotal`, `tax = total - subtotal`, `total`, and `display_total` (`billing.py:70-92`). Deriving tax by subtraction guarantees the row adds up even if `_tax_for` changes.
- `command_summary` sums the row subtotals and row totals, then prints the difference as tax (`main.py:31-37`).
- `reports.csv_rows` recalculates each invoice and formats each amount with `f"{value:.2f}"` for the table and CSV (`reports.py:55-72`).
- `reports.customer_totals` accumulates unrounded subtotals and totals per normalised customer, sorts by descending total, then rounds each aggregate once at the end (`reports.py:30-52`). Individual invoice totals inside those aggregates already contain floored tax.
- `reports.summary_lines` sums per-invoice subtotals and totals for the report footer (`reports.py:119-131`).

`utils.money` (`utils.py:34-38`) is formatting only: `$1,234.50` for USD. It does not alter the stored value.

## 5. Discounts, if any

`apply_discount` (`billing.py:39-49`) validates that the percent is between 0 and 100, copies every line, multiplies `unit_price` by `1 - percent/100`, and rounds each discounted unit price to two decimals. Subtotal and tax then run on those discounted prices, so discounts are applied before tax and rounded at the line level. No current CLI command calls this helper.

## 6. Worked example, start to finish

Invoice `3 × 19.99` at 8.5%:

1. Subtotal: `3 × 19.99 = 59.97`.
2. Raw tax: `59.97 × 0.085 = 5.09745`.
3. Floored tax: `math.floor(509.745) / 100 = 5.09`.
4. Total: `59.97 + 5.09 = 65.06`.
5. `repro.py` instead computes the gross `59.97 × 1.085 = 65.06745` and rounds that half-up to `65.07`.

The gap is not float noise; it is two different policies. The implementation floors the tax and adds it, while the reproduction rounds the gross total. For `100 × 1.085` both policies give `108.50`. The 14 tests pass (`python -m pytest tests -q`) because they use amounts where the policies agree and compare with `pytest.approx` (`tests/test_billing.py:20-27`), so the discrepancy is untested.

## 7. If you change the rounding

Change it in `_tax_for` only; every higher layer reaches tax through `invoice_total`. Switching to `Decimal` or half-up affects stored totals, CSV output, report footers, and customer aggregates for existing documents, so treat it as a behavioural change, not a formatting fix. The ignored `--tax-rate` on `summary` is a separate defect at `main.py:31` and would need its own fix.
``
