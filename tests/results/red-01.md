````markdown
# How an invoice total is calculated

## The one-line answer

`total = subtotal + tax`, where `subtotal = Σ(qty × unit_price)` across every line and `tax = floor(subtotal × tax_rate × 100) / 100`. All of the arithmetic lives in `app/billing.py`; the report and CLI layers only decide which invoices to feed in and how to print the result.

## Module boundaries

| Module | Owns | Must not |
| --- | --- | --- |
| `app/billing.py` | Invoice arithmetic: line amounts, subtotal, tax, total, discounts, validation | Import `app.reports`, format currency, print |
| `app/reports.py` | Selecting invoices, grouping, CSV rows, text tables | Recompute invoice amounts itself |
| `app/utils.py` | Money/date formatting, JSON/file helpers, padding | Know what an invoice is |
| `app/main.py` | Argument parsing, loading JSON, dispatch, exit codes | Contain business rules |

The dependency direction is one-way: `main → reports → billing → utils`. If you find yourself needing a new calculation in `reports.py`, add it to `billing.py` first.

## The data model

An invoice document is either a bare JSON list or an object with an `invoices` key (`main.load_invoices`, `app/main.py:16-25`). Each invoice is:

```json
{
  "id": "INV-1001",
  "customer": "Ada Ltd",
  "issued": "2026-03-04",
  "tax_rate": 0.085,
  "lines": [{"qty": 3, "unit_price": 19.99}]
}
```

`id`, `customer`, `issued` and `lines` are required. `tax_rate` is optional. Each line needs `qty` (positive) and `unit_price` (non-negative). Money is stored as plain floats — deliberately, to mirror the upstream service — so every calculation is binary floating point, and formatting to two decimals only happens at the edges.

## Start to finish, step by step

### 1. Entry point and loading

`python -m app.main <command> <path>` calls `main(argv)` (`app/main.py:102-113`), which builds the parser and dispatches to `args.func(args)`. Every command starts with `load_invoices`:

- `utils.read_json` opens the file as UTF-8 and calls `json.load`.
- A dict is unwrapped via `payload.get("invoices", [])`; anything else is treated as the list directly.
- A non-list result raises `ValueError`; a missing file raises `OSError`. Both are caught in `main()` and turned into exit code 1 with an `error:` prefix.

### 2. Choosing the tax rate

This happens per invoice, in four places, always with the same expression:

```python
rate = invoice.get("tax_rate", tax_rate)
```

(`billing.py:79`, `reports.py:39`, `reports.py:59`, `reports.py:123`)

Precedence is: **per-invoice `tax_rate` → rate passed by the caller (CLI `--tax-rate`) → `billing.DEFAULT_TAX_RATE` = `0.085`**. An explicit `0` is honoured because `.get` only falls back when the key is absent. An explicit `null` is *not* handled and will raise a `TypeError` during multiplication.

### 3. Subtotal

```python
def subtotal_for(lines):
    return sum(line["qty"] * line["unit_price"] for line in lines)
```

(`billing.py:22-24`)

One multiplication per line, summed left to right. No rounding, no per-line rounding, no validation. Direct indexing means a line missing `qty` or `unit_price` raises `KeyError` here (not the friendlier `ValueError` that `validate_lines` produces). An empty list returns the integer `0`.

### 4. Tax

```python
def _tax_for(subtotal, tax_rate):
    return math.floor(subtotal * tax_rate * 100) / 100
```

(`billing.py:27-29`)

This is the single most important line in the codebase. Read it as: convert the tax to cents, **throw away the fractional cent**, convert back to dollars. It is truncation toward negative infinity, not rounding. At 8.5% on a $59.97 subtotal the raw tax is $5.09745, which is 509.745 cents; `floor` gives 509 cents, i.e. **$5.09**, not $5.10.

For negative subtotals `floor` moves *away* from zero (e.g. `-0.86`), which only matters because validation is not enforced on the calculation path (see below).

### 5. Total

```python
def invoice_total(lines, tax_rate):
    subtotal = sum(line["qty"] * line["unit_price"] for line in lines)
    tax = _tax_for(subtotal, tax_rate)
    return subtotal + tax
```

(`billing.py:32-36`)

Note that it recomputes the subtotal inline rather than calling `subtotal_for`, so the sum expression exists twice (`billing.py:24` and `billing.py:34`). `invoice_total` never rounds the grand total; it adds a truncated tax to an unrounded subtotal. An empty line list returns `0.0` rather than raising.

### 6. Packaging the breakdown

`invoice_rows` (`billing.py:70-92`) is what the `summary` command uses. For each invoice it produces:

- `subtotal` from `subtotal_for`,
- `total` from `invoice_total`,
- `tax` as `total - subtotal` — derived, not recomputed, so despite the name it is a float subtraction rather than the exact `_tax_for` result (`-0.86` can come back as `-0.8599999999999994`),
- `display_total` from `utils.money(total)`, which is `f"${value:,.2f}"` (`utils.py:34-38`).

Because both subtotal and total are computed independently, the subtotal is summed twice per invoice on this path.

### 7. Aggregation and presentation

- `summary` (`main.py:28-38`) sums `row["subtotal"]` and `row["total"]` and prints count, subtotal, tax (`total - subtotal`) and total through `utils.money`.
- `report` (`main.py:41-45`) goes through `reports.monthly_report`: `filter_month` keeps invoices whose parsed `issued` date matches the year and month, `sort_by_issued` orders oldest first, `csv_rows` formats each row with `f"{value:.2f}"`, `format_table` pads it, and `summary_lines` recomputes count/subtotal/tax/total from the *raw* underlying values.
- `export` (`main.py:48-54`) uses `csv_rows` plus `write_csv` with the fixed `CSV_COLUMNS` order.
- `validate` (`main.py:57-71`) is the only command that calls `billing.validate_lines`.

