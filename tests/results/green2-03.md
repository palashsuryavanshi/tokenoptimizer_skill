````
CSV export now uses `invoice_total` for both the header and row key in `app/reports.py` (lines 12 and 69).

**Monthly report pipeline.** `monthly_report()` (`app/reports.py:134`) filters invoices by `issued` month, sorts them oldest-first, renders a heading from `utils.month_name(month)`, formats per-invoice rows into a table, and appends summary lines. `filter_month()` parses each date; `export_csv_rows()` computes subtotal and total per invoice via `billing.subtotal_for()`/`billing.invoice_total()`, applying a per-invoice `tax_rate` when present; `format_table()` pads columns; `summary_lines()` totals invoices, subtotal, tax, and total.

**utils.py dependencies.** `parse_date()` (filtering and sorting), `month_name()` (heading), `pad()` (table rendering), and `money()` (summary formatting). `customer_totals()` additionally uses `normalize_customer_name()`.

**Change and proof.** I re-read the current file before editing. `CSV_COLUMNS` now ends with `invoice_total`, and the row dict uses that key. A direct export produced:
`customer,invoice,issued,subtotal,tax,invoice_total`
`Ada Ltd,INV-1,2026-03-02,100.00,8.50,108.50`
The full suite passes: `14 passed in 0.03s`.

Caveat: `monthly_report()` reuses `CSV_COLUMNS` for `format_table()` (`app/reports.py:138`), so its text-table header also changed to `invoice_total`. Existing callers reading `export_csv_rows()[...]["total"]` must use `["invoice_total"]`; `customer_totals()` and `billing.invoice_rows()` were not changed.
````
