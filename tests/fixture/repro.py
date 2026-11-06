"""Reproduce the reported one-cent discrepancy on a small invoice."""

import os
import sys
from decimal import ROUND_HALF_UP, Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.billing import invoice_total


def main():
    lines = [{"qty": 3, "unit_price": 19.99}]
    tax_rate = 0.085

    subtotal = sum(line["qty"] * line["unit_price"] for line in lines)
    total = invoice_total(lines, tax_rate)
    tax = total - subtotal
    expected = float(
        (Decimal(str(subtotal)) * (Decimal("1") + Decimal(str(tax_rate)))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    )

    print(
        f"subtotal={subtotal:.2f} tax={tax:.2f} "
        f"total={total:.2f} expected={expected:.2f}"
    )


if __name__ == "__main__":
    main()
