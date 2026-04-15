"""Normalization tests: brokerage name mapping, ticker standardization, date format unification."""

from __future__ import annotations

from datetime import date

import pytest

# --- Brokerage normalization ---

@pytest.mark.parametrize("raw_name,expected", [
    ("미래에셋증권", "미래에셋증권"),
    ("미래에셋대우", "미래에셋증권"),
    ("메리츠증권", "메리츠증권"),
    ("메리츠종금증권", "메리츠증권"),
    ("하나금융투자", "하나증권"),
    ("하나증권", "하나증권"),
    ("대신증권", "대신증권"),
    ("키움증권", "키움증권"),
    ("한국투자증권", "한국투자증권"),
    ("NH투자증권", "NH투자증권"),
    ("삼성증권", "삼성증권"),
    ("KB증권", "KB증권"),
    ("신한금융투자", "신한투자증권"),
    ("신한투자증권", "신한투자증권"),
    ("IBK투자증권", "IBK투자증권"),
])
def test_brokerage_normalization(raw_name, expected):
    """Variant brokerage names should normalize to canonical form."""
    from src.normalizers.brokerage import normalize_brokerage

    result = normalize_brokerage(raw_name)
    assert result == expected


def test_brokerage_unknown_passes_through():
    """Unknown brokerage name is returned as-is."""
    from src.normalizers.brokerage import normalize_brokerage

    result = normalize_brokerage("가나다증권")
    assert result == "가나다증권"


# --- Date normalization ---

@pytest.mark.parametrize("raw_date,expected", [
    ("2026.04.10", date(2026, 4, 10)),
    ("2026-04-10", date(2026, 4, 10)),
    ("2026년 04월 10일", date(2026, 4, 10)),
    ("26.04.10", date(2026, 4, 10)),
])
def test_date_normalization(raw_date, expected):
    """Korean date formats should normalize to ISO date object."""
    from src.normalizers.date import normalize_date

    result = normalize_date(raw_date)
    assert result == expected


def test_date_normalization_invalid_returns_none():
    from src.normalizers.date import normalize_date

    assert normalize_date("invalid") is None
    assert normalize_date("") is None


# --- Ticker normalization ---

@pytest.mark.parametrize("code,expected", [
    ("005930", "005930"),
    ("5930", "005930"),       # zero-pad
    ("000660", "000660"),
    ("660", "000660"),
])
def test_ticker_code_normalization(code, expected):
    """Ticker codes should be zero-padded to 6 digits."""
    from src.normalizers.ticker import normalize_ticker_code

    result = normalize_ticker_code(code)
    assert result == expected


def test_ticker_none_returns_none():
    from src.normalizers.ticker import normalize_ticker_code

    assert normalize_ticker_code(None) is None
    assert normalize_ticker_code("") is None
