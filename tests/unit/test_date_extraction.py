"""Parameterized date extraction tests for multi-strategy date extraction (R10).

Tests: meta_tag, json_ld, body_pattern, Korean date formats.
"""

from __future__ import annotations

from datetime import date

import pytest


@pytest.mark.parametrize("html,expected_date,expected_source", [
    # Strategy 1: og:article:published_time meta tag
    (
        '<html><head><meta property="article:published_time" content="2026-04-10T09:30:00+09:00"></head><body></body></html>',
        date(2026, 4, 10),
        "meta_tag",
    ),
    # Strategy 1: date meta name
    (
        '<html><head><meta name="date" content="2026-04-10"></head><body></body></html>',
        date(2026, 4, 10),
        "meta_tag",
    ),
    # Strategy 2: JSON-LD datePublished
    (
        '''<html><head>
        <script type="application/ld+json">{"@type":"Article","datePublished":"2026-04-10"}</script>
        </head><body></body></html>''',
        date(2026, 4, 10),
        "json_ld",
    ),
    # Strategy 3: body YYYY.MM.DD pattern
    (
        '<html><body><p>작성일: 2026.04.10</p><p>내용...</p></body></html>',
        date(2026, 4, 10),
        "body_pattern",
    ),
    # Strategy 3: body YYYY-MM-DD
    (
        '<html><body><span class="date">2026-04-10</span></body></html>',
        date(2026, 4, 10),
        "body_pattern",
    ),
])
def test_extract_date_multi_strategy(html, expected_date, expected_source):
    """Multi-strategy extraction should detect the correct date and source."""
    from src.parsers.base import BaseSiteParser

    # Create a minimal concrete subclass for testing
    class _TestParser(BaseSiteParser):
        @property
        def site_id(self) -> str:
            return "test"

        async def discover_reports(self, html_content, base_url):
            return []

        async def parse_report(self, raw):
            pass

    parser = _TestParser()
    extracted_date, source = parser.extract_date_multi_strategy(html)

    assert extracted_date == expected_date
    assert source is not None
    assert source.value == expected_source


def test_extract_date_returns_none_for_no_date():
    """Returns (None, None) when no date found."""
    from src.parsers.base import BaseSiteParser

    class _TestParser(BaseSiteParser):
        @property
        def site_id(self) -> str:
            return "test"

        async def discover_reports(self, html_content, base_url):
            return []

        async def parse_report(self, raw):
            pass

    parser = _TestParser()
    extracted_date, source = parser.extract_date_multi_strategy(
        "<html><body><p>날짜 없음</p></body></html>"
    )
    assert extracted_date is None
    assert source is None


@pytest.mark.parametrize("date_str,expected", [
    ("2026-04-10", date(2026, 4, 10)),
    ("2026.04.10", date(2026, 4, 10)),
    ("2026/04/10", date(2026, 4, 10)),
    ("2026년 04월 10일", date(2026, 4, 10)),
    ("2026년4월10일", date(2026, 4, 10)),
    ("2026년 4월 10일", date(2026, 4, 10)),
    ("26.04.10", date(2026, 4, 10)),
    ("invalid", None),
    ("", None),
])
def test_parse_date_kst_formats(date_str, expected):
    """parse_date_kst() should handle all Korean date formats."""
    from src.utils.timezone import parse_date_kst

    result = parse_date_kst(date_str)
    assert result == expected


def test_today_kst_returns_date():
    """today_kst() should return a date in KST."""
    from src.utils.timezone import today_kst

    d = today_kst()
    assert isinstance(d, date)


def test_is_same_date_kst():
    """is_same_date_kst() should correctly compare dates in Asia/Seoul."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from src.utils.timezone import is_same_date_kst

    kst = ZoneInfo("Asia/Seoul")
    dt = datetime(2026, 4, 10, 23, 50, tzinfo=kst)

    assert is_same_date_kst(dt, date(2026, 4, 10)) is True
    assert is_same_date_kst(dt, date(2026, 4, 9)) is False
    assert is_same_date_kst(date(2026, 4, 10), date(2026, 4, 10)) is True
