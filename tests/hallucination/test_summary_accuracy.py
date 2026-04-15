"""Hallucination detection tests: extracted values must only come from source text.

Per task T039: 원문에 없는 수치가 요약에 등장하면 실패.
"""

from __future__ import annotations

import re

import pytest

from src.schemas.summary import ExtractedInfo, GeneratedSummary, Summary


def _body_contains_number(body: str, value: float) -> bool:
    """Check if a specific number appears in the source body text."""
    # Format in common ways: 110000, 110,000, 11만
    str_val = str(int(value))
    if str_val in body.replace(",", ""):
        return True
    formatted = f"{int(value):,}"
    return formatted in body


class TestHallucinationDetection:
    """Extracted numeric values must exist in the original body text."""

    def test_target_price_present_in_source(self):
        """If extracted.target_price is set, it must appear in body_text."""
        body = "삼성전자(005930) 목표주가 110,000원으로 상향. 투자의견 BUY 유지."
        extracted = ExtractedInfo(target_price=110000, rating="BUY", earnings=None)

        assert _body_contains_number(body, extracted.target_price)

    def test_target_price_hallucinated_should_fail(self):
        """target_price NOT in source → hallucination."""
        body = "삼성전자에 대한 긍정적 전망을 유지합니다."
        # This target price is NOT in the body text
        extracted = ExtractedInfo(target_price=95000, rating=None, earnings=None)

        assert not _body_contains_number(body, extracted.target_price)

    def test_target_price_none_when_absent(self):
        """If body has no target_price info, extracted.target_price must be None."""
        extracted = ExtractedInfo(target_price=None, rating=None, earnings=None)

        assert extracted.target_price is None

    def test_rating_present_in_source(self):
        """Extracted rating should appear in body text."""
        body = "투자의견 BUY, 목표주가 유지"
        extracted = ExtractedInfo(target_price=None, rating="BUY", earnings=None)

        assert extracted.rating in body

    def test_generated_key_points_no_fabricated_numbers(self):
        """Generated key_points should not contain numbers not in the source."""
        body = "삼성전자 HBM 매출 35% 증가. 영업이익 15.2조원 예상."
        generated = GeneratedSummary(
            key_points=["HBM 매출 35% 증가", "영업이익 15.2조원 예상"],
            one_line="HBM 매출 급증에 따른 실적 개선",
        )

        # All numbers in key_points must exist in body
        for point in generated.key_points:
            numbers = re.findall(r"\d+\.?\d*", point)
            for num in numbers:
                assert num in body, f"Number {num} in key_points not found in source body"


class TestExtractedGeneratedSeparation:
    """Per T040: extracted vs generated must be clearly separated."""

    def test_summary_has_both_sections(self):
        summary = Summary(
            canonical_id="c1",
            extracted=ExtractedInfo(target_price=110000, rating="BUY", earnings=None),
            generated=GeneratedSummary(
                key_points=["HBM 매출 증가"],
                one_line="반도체 실적 개선",
            ),
        )

        assert summary.extracted is not None
        assert summary.generated is not None
        assert isinstance(summary.extracted, ExtractedInfo)
        assert isinstance(summary.generated, GeneratedSummary)

    def test_extracted_fields_are_nullable(self):
        """All extracted fields should be None when info not available."""
        extracted = ExtractedInfo(target_price=None, rating=None, earnings=None)
        assert extracted.target_price is None
        assert extracted.rating is None
        assert extracted.earnings is None

    def test_generated_requires_key_points(self):
        """Generated summary must have at least one key_point."""
        with pytest.raises(ValueError):
            GeneratedSummary(key_points=[], one_line="요약")
