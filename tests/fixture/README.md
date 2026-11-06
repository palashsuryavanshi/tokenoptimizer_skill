# Fixture application

A small invoicing application used as a realistic sandbox for the
token-optimizer scenarios. It has no external dependencies beyond the Python
standard library; the test suite uses `pytest`.

## Layout

```
fixture/
  app/
    __init__.py
    billing.py    # invoice arithmetic
    main.py       # command line entry point
    reports.py    # monthly reports and CSV export
    utils.py      # formatting, dates, grouping, file helpers
  docs/
    architecture.md
    changelog.md
  tests/
    test_billing.py
  conftest.py
  repro.py
  README.md
```

## Running the tests

From the repository root:

```powershell
python -m pytest tests/fixture/tests -q
```

The tests only exercise the public helpers in `app.billing`.

## Reproducing an invoice calculation

`repro.py` calculates one invoice and prints the subtotal, the tax, the final
total and the expected total side by side:

```powershell
python tests/fixture/repro.py
```

It also runs when the current directory is `tests/fixture`:

```powershell
cd tests/fixture
python repro.py
```

## Command line

The command line interface reads a JSON document containing a list of
invoices:

```json
{
  "invoices": [
    {
      "id": "INV-1001",
      "customer": "Ada Ltd",
      "issued": "2026-03-04",
      "lines": [
        {"qty": 3, "unit_price": 19.99}
      ]
    }
  ]
}
```

All amounts are plain floats and the default tax rate is 8.5%. A per-invoice
`tax_rate` overrides the default.

```powershell
python -m app.main summary invoices.json
python -m app.main report invoices.json --year 2026 --month 3
python -m app.main export invoices.json --out report.csv
python -m app.main validate invoices.json
```

Run these from the `tests/fixture` directory (or set `PYTHONPATH` to it) so
that the `app` package is importable.

## Notes

- Monetary values are stored as floats, matching the upstream service this
  fixture was extracted from.
- Dates are ISO `YYYY-MM-DD` strings.
- The reports layer never formats currency itself; it calls `app.utils`.