## A worked example

`repro.py` calculates one invoice: 3 × $19.99 at 8.5%.

1. Subtotal: `3 × 19.99 = 59.97`.
2. Raw tax: `59.97 × 0.085 = 5.09745`.
3. In cents: `509.745`.
4. Truncate: `509` cents → tax `5.09`.
5. Total: `59.97 + 5.09 = 65.06`.

`repro.py` compares that with a `Decimal`-based expectation: `59.97 × 1.085 = 65.06745`, rounded half-up to the cent → **65.07**. Hence the reported one-cent gap:

```
subtotal=59.97 tax=5.09 total=65.06 expected=65.07
```

There are three separate reasons it can differ from a "correct" total:

1. **Direction:** tax is truncated, never rounded up, so the error is always downward and accumulates across many invoices.
2. **Where rounding happens:** the code rounds the tax separately and then adds it to an unrounded subtotal, rather than rounding the grand total once. These are not equivalent (e.g. a subtotal of 1.005 at 8.5% gives 1.10 if you round each part, 1.09 if you round the total).
3. **Binary floats:** `59.97`, `19.99` and `0.085` are not exactly representable, so intermediate values are only approximately the decimal ones.

Over random subtotals, truncation disagrees with half-up rounding roughly half the time (about 4,978 in 10,000 in a quick sample of $1–$1,000 invoices at 8.5%).

## A second trap: displayed columns need not add up

Take a line of `2 × 10.00` plus `1 × 5.555` at 8.5%:

- raw subtotal `25.555` → CSV shows `25.55` (binary value is just below the half-way point),
- raw tax `2.172175` → floored to `2.17`,
- raw total `27.725` → formats as `27.73`.

So the exported row reads `25.55, 2.17, 27.73`, and `25.55 + 2.17 = 27.72`. Each cell is rounded independently from the raw float; nothing reconciles them. The report footer is computed from the raw values, so it can also disagree with the visible column sum.

## Discounts

`apply_discount(lines, percent)` (`billing.py:39-49`) validates `0 ≤ percent ≤ 100`, computes `factor = 1 - percent/100`, copies each line (the input is never mutated), and stores `round(unit_price * factor, 2)`. Two things to know:

- It is **not wired into any calculation path or CLI command**. Callers must apply it before calling `invoice_total`; `invoice_total` itself knows nothing about discounts.
- It uses Python's `round`, which is banker's rounding on a binary float, so even a 0% discount can change a price: `round(1.005, 2) == 1.00`.

Rounding at the line level is intentional — promotions are advertised per unit — but it means discounting then taxing can differ from taxing then discounting.

## Validation, and where it does *not* run

`validate_lines` (`billing.py:52-67`) rejects an empty list, missing `qty`/`unit_price`, `qty <= 0`, and `unit_price < 0`, returning the same list on success. It is only invoked by the `validate` command. `summary`, `report` and `export` never call it, so zero quantities, negative prices and missing fields flow straight into the arithmetic (or raise `KeyError`). The architecture doc's "step 1: validate_lines" describes intent, not the summary path.

Also note the asymmetry: `invoice_total([])` happily returns `0.0`, while `validate_lines([])` raises.

## Tax-rate gotchas in the CLI

- `--tax-rate` is a *global* option and argparse requires it **before** the subcommand: `python -m app.main --tax-rate 0.1 report inv.json --year 2026 --month 3`. After the subcommand it is an "unrecognized arguments" error.
- `command_summary` calls `billing.invoice_rows(invoices)` **without** passing `args.tax_rate` (`main.py:31`), so `--tax-rate` is silently ignored by `summary` but honoured by `report` and `export`. That is a genuine inconsistency, not intended behaviour.
- Per-invoice overrides always win, including over an explicitly supplied CLI rate.

## Who calls what

| Caller | Path |
| --- | --- |
| `summary` | `invoice_rows` → `subtotal_for`, `invoice_total`, `utils.money` |
| `report` | `filter_month` → `sort_by_issued` → `csv_rows` → `format_table` → `summary_lines` |
| `export` | `csv_rows` → `write_csv` |
| `validate` | `validate_lines` |

`line_total`, `apply_discount` and `customer_totals` exist and are tested or documented, but no CLI command reaches them. `customer_totals` rounds only after accumulating all invoices for a customer, which is the one place the code deliberately avoids per-invoice rounding drift.

## Practical rules for changing this code

- Change the tax policy in `_tax_for` only — but remember `invoice_total` also owns the subtotal expression, so keep the two in sync if you refactor.
- If you move to `Decimal`, convert at the boundary (`utils.parse_money`/`read_json`) and quantize with an explicit rounding mode; that will change every total in the fixture and should come with new tests.
- `tests/test_billing.py` has 14 tests. They cover the happy path (`pytest.approx`), discount bounds and validation, but nothing pins the truncation direction, the `tax = total - subtotal` derivation, the `--tax-rate` pass-through, or the CLI at all. Add tests there before touching rounding.
- To see the discrepancy yourself: `python repro.py`. To see the whole pipeline: `python -m app.main summary <file>`, `report --year Y --month M`, `export --out out.csv`.

## Glossary

- **Line**: `qty × unit_price`, pre-tax, unrounded.
- **Subtotal**: sum of line amounts.
- **Tax rate**: a fraction (`0.085` = 8.5%), applied to the subtotal.
- **Tax**: subtotal × rate, truncated down to whole cents.
- **Total**: subtotal + tax (not rounded again).
````
