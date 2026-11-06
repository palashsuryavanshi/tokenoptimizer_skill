"""Small helpers shared across the fixture application.

Nothing in this module knows about invoices. It only deals with formatting,
dates, grouping and file handling so the other modules stay readable.
"""

import json
import os
import re
import unicodedata
from datetime import date, datetime

DEFAULT_CURRENCY = "USD"

MONTH_NAMES = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

_WHITESPACE_RE = re.compile(r"\s+")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def money(value, currency=DEFAULT_CURRENCY):
    """Format *value* as a human readable amount."""
    if currency == DEFAULT_CURRENCY:
        return f"${value:,.2f}"
    return f"{value:,.2f} {currency}"


def parse_money(text):
    """Parse a string such as ``"$1,234.50"`` into a float."""
    cleaned = str(text).strip().replace("$", "").replace(",", "")
    if not cleaned:
        raise ValueError("empty amount")
    return float(cleaned)


def format_percent(value, digits=2):
    """Render a fraction as a percentage string."""
    return f"{value * 100:.{digits}f}%"


def clamp(value, low, high):
    """Return *value* limited to the inclusive ``low..high`` range."""
    if low > high:
        raise ValueError("low must not exceed high")
    return max(low, min(high, value))


def collapse_spaces(text):
    """Collapse runs of whitespace into single spaces and trim the ends."""
    return _WHITESPACE_RE.sub(" ", text).strip()


def is_blank(value):
    """Return ``True`` when *value* is ``None`` or only whitespace."""
    return value is None or not str(value).strip()


def slugify(text):
    """Turn arbitrary text into a lower-case dash separated slug."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = _SLUG_RE.sub("-", ascii_text.lower())
    return slug.strip("-")


def normalize_customer_name(name):
    """Return a display form of *name* with tidy spacing and casing."""
    cleaned = collapse_spaces(str(name))
    if not cleaned:
        raise ValueError("customer name is required")
    return " ".join(part.capitalize() for part in cleaned.split(" "))


def unique_preserving_order(values):
    """Remove duplicates from *values* while keeping the first occurrence."""
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def group_by(items, key):
    """Group *items* into a dict of lists keyed by ``key(item)``."""
    grouped = {}
    for item in items:
        grouped.setdefault(key(item), []).append(item)
    return grouped


def chunked(values, size):
    """Yield consecutive chunks of at most *size* items."""
    if size <= 0:
        raise ValueError("size must be positive")
    for start in range(0, len(values), size):
        yield values[start : start + size]


def month_bounds(year, month):
    """Return the first and last :class:`date` of a calendar month."""
    if month < 1 or month > 12:
        raise ValueError("month must be between 1 and 12")
    first = date(year, month, 1)
    if month == 12:
        last = date(year, 12, 31)
    else:
        last = date(year, month + 1, 1)
        last = date.fromordinal(last.toordinal() - 1)
    return first, last


def parse_date(value):
    """Parse ``YYYY-MM-DD`` text, or return a :class:`date` unchanged."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()


def month_label(year, month):
    """Return a short human label such as ``2026-03``."""
    if month < 1 or month > 12:
        raise ValueError("month must be between 1 and 12")
    return f"{year:04d}-{month:02d}"


def month_name(month):
    """Return the English name for a month number."""
    if month < 1 or month > 12:
        raise ValueError("month must be between 1 and 12")
    return MONTH_NAMES[month - 1]


def in_month(day, year, month):
    """Return ``True`` when *day* falls inside the given month."""
    first, last = month_bounds(year, month)
    return first <= parse_date(day) <= last


def read_json(path):
    """Load a UTF-8 JSON document from *path*."""
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, payload):
    """Write *payload* to *path* as indented UTF-8 JSON."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def ensure_directory(path):
    """Create *path* (and parents) if it does not exist yet."""
    os.makedirs(path, exist_ok=True)
    return path


def truncate(text, limit=40, suffix="..."):
    """Shorten *text* to *limit* characters, adding *suffix* when needed."""
    if limit < len(suffix):
        raise ValueError("limit is smaller than the suffix")
    if len(text) <= limit:
        return text
    return text[: limit - len(suffix)] + suffix


def pad(text, width, align="left"):
    """Pad *text* to *width*, truncating when it is too long."""
    text = truncate(str(text), width, "")
    if align == "right":
        return text.rjust(width)
    return text.ljust(width)
