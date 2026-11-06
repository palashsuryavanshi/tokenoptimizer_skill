````
**Pipeline** (`app/reports.py`) — `monthly_report()` (reports.py:134) is the entry point; it does no arithmetic itself, all money comes from `app.billing`:

1. `filter_month()` (reports.py:15) parses each `issued` value with `utils.parse_date` and keeps only matching year/month.
2. `sort_by_issued()` (reports.py:25) orders those invoices oldest-first by the same parsed date.
3. `export_csv_rows()` (reports.py:55) flattens each invoice: `billing.subtotal_for(lines)`, `billing.invoice_total(lines, rate)` where `rate` is the invoice's own `tax_rate` or the passed default, and `tax = total - subtotal`; all values are two-decimal strings keyed by `CSV_COLUMNS`.
4. `format_table(rows, CSV_COLUMNS)` (reports.py:86) sizes each column to its widest cell and pads it via `utils.pad` — first column left-aligned, the rest right-aligned.
5. `summary_lines()` (reports.py:119) sums subtotal and total over the selected invoices and formats them with `utils.money`.
6. The final string is heading (`utils.month_name(month)`), an `=` underline, blank line, table, blank line, then the four summary lines (reports.py:140).

`write_csv()` (reports.py:75) is the separate file writer behind the CLI `export` command, and `customer_totals()` (reports.py:30) is an independent per-customer aggregation that `monthly_report` never calls.

**Helpers used from `app/utils.py`**: `parse_date` (filter and sort), `pad` (table rendering; it calls `truncate`), `money` (summary lines), `month_name` (heading), and `normalize_customer_name` (`customer_totals` only; it calls `collapse_spaces`). No other utils function is reached from reports. Reports also depends on `billing.subtotal_for`, `billing.invoice_total`, and `billing.DEFAULT_TAX_RATE`.

**Change made** (`app/reports.py`): the `CSV_COLUMNS` entry and the `export_csv_rows` row key are now `invoice_total`. Before: `['customer', 'invoice', 'issued', 'subtotal', 'tax', 'total']` and the row key was `total`; after: the last column and key are `invoice_total` (reports.py:12, reports.py:69). `python -m pytest -q` → 18 passed. CLI check: `python -m app.main export inv.json --out out.csv` wrote header `customer,invoice,issued,subtotal,tax,invoice_total` and row `Ada Ltd,INV-1,2026-03-14,100.00,8.50,108.50`.

Two things to flag:
- Your intervening edit (reports.py mtime 21:19) left `app/main.py:51` calling `reports.csv_rows`, a name that no longer exists, so `python -m app.main export` raised `AttributeError` before my change. I pointed it at `reports.export_csv_rows`; otherwise the export path stayed dead. Files changed beyond the request: `app/main.py` (one-line fix) and new regression tests in `tests/test_reports.py`.
- This is a breaking CSV schema change: any consumer reading the `total` header or key must switch to `invoice_total` (`docs/changelog.md:134` notes `CSV_COLUMNS` is a constant downstream consumers rely on). The monthly report's text table header changes as well, since it is rendered from `CSV_COLUMNS`. The `total` key returned by `customer_totals()` is untouched.
````
