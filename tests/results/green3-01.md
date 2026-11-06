````markdown
**Answer: `total = subtotal + tax`, where `subtotal = Σ(qty × unit_price)` and `tax = floor(subtotal × rate × 100) / 100` — truncated to the cent, never rounded. On `3 × 19.99` at 8.5% that is `59.97 + 5.09 = 65.06`, one cent under the `65.07` a half-up rule gives.**

## The path, end to end

Entry is `app/main.py:102` (`main`) → argparse → one command function → `load_invoices` → `app.billing`.

1. **Load** — `main.load_invoices` (`app/main.py:16`) reads UTF-8 JSON through `utils.read_json` (`app/utils.py:157`) and accepts either a bare list or `{"invoices": [...]}`. No arithmetic and no per-field validation here.
2. **Subtotal** — `billing.subtotal_for` (`app/billing.py:22`) sums `qty * unit_price` over every line, indexing `line["qty"]` / `line["unit_price"]` directly.
3. **Tax** — `billing._tax_for` (`app/billing.py:27`) evaluates `math.floor(subtotal * tax_rate * 100) / 100`. Floats, truncation.
4. **Total** — `billing.invoice_total` (`app/billing.py:32`) recomputes the same sum inline (`:34`), calls `_tax_for`, returns `subtotal + tax`. `tax_rate` is positional and has no default.
5. **Shape** — two parallel presenters over the same arithmetic:
   - `billing.invoice_rows` (`:70`) → `{subtotal, tax: total - subtotal, total, display_total}`; used by `main.command_summary` (`app/main.py:28`).
   - `reports.csv_rows` (`app/reports.py:55`) → amounts as `f"{x:.2f}"` strings; used by `export` and by `monthly_report` (`:134`), which filters the month, sorts oldest first, renders a table and appends a footer from `reports.summary_lines` (`:119`).
   - `reports.customer_totals` (`:30`) accumulates raw subtotal/total per normalised customer, then rounds once after accumulation (`:50-51`).
6. **Format** — `utils.money` (`app/utils.py:34`) produces `$1,234.50` for stdout; CSV and table cells use `f"{x:.2f}"` with no symbol. Formatting happens only at the edge; nothing is rounded before arithmetic.

The tax figure is never stored: the summary and the report footer derive it as `total - subtotal` (`app/billing.py:87`, `app/reports.py:129`), which is exactly the floored tax.

## Where the rate comes from

Resolved per invoice, at each call site:

1. `invoice["tax_rate"]` when the key is present — `invoice.get("tax_rate", default)`, so a `0` rate is honoured;
2. the caller's `tax_rate` argument;
3. `billing.DEFAULT_TAX_RATE = 0.085` (`app/billing.py:11`).

On the CLI, `--tax-rate` is a *global* option (`app/main.py:77`) and must precede the subcommand. `python -m app.main summary inv.json --tax-rate 0.1` fails with `unrecognized arguments`.

## Worked example (verified)

Invoice `{"id": "INV-1001", "lines": [{"qty": 3, "unit_price": 19.99}]}`, default 8.5%:

```
python -m app.main summary inv.json
Invoices: 1
Subtotal: $59.97
Tax: $5.09
Total: $65.06
```

- subtotal = `3 × 19.99 = 59.97`
- tax = `59.97 × 0.085 = 5.09745` → floor to `5.09` (half-up would give `5.10`)
- total = `59.97 + 5.09 = 65.06`

`python repro.py` prints the same split: `subtotal=59.97 tax=5.09 total=65.06 expected=65.07`.

## Traps a newcomer hits

1. **Tax truncates.** This is the source of every one-cent discrepancy reported here; `repro.py` exists to show it. Changing it changes exported spreadsheets and needs the billing team (`docs/changelog.md:399`).
2. **Tax is floored per invoice, not per document.** The summary adds already-floored per-invoice taxes, so a document total is not `floor(Σsubtotals × rate)`.
3. **`summary` silently ignores `--tax-rate`.** `command_summary` calls `billing.invoice_rows(invoices)` with no rate (`app/main.py:31`), so the default is always `0.085`. A per-invoice `tax_rate` still wins. `report` and `export` do pass `args.tax_rate` (`:44`, `:51`). Verified: `--tax-rate 0.1 summary` still prints `5.09`; the same flag on `report` prints `5.99`.
4. **`invoice_total` duplicates `subtotal_for` inline** (`app/billing.py:34` vs `:24`). Rounding added to `subtotal_for` would silently stop reaching the total.
5. **`summary`, `report` and `export` never validate.** A line missing `unit_price` raises an uncaught `KeyError` from `subtotal_for` and dumps a traceback; only `validate` (`app/main.py:57`) reports it as `INV-3: line 0 is missing qty or unit_price` with exit 1. `line_total` (`:15`) uses `.get` defaults and therefore disagrees with `subtotal_for` on malformed input.
6. **Empty invoices diverge by command.** `invoice_total([], rate)` returns `0.0` (tested), but `validate_lines` rejects an empty list (`app/billing.py:58`): summary prints `$0.00`, validate fails. Both are intended (`docs/architecture.md:132`).
7. **Discounts are not wired into any invoice path.** `apply_discount` (`:39`) is reached only from tests. Where used, it reduces the *unit* price and rounds per unit with Python's banker's `round` (`:47`) before `qty` multiplies — 100 units at `0.125` with 50% off becomes `100 × 0.06`, not one rounding of `6.25`.
8. **`customer_totals` rounds once after accumulation** while invoice rows round individually, so a customer total need not equal the sum of the invoice totals listed for that customer.
9. **Money is float throughout.** `utils.read_json` rejects a UTF-8 BOM (`Unexpected UTF-8 BOM`), which PowerShell's `Set-Content -Encoding utf8` writes — save input JSON without a BOM.
10. **The README paths are stale.** `tests/fixture/...` and `cd tests/fixture` do not exist in this checkout. From the repo root: `python -m pytest tests -q` (14 passed) and `python -m app.main <command> ...`. `conftest.py` puts the root on `sys.path`; `repro.py` inserts its own directory.

Exit codes: `0` success, `1` handled error (`error: ...` on stderr) or uncaught exception, `2` no subcommand supplied.
````
