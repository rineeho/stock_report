"""Unit tests for Summary schema: extracted/generated separation."""

from __future__ import annotations

import pytest

from src.schemas.summary import ExtractedInfo, GeneratedSummary, Summary


def test_summary_schema_valid():
    s = Summary(
        canonical_id="c1",
        extracted=ExtractedInfo(target_price=110000, rating="BUY", earnings="15.2조원"),
        generated=GeneratedSummary(
            key_points=["HBM 매출 증가", "목표주가 상향"],
            one_line="HBM 매출 급증에 따른 실적 개선",
            opinion_summary="매수 의견 유지",
        ),
    )
    assert s.extracted.target_price == 110000
    assert len(s.generated.key_points) == 2


def test_extracted_all_none_valid():
    e = ExtractedInfo(target_price=None, rating=None, earnings=None)
    assert e.target_price is None


def test_generated_too_many_key_points_rejected():
    with pytest.raises(ValueError):
        GeneratedSummary(
            key_points=["a", "b", "c", "d", "e", "f"],  # max 5
            one_line="test",
        )


def test_generated_empty_one_line_rejected():
    with pytest.raises(ValueError):
        GeneratedSummary(key_points=["a"], one_line="")
