"""Date normalizer: various Korean date formats → ISO 8601 date object."""

from __future__ import annotations

from datetime import date

from src.utils.timezone import parse_date_kst


def normalize_date(raw_date: str | None) -> date | None:
    """Normalize a Korean date string to a Python date object.

    Delegates to parse_date_kst() which handles all common formats.

    Args:
        raw_date: Date string in various Korean formats.

    Returns:
        Python date object or None if unparsable.
    """
    if not raw_date:
        return None
    return parse_date_kst(raw_date.strip())
