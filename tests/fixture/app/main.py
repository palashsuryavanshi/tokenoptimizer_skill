"""Command line entry point for the fixture application.

Usage examples::

    python -m app.main summary invoices.json
    python -m app.main report invoices.json --year 2026 --month 3
    python -m app.main export invoices.json --out report.csv
"""

import argparse
import sys

from app import billing, reports, utils


def load_invoices(path):
    """Load and lightly validate an invoice document."""
    payload = utils.read_json(path)
    if isinstance(payload, dict):
        invoices = payload.get("invoices", [])
    else:
        invoices = payload
    if not isinstance(invoices, list):
        raise ValueError("invoices.json must contain a list of invoices")
    return invoices


def command_summary(args):
    """Print the overall totals for every invoice in the file."""
    invoices = load_invoices(args.path)
    rows = billing.invoice_rows(invoices)
    subtotal = sum(row["subtotal"] for row in rows)
    total = sum(row["total"] for row in rows)
    print(f"Invoices: {len(rows)}")
    print(f"Subtotal: {utils.money(subtotal)}")
    print(f"Tax: {utils.money(total - subtotal)}")
    print(f"Total: {utils.money(total)}")
    return 0


def command_report(args):
    """Print the monthly report for the requested month."""
    invoices = load_invoices(args.path)
    print(reports.monthly_report(invoices, args.year, args.month, args.tax_rate))
    return 0


def command_export(args):
    """Write a CSV export and report where it landed."""
    invoices = load_invoices(args.path)
    rows = reports.csv_rows(invoices, args.tax_rate)
    reports.write_csv(args.out, rows)
    print(f"Wrote {len(rows)} rows to {args.out}")
    return 0


def command_validate(args):
    """Check every invoice and print the problems that were found."""
    invoices = load_invoices(args.path)
    problems = 0
    for invoice in invoices:
        try:
            billing.validate_lines(invoice["lines"])
        except ValueError as error:
            problems += 1
            print(f"{invoice.get('id', '<unknown>')}: {error}")
    if problems:
        print(f"{problems} invoice(s) need attention")
        return 1
    print(f"Checked {len(invoices)} invoice(s): no problems found")
    return 0


def build_parser():
    """Build the argument parser for the command line interface."""
    parser = argparse.ArgumentParser(prog="app.main", description="Fixture invoicing tool")
    parser.add_argument("--tax-rate", type=float, default=billing.DEFAULT_TAX_RATE)
    subparsers = parser.add_subparsers(dest="command")

    summary = subparsers.add_parser("summary", help="show overall totals")
    summary.add_argument("path")
    summary.set_defaults(func=command_summary)

    report = subparsers.add_parser("report", help="print a monthly report")
    report.add_argument("path")
    report.add_argument("--year", type=int, required=True)
    report.add_argument("--month", type=int, required=True)
    report.set_defaults(func=command_report)

    export = subparsers.add_parser("export", help="write a CSV export")
    export.add_argument("path")
    export.add_argument("--out", required=True)
    export.set_defaults(func=command_export)

    validate = subparsers.add_parser("validate", help="check invoice data")
    validate.add_argument("path")
    validate.set_defaults(func=command_validate)

    return parser


def main(argv=None):
    """Run the command line interface and return a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 2
    try:
        return args.func(args)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
