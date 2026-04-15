"""Ticker/stock code normalizer: zero-pad codes to 6 digits."""

from __future__ import annotations

import re


def normalize_ticker_code(code: str | None) -> str | None:
    """Normalize a Korean stock ticker code to 6-digit zero-padded form.

    Args:
        code: Raw ticker code (e.g., "5930", "005930").

    Returns:
        Zero-padded 6-digit string or None if input is None/empty.
    """
    if not code:
        return None
    code = code.strip()
    if not code:
        return None
    # Remove any non-digit prefix (like 'A' for KOSDAQ in some sources)
    digits = re.sub(r"[^\d]", "", code)
    if not digits:
        return None
    return digits.zfill(6)


def normalize_stock_name(name: str | None) -> str | None:
    """Strip extra whitespace from stock name."""
    if not name:
        return None
    return name.strip()
