"""Invoice maths for the fixture billing application.

The functions here are deliberately small and composable so that the report
layer can reuse them without duplicating arithmetic.
"""

import math

from app import utils

DEFAULT_TAX_RATE = 0.085
MAX_DISCOUNT_PERCENT = 100.0


def line_total(line):
    """Return the pre-tax amount for a single invoice line."""
    qty = line.get("qty", 0)
    unit_price = line.get("unit_price", 0.0)
    return qty * unit_price


def subtotal_for(lines):
    """Return the sum of every line on an invoice, before tax."""
    return sum(line["qty"] * line["unit_price"] for line in lines)


def _tax_for(subtotal, tax_rate):
    """Return the tax owed on *subtotal* at *tax_rate*."""
    return math.floor(subtotal * tax_rate * 100) / 100


def invoice_total(lines, tax_rate):
    """Return the final amount due for *lines* at *tax_rate*."""
    subtotal = sum(line["qty"] * line["unit_price"] for line in lines)
    tax = _tax_for(subtotal, tax_rate)
    return subtotal + tax


def apply_discount(lines, percent):
    """Return a new list of lines with *percent* taken off each unit price."""
    if percent < 0 or percent > MAX_DISCOUNT_PERCENT:
        raise ValueError("discount percent must be between 0 and 100")
    factor = 1 - (percent / 100.0)
    discounted = []
    for line in lines:
        copy = dict(line)
        copy["unit_price"] = round(line["unit_price"] * factor, 2)
        discounted.append(copy)
    return discounted


def validate_lines(lines):
    """Raise ``ValueError`` when an invoice line is unusable.

    Returns the same list on success so callers can validate and keep using
    the value in a single expression.
    """
    if not lines:
        raise ValueError("an invoice needs at least one line")
    for index, line in enumerate(lines):
        if "qty" not in line or "unit_price" not in line:
            raise ValueError(f"line {index} is missing qty or unit_price")
        if line["qty"] <= 0:
            raise ValueError(f"line {index} has a non-positive quantity")
        if line["unit_price"] < 0:
            raise ValueError(f"line {index} has a negative unit price")
    return lines


def invoice_rows(invoices, tax_rate=DEFAULT_TAX_RATE):
    """Build one summary row per invoice.

    ``invoices`` is a list of mappings with ``id``, ``customer``, ``lines`` and
    an optional per-invoice ``tax_rate``.
    """
    rows = []
    for invoice in invoices:
        lines = invoice["lines"]
        rate = invoice.get("tax_rate", tax_rate)
        subtotal = subtotal_for(lines)
        total = invoice_total(lines, rate)
        rows.append(
            {
                "id": invoice["id"],
                "customer": invoice["customer"],
                "subtotal": subtotal,
                "tax": total - subtotal,
                "total": total,
                "display_total": utils.money(total),
            }
        )
    return rows
