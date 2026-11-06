````
**1. What the monthly report pipeline does**

`reports.monthly_report(invoices, year, month, tax_rate)` is the entry point. It runs a four-stage pipeline:

1. **Filter** — `filter_month` parses each invoice's `issued` date and keeps only invoices from the requested year and month.
2. **Sort** — `sort_by_issued` orders the survivors oldest first.
3. **Flatten and render** — `export_csv_rows` turns each invoice into a flat dict (`customer`, `invoice`, `issued`, `subtotal`, `tax`, `invoice_total`) with amounts formatted to two decimals; `format_table` lays those rows out as a fixed-width text table using `CSV_COLUMNS` for header and column order (first column left-aligned, rest right-aligned).
4. **Summarise** — `summary_lines` adds invoice count, subtotal, tax and total, and the whole thing is joined under a "Monthly report for March 2026" heading.

All arithmetic is delegated to `app.billing`; `reports.py` only aggregates and formats. The module also provides `write_csv` for actual CSV file output and `customer_totals` for per-customer aggregation.

**2. Helpers `utils.py` provides to the pipeline**

`reports.py` imports `from app import billing, utils` and uses:

- `utils.parse_date` — by `filter_month` and `sort_by_issued` (accepts `date`/`datetime` or `YYYY-MM-DD` text).
- `utils.normalize_customer_name` — by `customer_totals` to tidy spacing and casing and reject blank names.
- `utils.pad` — by `format_table` to pad/truncate cells to column width.
- `utils.money` — by `summary_lines` to format amounts as `$1,234.50`.
- `utils.month_name` — by `monthly_report` for the heading.

Indirectly, `utils.pad` relies on `utils.truncate`, and `normalize_customer_name` relies on `utils.collapse_spaces`. The pipeline does not use the JSON/file helpers (`read_json`, `write_json`, `ensure_directory`), nor `slugify`, `group_by`, `chunked`, `month_bounds`, `in_month` or `month_label`.

**3. Change made**

I re-read the current `app/reports.py` before editing and confirmed it still had the old keys, then renamed the CSV export column in both required places:

- `CSV_COLUMNS`: `"total"` → `"invoice_total"`
- `export_csv_rows` row dict key: `"total"` → `"invoice_total"`

Verified with a sample invoice: the header is now `customer,invoice,issued,subtotal,tax,invoice_total` and the row emits `invoice_total`. `monthly_report` stays consistent because it renders from the same `CSV_COLUMNS`. I left the non-CSV `total` keys alone (in `customer_totals`, `summary_lines`, and the `Total:` footer line). The billing tests still pass (14 passed).

One unrelated issue I noticed while checking callers: `app/main.py` calls `reports.csv_rows(...)`, but `reports.py` defines `export_csv_rows`. The `export` CLI command would raise `AttributeError` today. That is pre-existing and I did not touch it.
````
