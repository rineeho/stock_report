"""Asia/Seoul timezone utilities for date boundary handling."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


def now_kst() -> datetime:
    """Get current datetime in KST."""
    return datetime.now(KST)


def today_kst() -> date:
    """Get today's date in KST."""
    return now_kst().date()


def is_same_date_kst(dt: datetime | date, target: date) -> bool:
    """Check if the given datetime/date matches the target date in KST.

    Args:
        dt: A datetime (with or without timezone) or date to check.
        target: The target date to compare against.

    Returns:
        True if dt falls on the target date in KST timezone.
    """
    if isinstance(dt, datetime):
        dt = dt.replace(tzinfo=KST) if dt.tzinfo is None else dt.astimezone(KST)
        return dt.date() == target
    return dt == target


def parse_date_kst(date_str: str) -> date | None:
    """Try to parse a date string in various Korean formats.

    Supported formats:
    - 2026-04-10 (ISO)
    - 2026.04.10
    - 2026/04/10
    - 26.04.10
    - 2026년 04월 10일
    - 2026년4월10일

    Returns:
        Parsed date or None if unparsable.
    """
    import re

    date_str = date_str.strip()

    # Korean format: 2026년 04월 10일 or 2026년4월10일
    m = re.match(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", date_str)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # Standard formats
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    # Short year: 26.04.10
    m = re.match(r"(\d{2})\.(\d{2})\.(\d{2})", date_str)
    if m:
        year = 2000 + int(m.group(1))
        return date(year, int(m.group(2)), int(m.group(3)))

    return None
