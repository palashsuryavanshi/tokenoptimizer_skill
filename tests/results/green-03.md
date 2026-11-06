````
**1. Monthly report pipeline** (`app/reports.py:134-140`)

`monthly_report(invoices, year, month, tax_rate=0.085)`:
1. `filter_month` keeps invoices whose `issued` date parses into the requested year/month (`reports.py:15-22`).
2. `sort_by_issued` orders the survivors oldest first (`:25-27`).
3. Heading: `"Monthly report for <Month> <Year>"`, underlined with `=` (`:137`).
4. Body: `export_csv_rows` converts each invoice to a flat row — subtotal via `billing.subtotal_for`, total via `billing.invoice_total`, tax as total minus subtotal, money values as 2-dp strings, per-invoice `tax_rate` overriding the default (`:55-72`). `format_table` renders those rows using `CSV_COLUMNS`, first column left-aligned, rest right-aligned (`:86-116`).
5. Footer: `summary_lines` sums subtotal and total across the selected invoices and prints invoice count, subtotal, tax, total (`:119-131`).

All amounts come from `app.billing`; the report layer does no arithmetic of its own except tax subtraction and footer summation.

**2. `utils.py` helpers used**
- `parse_date` — month filtering and sorting (`reports.py:19,27`; `utils.py:128`).
- `month_name` — heading (`reports.py:137`; `utils.py:144`).
- `pad` — table cell alignment and truncation (`reports.py:103,110`; `utils.py:187`).
- `money` — footer amounts (`reports.py:128-130`; `utils.py:34`).
- `normalize_customer_name` — only in `customer_totals`, not `monthly_report` (`reports.py:38`; `utils.py:79`); it calls `collapse_spaces`.

**3. CSV column rename**
I read the current 140-line `reports.py` immediately before editing; there is no baseline copy to diff, so I cannot identify what your edit changed. Changed `app/reports.py:12` (`CSV_COLUMNS` last entry) and `app/reports.py:69` (row key), so both header and rows use `invoice_total`:
`customer,invoice,issued,subtotal,tax,invoice_total`
`Acme,INV-1,2026-03-02,100.00,10.00,110.00`
`pytest`: 14 passed.

Side effect to name: `CSV_COLUMNS` also feeds `format_table` in `monthly_report` (`:138`), so the printed monthly table header changes too; `customer_totals`, `summary_lines`, and `main.py` are untouched.
````
