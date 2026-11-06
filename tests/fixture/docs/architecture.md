# Architecture

## Purpose

The fixture application is a deliberately small invoicing service. It exists to
demonstrate the shape of a real codebase: a domain module, a reporting module, a
utility layer and a command line entry point, each with its own vocabulary and
its own reasons to change. Nothing here is generated; every line is meant to be
read by a person.

The application answers three questions:

1. What does a single invoice add up to?
2. What did a given month look like across all customers?
3. Which invoices are malformed and should be held back?

The answers live in `app/billing.py`, `app/reports.py` and `app/main.py`
respectively. Shared formatting and date handling lives in `app/utils.py`.

## System context

The fixture has no network access, no database and no scheduled jobs. It is a
library plus a command line wrapper. The only inputs are JSON documents and the
only outputs are text on stdout plus optional CSV files. This keeps the
scenarios focused on reading and changing code rather than on infrastructure.

A production version of the same design would add:

- a database adapter behind the invoice loader,
- an HTTP layer that exposes the same report functions,
- a queue consumer that recalculates totals when a rate changes,
- an audit log for every mutation.

None of that exists in the fixture. Those concerns are described here only so
that a new developer understands which seams were left open on purpose.

## Module map

### `app/billing.py`

Owns the arithmetic. It exposes:

- `line_total(line)` for a single line,
- `subtotal_for(lines)` for the pre-tax sum,
- `invoice_total(lines, tax_rate)` for the amount due,
- `apply_discount(lines, percent)` for promotional pricing,
- `validate_lines(lines)` for structural checks,
- `invoice_rows(invoices, tax_rate)` for the report layer.

The module imports only `math` and `app.utils`. It must not import
`app.reports`; the dependency direction is strictly one way. If a change to the
report layer requires a new billing helper, the helper is added here first and
then used from above.

### `app/reports.py`

Turns invoices into presentable output. It filters by month, groups by
customer, builds CSV rows and renders fixed width tables. It never performs
invoice arithmetic itself. Every amount it prints comes from a `billing`
function, which is what keeps the invoice screen and the monthly statement in
agreement.

Report functions accept plain lists of dictionaries. They do not know where the
data came from, which makes them easy to call from tests and from the CLI.

### `app/utils.py`

The utility layer has no domain knowledge. It formats money, parses dates,
normalises customer names, groups and chunks sequences, reads and writes JSON,
and pads text for the table renderer. Utility functions are pure wherever
possible; the file helpers are the only functions that touch the filesystem.

Keeping this layer domain free is important. As soon as a helper starts talking
about invoices it belongs in `billing.py` instead.

### `app/main.py`

The command line entry point. It parses arguments, loads the invoice document,
dispatches to a command function and translates exceptions into exit codes.
Argument parsing is separated from dispatch so the command functions can be
tested without going through `sys.argv`.

### `app/__init__.py`

A package marker with a docstring. There is no package level state.

## Data model

An invoice document is a JSON object with a single `invoices` key, or a bare
list. Each invoice has:

| Field      | Type            | Required | Notes                          |
| ---------- | --------------- | -------- | ------------------------------ |
| `id`       | string          | yes      | Unique within the document     |
| `customer` | string          | yes      | Free text, normalised on read  |
| `issued`   | string          | yes      | ISO `YYYY-MM-DD`               |
| `lines`    | list of line    | yes      | At least one line              |
| `tax_rate` | number          | no       | Overrides the document default |

A line has two fields:

| Field        | Type   | Required | Notes                    |
| ------------ | ------ | -------- | ------------------------ |
| `qty`        | number | yes      | Must be positive         |
| `unit_price` | number | yes      | Must not be negative     |

Amounts are floats. This mirrors the upstream service the fixture was extracted
from, and it is the reason the report layer consistently formats to two decimal
places at the edge rather than in the middle of a calculation.

## Invoice calculation flow

The calculation starts when the CLI loads a document. For each invoice:

1. `billing.validate_lines` checks that the line list is structurally sound.
2. `billing.subtotal_for` sums quantity times unit price over every line.
3. `billing.invoice_total` computes the tax for that subtotal and adds it to
   the subtotal to produce the amount due.
4. `billing.invoice_rows` packages subtotal, tax, total and a display string
   into a row.
5. `reports` decides how that row is presented.

The tax rate is expressed as a fraction: `0.085` means 8.5 percent. A per
invoice rate takes precedence over the rate passed on the command line, which
in turn defaults to `billing.DEFAULT_TAX_RATE`.

Discounts are applied before tax. `apply_discount` returns new line objects and
never mutates its input, so callers are free to keep the original for audit
purposes. Discounted unit prices are rounded to the cent at the line level,
because the promotion is advertised per unit.

