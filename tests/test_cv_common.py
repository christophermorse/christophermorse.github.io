import datetime
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from cv_common import (
    PRESENT,
    month_label,
    strip_markdown,
    timeline_position,
    timeline_span,
    year_range,
)


@pytest.mark.parametrize(
    "value, label",
    [
        (2019, "2019"),
        ("2021-09", "Sep 2021"),
        (datetime.date(2025, 2, 24), "24 Feb 2025"),
        ("present", "present"),
    ],
)
def test_timeline_position_labels(value, label):
    assert timeline_position(value)[1] == label


def test_present_sits_at_the_end_of_the_timeline():
    assert timeline_position("present")[0] == PRESENT


def test_span_across_years_shows_only_years():
    assert timeline_span("2021-09", "2024-02")[2] == "2021–2024"


def test_span_within_a_year_shows_months():
    assert timeline_span("2006-06", "2006-08")[2] == "Jun–Aug 2006"


def test_span_with_one_end_collapses_to_a_point():
    start, end, label = timeline_span(None, 2020)
    assert start == end
    assert label == "2020"


def test_year_range():
    assert year_range(2017, "2021-09") == "2017–2021"
    assert year_range("2024-04", "present") == "2024–present"
    assert year_range(2023, "2023-12") == "2023"


def test_month_label_without_a_month():
    assert month_label(2019) == "2019"


def test_strip_markdown_keeps_link_text():
    assert strip_markdown("*A* [link](https://example.com)") == "A link"
