````
An invoice total is `subtotal + tax`, where the tax is **floored to the cent**, not rounded:

```python
subtotal = sum(qty * unit_price for each line)   # floats, no rounding
tax      = math.floor(subtotal * rate * 100) / 100
total    = subtotal + tax
```

That is all of it. `billing.invoice_total` (app/billing.py:32-36) is the single producer; every other total — summary, monthly report, CSV — is a sum or a reformat of its output. What follows is how values reach it and where it bites.

## The path, start to finish

Entry point: `python -m app.main [--tax-rate RATE] <command> <path> [options]` (app/main.py:74-113).

1. `main()` parses args; `load_invoices` (main.py:16) reads UTF-8 JSON via `utils.read_json` and accepts either `{"invoices": [...]}` or a bare list. It only checks that the result is a list — no line validation.
2. `summary` (main.py:28) calls `billing.invoice_rows(invoices)` (billing.py:70). Per invoice: `subtotal_for` sums `qty * unit_price` (billing.py:22), `invoice_total` computes the floored tax and adds it, then the row stores `subtotal`, `tax = total - subtotal`, `total`, and `display_total = utils.money(total)`. `command_summary` sums the rows and prints count/subtotal/tax/total.
3. `report` (main.py:41) → `reports.monthly_report` (reports.py:134): `filter_month` on `issued`, `sort_by_issued`, `csv_rows` (which repeats the same `subtotal_for`/`invoice_total` pair and formats each to 2 dp), `format_table`, then `summary_lines` — which **recomputes** subtotal and total from the raw invoices rather than adding the table cells.
4. `export` (main.py:48) is `csv_rows` + `write_csv`; `validate` (main.py:57) is the only caller of `validate_lines` and is not on any total path.

Rate resolution happens at the edges, not inside `invoice_total`: `invoice["tax_rate"]` if present, else the rate the caller passed, else `billing.DEFAULT_TAX_RATE = 0.085` (billing.py:11). See billing.py:79, reports.py:39/59/123. Rates are fractions: `0.085` means 8.5%.

## One invoice by hand (INV-1001)

3 × $19.99 at 8.5%:

```
subtotal = 3 * 19.99             = 59.97
tax      = floor(59.97 * 0.085 * 100) / 100
         = floor(509.745) / 100  = 5.09      # .745 discarded
total    = 59.97 + 5.09          = 65.06
```

`python repro.py` prints `subtotal=59.97 tax=5.09 total=65.06 expected=65.07`; `expected` applies `ROUND_HALF_UP` to the tax-inclusive amount. The one-cent gap is the floor, not a bug in `repro.py`.

## Traps

**Flooring.** `_tax_for` (billing.py:27) truncates, so tax is never overstated and up to $0.01 per invoice is understated. On a $0.10 line at 8.5% it charges $0.00 (verified). Monthly totals sum per-invoice floored tax, so the error accumulates across invoices instead of cancelling.

**`--tax-rate` only half works.** It is a global option and must precede the subcommand (`python -m app.main --tax-rate 0.1 summary f.json`); after it, argparse errors. Worse, `command_summary` calls `invoice_rows(invoices)` without `args.tax_rate` (main.py:31), so summary ignores it entirely: on one file, default and `--tax-rate 0.1` both printed Total $89.06, while `report` with 0.1 printed $89.96. `report` and `export` do pass it. architecture.md:123-125 and :160 claim otherwise.

**Nothing validates before totalling.** architecture.md:115 says validation runs first; no totals path calls it. A `qty: 0` invoice is included at $0.00 in summary and report (ran it: `INV-BAD ... 0.00 | 0.00 | 0.00`), and a line missing `unit_price` raises `KeyError` — not caught by the `(OSError, ValueError)` handler at main.py:111, so users get a traceback (verified).

**Discounts are not in the total.** `apply_discount` (billing.py:39) is tested but has no caller in `app/`; nothing in the CLI applies a promotion. If you call it, do so before `invoice_total`: it returns copied lines with `unit_price` rounded to cents per unit (billing.py:47), which changes the taxable base.

**Empty vs invalid.** `invoice_total([])` and `subtotal_for([])` return 0; `validate_lines([])` raises "an invoice needs at least one line". Summary prints 0 for an empty invoice; validate fails it.

**Formatting is not rounding.** `utils.money` (utils.py:34) only formats; stored values keep float residue (`65.06000000000001`, and `tax = 5.090000000000003`). Two display paths exist: `utils.money` for footer rows, f-string `:.2f` for CSV and table cells.

**Report footer ≠ column sum.** Because `summary_lines` recomputes from raw floats, a report of three 1 × $0.333 invoices shows 0.35 in each total cell ($1.05 as displayed) but a footer Total of $1.06; subtotal cells sum to 0.99, footer says $1.00 (verified). Reconciling the printed table can be off by cents.

**The line helpers disagree.** `line_total` (billing.py:15) defaults absent `qty`/`unit_price` to 0; `subtotal_for` uses `line["..."]` and raises. `line_total` is unused by the app.

**BOM.** `read_json` opens `encoding="utf-8"`, not `utf-8-sig`; a BOM (PowerShell 5.1 `Set-Content -Encoding utf8`) makes every command fail with "Unexpected UTF-8 BOM" (verified).

**Float money.** Deliberate, documented at architecture.md:240-242; no `Decimal` in the calculation.

## Coverage

`python -m pytest tests -q` → 14 passed. All are in `tests/test_billing.py`; they assert current behaviour (e.g. 2 × $20 at 8.5% = $43.40), none distinguishes floor from half-up, and there are no CLI or report tests. `reports.customer_totals` has no caller and no test. The flooring, the ignored summary flag and the unvalidated total path are therefore unguarded.
````
