````
**1. What the monthly report pipeline does**

`reports.monthly_report` (`app/reports.py:135-144`) is the pipeline; the CLI `report` command calls it at `app/main.py:44`.

1. `filter_month` (`app/reports.py:15-22`) parses each invoice's `issued` with `utils.parse_date` and keeps those whose year and month match. It does its own field check, so `utils.in_month`/`month_bounds` are never used here.
2. `sort_by_issued` (`:25-27`) sorts survivors oldest first, parsing the date a second time.
3. `export_csv_rows` (`:56-73`) flattens each invoice: `billing.subtotal_for` for the pre-tax sum, `billing.invoice_total` for the amount due, and `tax` is derived as `total - subtotal`. A per-invoice `tax_rate` overrides the argument, which defaults to `billing.DEFAULT_TAX_RATE` (0.085). Tax is floored to cents inside `billing._tax_for` (`app/billing.py:29`), so the `tax` column is the floored value, not a straight percentage of the subtotal. Amounts become two-decimal strings here, at the edge.
4. `format_table` (`:86-117`) sizes each column from header plus values, truncates/pads with `utils.pad`, left-aligns the first column and right-aligns the rest, and joins with `" | "`.
5. `summary_lines` (`:119-131`) recomputes subtotal and total over the whole selection (it does not sum the rows) and formats count, subtotal, tax and total with `utils.money`.
6. Everything is joined under `"Monthly report for <month> <year>"` with an `=` underline.

The report layer does no arithmetic of its own; every amount comes from `billing`, which is why report numbers match the invoice screens. `customer_totals` (`:30-52`) is a separate path, not part of the monthly report.

**2. utils.py helpers the pipeline depends on**

In the monthly report path:
- `utils.parse_date` — `reports.py:19`, `:27`
- `utils.month_name` — `reports.py:138`
- `utils.pad` — `reports.py:103`, `:110`; it calls `utils.truncate` (`app/utils.py:187-192`)
- `utils.money` — `reports.py:128-130`

Used by the report module but not the monthly report: `utils.normalize_customer_name` in `customer_totals` (`reports.py:38`), which pulls in `utils.collapse_spaces`.

Never used by `reports.py`: `parse_money`, `format_percent`, `clamp`, `is_blank`, `slugify`, `unique_preserving_order`, `group_by`, `chunked`, `month_bounds`, `month_label`, `in_month`, `read_json`, `write_json`, `ensure_directory`. `in_month` is the near-miss: it already does what `filter_month` does by hand, but nothing calls it.

**3. Change: CSV `total` → `invoice_total`**

In `app/reports.py` (the version saved at 21:58:26 — I re-read it immediately before editing and it was unchanged from that save):
- `CSV_COLUMNS` now ends `"invoice_total"` (`:12`).
- `export_csv_rows` emits the `"invoice_total"` key (`:70`).
- Added `TABLE_COLUMNS` (`:13`) and `monthly_report` maps the row for the printed table (`:139-142`), so the text report still renders a `total` header — you asked for the CSV export only.

Actual run:
```
row keys: ['customer', 'invoice', 'issued', 'subtotal', 'tax', 'invoice_total']
--- CSV file ---
customer,invoice,issued,subtotal,tax,invoice_total
Ada Ltd,INV-1,2026-03-04,59.97,5.09,65.06
Bob Inc,INV-2,2026-03-31,100.00,10.00,110.00
--- report table header ---
customer | invoice |     issued | subtotal |   tax |  total
```
Before the change the header and row key were both `total` (`reports.py:12` and `:69` pre-edit). `python -m pytest -q` → `14 passed in 0.03s`.

Caveat: this renames a documented header contract (`docs/changelog.md:134`, `docs/architecture.md:151-155`), so anything reading the `total` column breaks until it reads `invoice_total`.

Pre-existing and untouched: the CLI `export` command is already broken. `app/main.py:51` calls `reports.csv_rows`, which does not exist (the function is `export_csv_rows`), so `python -m app.main export ...` dies with an uncaught `AttributeError: module 'app.reports' has no attribute 'csv_rows'`; `docs/architecture.md:142` carries the same stale name. Outside the rename, so I left it — say so if you want it fixed.
````
