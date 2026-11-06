"""Report generation for the fixture application.

The report layer deliberately does no arithmetic of its own: every amount is
delegated to :mod:`app.billing` so the reporting numbers always agree with the
invoice screens.
"""

import csv

from app import billing, utils

CSV_COLUMNS = ["customer", "invoice", "issued", "subtotal", "tax", "total"]


def filter_month(invoices, year, month):
    """Return only the invoices issued inside ``year``/``month``."""
    selected = []
    for invoice in invoices:
        issued = utils.parse_date(invoice["issued"])
        if issued.year == year and issued.month == month:
            selected.append(invoice)
    return selected


def sort_by_issued(invoices):
    """Return invoices ordered oldest first."""
    return sorted(invoices, key=lambda invoice: utils.parse_date(invoice["issued"]))


def customer_totals(invoices, tax_rate=billing.DEFAULT_TAX_RATE):
    """Aggregate invoice totals per customer.

    The result is a list of ``{"customer", "invoices", "subtotal", "total"}``
    dictionaries ordered by descending total.
    """
    totals = {}
    for invoice in invoices:
        name = utils.normalize_customer_name(invoice["customer"])
        rate = invoice.get("tax_rate", tax_rate)
        subtotal = billing.subtotal_for(invoice["lines"])
        total = billing.invoice_total(invoice["lines"], rate)
        bucket = totals.setdefault(
            name, {"customer": name, "invoices": 0, "subtotal": 0.0, "total": 0.0}
        )
        bucket["invoices"] += 1
        bucket["subtotal"] += subtotal
        bucket["total"] += total
    ordered = sorted(totals.values(), key=lambda row: row["total"], reverse=True)
    for row in ordered:
        row["subtotal"] = round(row["subtotal"], 2)
        row["total"] = round(row["total"], 2)
    return ordered


def csv_rows(invoices, tax_rate=billing.DEFAULT_TAX_RATE):
    """Turn invoices into flat rows ready for CSV export."""
    rows = []
    for invoice in invoices:
        rate = invoice.get("tax_rate", tax_rate)
        subtotal = billing.subtotal_for(invoice["lines"])
        total = billing.invoice_total(invoice["lines"], rate)
        rows.append(
            {
                "customer": invoice["customer"],
                "invoice": invoice["id"],
                "issued": invoice["issued"],
                "subtotal": f"{subtotal:.2f}",
                "tax": f"{total - subtotal:.2f}",
                "total": f"{total:.2f}",
            }
        )
    return rows


def write_csv(path, rows, columns=None):
    """Write *rows* to *path* using the given column order."""
    columns = columns or CSV_COLUMNS
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
    return path


def format_table(rows, columns=None):
    """Render rows as a plain text table.

    The first column is left aligned and the rest are right aligned, which
    matches the layout used by the printed statements.
    """
    if not rows:
        return "(no rows)"
    columns = columns or list(rows[0].keys())
    widths = {}
    for column in columns:
        header = str(column)
        widths[column] = max(
            [len(header)] + [len(str(row.get(column, ""))) for row in rows]
        )
    lines = []
    header_cells = [
        utils.pad(column, widths[column], "left" if index == 0 else "right")
        for index, column in enumerate(columns)
    ]
    lines.append(" | ".join(header_cells))
    lines.append("-+-".join("-" * widths[column] for column in columns))
    for row in rows:
        cells = [
            utils.pad(
                row.get(column, ""), widths[column], "left" if index == 0 else "right"
            )
            for index, column in enumerate(columns)
        ]
        lines.append(" | ".join(cells))
    return "\n".join(lines)


def summary_lines(invoices, tax_rate=billing.DEFAULT_TAX_RATE):
    """Return the text lines used at the top of a monthly report."""
    subtotal = sum(billing.subtotal_for(invoice["lines"]) for invoice in invoices)
    total = sum(
        billing.invoice_total(invoice["lines"], invoice.get("tax_rate", tax_rate))
        for invoice in invoices
    )
    return [
        f"Invoices: {len(invoices)}",
        f"Subtotal: {utils.money(subtotal)}",
        f"Tax: {utils.money(total - subtotal)}",
        f"Total: {utils.money(total)}",
    ]


def monthly_report(invoices, year, month, tax_rate=billing.DEFAULT_TAX_RATE):
    """Build the complete monthly report as a single string."""
    selected = sort_by_issued(filter_month(invoices, year, month))
    heading = f"Monthly report for {utils.month_name(month)} {year}"
    body = format_table(csv_rows(selected, tax_rate), CSV_COLUMNS)
    footer = summary_lines(selected, tax_rate)
    return "\n".join([heading, "=" * len(heading), "", body, "", *footer])