Empty invoices short circuit to a zero total. A truly empty line list is
allowed by `invoice_total` but rejected by `validate_lines`, which is why the
CLI's validate command reports it while the summary command still prints zero.

## Report pipeline

The monthly report is assembled in `reports.monthly_report`:

1. `filter_month` keeps invoices issued inside the requested month.
2. `sort_by_issued` orders the survivors oldest first.
3. `csv_rows` flattens each invoice into display columns.
4. `format_table` renders the rows with right aligned amounts.
5. `summary_lines` adds count, subtotal, tax and total at the bottom.

Customer totals follow a different path. `customer_totals` groups by normalised
customer name, accumulates subtotal and total, then sorts by descending total.
Rounding to the cent happens once, after accumulation, so a customer with many
small invoices is not penalised by repeated rounding.

CSV export is intentionally a separate function from the table renderer. A
caller may want a machine readable file without the padding, and the column
order for a file is a contract with downstream spreadsheet users. That is why
`CSV_COLUMNS` is a module constant rather than something derived from a row
dictionary.

## Command line interface

```
python -m app.main [--tax-rate RATE] <command> <path> [options]
```

Commands:

- `summary` prints invoice count, subtotal, tax and total.
- `report --year Y --month M` prints the monthly report.
- `export --out FILE` writes a CSV file.
- `validate` prints structural problems and exits non-zero when any are found.

Global options must appear before the command because of how the standard
library parser handles subcommands. This is a known ergonomic wart and is
documented in the README rather than worked around.

Exit codes:

- `0` success,
- `1` handled error (bad input, missing file, validation failure),
- `2` no command supplied; help was printed.

Handled errors are printed to stderr with an `error:` prefix. Unexpected
exceptions are allowed to propagate so that they keep a traceback, which is
more useful during development than a friendly message that hides the cause.

## Storage

There is no storage layer. Documents are read fully into memory and written
fully back out. The largest fixture document is a few kilobytes, so streaming
was not worth the complexity. File helpers create parent directories on write
but never on read; a missing input file is an error the caller should see.

JSON is written with sorted keys and a trailing newline. Sorted keys make diffs
stable when a document is regenerated, and the trailing newline keeps text
editors from complaining. Both choices are deliberate and should be preserved.

## Error handling

The code distinguishes three classes of problem:

- Programming errors, such as passing a string where a number is expected.
  These raise and are not caught.
- Input errors, such as a missing field or a negative price. These raise
  `ValueError` with a message that names the offending line.
- Environment errors, such as a missing file or a permission problem. These
  surface as `OSError` from the standard library.

The CLI catches `OSError` and `ValueError` and maps them to exit code one. That
boundary is the only place where errors are converted into user facing text.
Library functions never print.

## Testing strategy

Tests live in `tests/` and use pytest. They cover the public helpers in
`billing` and the pure helpers in `utils`. Report rendering is covered
indirectly through the CSV row builder. The command line is exercised manually;
it is thin enough that automated coverage would mostly test argparse.

Tests use `pytest.approx` for float comparisons. Exact equality is reserved for
values that are representable without error, such as whole numbers of dollars.

## Deployment

The fixture is not deployed. A production build would produce a wheel, pin the
interpreter version and expose `app.main:main` as a console script. The command
line wrapper is already shaped for that: it accepts an optional `argv` argument
and returns an integer instead of calling `sys.exit` itself.

## Observability

There is no logging configuration in the fixture. Report functions return
strings rather than writing to stdout so a future caller can log them, send
them by email or embed them in a web page. The CLI is the only component that
prints.

If logging were added, the natural seams are the loader in `main.py` and the
report entry points. The arithmetic layer should stay silent; a billing helper
that logs is harder to test and harder to reuse.

## Known limitations

- Money is stored as float. Totals are formatted at the boundary, but long
  chains of additions can still accumulate binary representation error.
- Customer names are normalised by capitalising each word, which is wrong for
  names such as `McDonald` or `van der Berg`.
- The report table does not wrap long customer names; it truncates them.
- CSV export writes UTF-8 without a byte order mark, which some spreadsheet
  applications interpret incorrectly.
- There is no pagination. The whole document is loaded at once.

## Future work

- Move money to `decimal.Decimal` at the boundary.
- Add a date range filter alongside the month filter.
- Emit a machine readable JSON report for dashboards.
- Replace the hand rolled table renderer with a small dependency.
- Add property based tests for the arithmetic helpers.

## Glossary

- **Invoice**: a customer, a date and one or more lines.
- **Line**: a quantity and a unit price.
- **Subtotal**: the sum of line amounts before tax.
- **Tax rate**: a fraction applied to the subtotal.
- **Total**: subtotal plus tax.
- **Report**: a presentation of invoices for a period.
- **Document**: the JSON file that holds invoices.
