"""Tests for the billing module."""

import pytest

from app import billing


def test_line_total_multiplies_quantity_by_unit_price():
    assert billing.line_total({"qty": 4, "unit_price": 2.5}) == 10.0


def test_subtotal_sums_every_line():
    lines = [
        {"qty": 2, "unit_price": 10.0},
        {"qty": 1, "unit_price": 5.5},
    ]
    assert billing.subtotal_for(lines) == 25.5


def test_invoice_total_adds_tax():
    lines = [{"qty": 1, "unit_price": 100.0}]
    assert billing.invoice_total(lines, 0.1) == pytest.approx(110.0)


def test_invoice_total_at_default_style_rate():
    lines = [{"qty": 2, "unit_price": 20.0}]
    assert billing.invoice_total(lines, 0.085) == pytest.approx(43.4)


def test_invoice_total_of_empty_invoice_is_zero():
    assert billing.invoice_total([], 0.085) == 0.0


def test_apply_discount_reduces_unit_prices():
    lines = [{"qty": 1, "unit_price": 80.0}]
    discounted = billing.apply_discount(lines, 25)
    assert discounted[0]["unit_price"] == 60.0


def test_apply_discount_leaves_the_original_untouched():
    lines = [{"qty": 1, "unit_price": 80.0}]
    billing.apply_discount(lines, 25)
    assert lines[0]["unit_price"] == 80.0


def test_apply_discount_rejects_negative_percent():
    with pytest.raises(ValueError):
        billing.apply_discount([{"qty": 1, "unit_price": 1.0}], -1)


def test_apply_discount_rejects_percent_above_one_hundred():
    with pytest.raises(ValueError):
        billing.apply_discount([{"qty": 1, "unit_price": 1.0}], 101)


def test_validate_lines_accepts_good_input():
    lines = [{"qty": 1, "unit_price": 2.0}]
    assert billing.validate_lines(lines) is lines


def test_validate_lines_rejects_missing_fields():
    with pytest.raises(ValueError):
        billing.validate_lines([{"qty": 1}])


def test_validate_lines_rejects_non_positive_quantity():
    with pytest.raises(ValueError):
        billing.validate_lines([{"qty": 0, "unit_price": 2.0}])


def test_validate_lines_rejects_negative_price():
    with pytest.raises(ValueError):
        billing.validate_lines([{"qty": 1, "unit_price": -0.01}])


def test_invoice_rows_include_money_breakdown():
    invoices = [
        {
            "id": "INV-1",
            "customer": "Ada Ltd",
            "lines": [{"qty": 1, "unit_price": 100.0}],
        }
    ]
    rows = billing.invoice_rows(invoices, 0.1)
    assert rows[0]["subtotal"] == pytest.approx(100.0)
    assert rows[0]["tax"] == pytest.approx(10.0)
    assert rows[0]["total"] == pytest.approx(110.0)
    assert rows[0]["display_total"] == "$110.00"
