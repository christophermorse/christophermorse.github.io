"""Loading and date handling shared by the website and PDF builds."""

import datetime
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()

# Where "present" falls on the timeline. Keep in step with NOW in site/app.js.
PRESENT = 2026.75


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_cv():
    return load_yaml(ROOT / "cv.yaml")


def year_month_day(value):
    """Split a YAML date or a "YYYY[-MM[-DD]]" string; missing parts are None."""
    if isinstance(value, datetime.date):
        return value.year, value.month, value.day
    parts = [int(p) for p in str(value).split("-")]
    return tuple(parts + [None] * (3 - len(parts)))


def timeline_position(value):
    """Return a date as (decimal year, display label) for the timeline."""
    if value is None:
        return None, ""
    if value == "present":
        return PRESENT, "present"
    year, month, day = year_month_day(value)
    if month is None:
        return year + 0.5, str(year)
    name = MONTHS[month - 1]
    if day is None:
        return year + (month - 0.5) / 12, f"{name} {year}"
    return year + (month - 1 + day / 31) / 12, f"{day} {name} {year}"


def timeline_span(start, end):
    """Return (start, end, label) for a date range; either end may be missing."""
    start_pos, start_label = timeline_position(start)
    end_pos, end_label = timeline_position(end)
    if start_pos is None:
        return end_pos, end_pos, end_label
    if end_pos is None:
        return start_pos, start_pos, start_label

    start_year = start_label.split()[-1]
    end_year = end_label if end_label == "present" else end_label.split()[-1]
    if start_year != end_year:
        return start_pos, end_pos, f"{start_year}–{end_year}"
    if start_label == end_label:
        return start_pos, end_pos, start_label
    # Same year, different months: "Jun–Aug 2006".
    return start_pos, end_pos, f'{start_label.rsplit(" ", 1)[0]}–{end_label}'


def month_label(value):
    """Format a date as "Feb 2025", or "2025" when it has no month."""
    year, month, _ = year_month_day(value)
    return f"{MONTHS[month - 1]} {year}" if month else str(year)


def year_range(start, end):
    """Format a range in whole years: "2021–2024", "2024–present", or "2023"."""
    first = year_month_day(start)[0]
    last = "present" if end == "present" else year_month_day(end)[0]
    return str(first) if first == last else f"{first}–{last}"


def sort_key(value):
    year, month, _ = year_month_day(value)
    return year, month or 0


def strip_markdown(text):
    """Remove the light markdown allowed in cv.yaml, keeping link text."""
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", str(text)).replace("*", "")
