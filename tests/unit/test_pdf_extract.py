"""Unit tests for PDF text extraction and metadata extraction."""

from __future__ import annotations

import pytest

from src.parsers.pdf_extractor import (
    PdfExtractionResult,
    extract_analyst_from_pdf_text,
    extract_sector_from_pdf_text,
    extract_text_from_pdf,
)


class TestExtractTextFromPdf:
    """Tests for extract_text_from_pdf()."""

    def test_valid_text_pdf(self, sample_pdf_bytes: bytes) -> None:
        """Text-selectable PDF should extract text successfully."""
        result = extract_text_from_pdf(sample_pdf_bytes)
        assert result.success is True
        assert result.page_count >= 1
        assert result.char_count > 0
        assert len(result.text) > 0
        assert result.error is None

    def test_extracted_text_contains_content(self, sample_pdf_bytes: bytes) -> None:
        """Extracted text should contain the text embedded in the PDF."""
        result = extract_text_from_pdf(sample_pdf_bytes)
        assert result.success is True
        assert "Samsung" in result.text

    def test_empty_bytes(self) -> None:
        """Empty bytes should return failure."""
        result = extract_text_from_pdf(b"")
        assert result.success is False
        assert result.error == "empty_pdf_bytes"
        assert result.text == ""
        assert result.page_count == 0
        assert result.char_count == 0

    def test_invalid_bytes(self) -> None:
        """Non-PDF bytes should return failure with extraction error."""
        result = extract_text_from_pdf(b"this is not a pdf")
        assert result.success is False
        assert result.error is not None
        assert "extraction_error" in result.error

    def test_result_is_frozen(self, sample_pdf_bytes: bytes) -> None:
        """PdfExtractionResult should be frozen dataclass."""
        result = extract_text_from_pdf(sample_pdf_bytes)
        with pytest.raises(AttributeError):
            result.text = "mutated"  # type: ignore[misc]

    def test_result_fields_types(self, sample_pdf_bytes: bytes) -> None:
        """Result fields should have correct types."""
        result = extract_text_from_pdf(sample_pdf_bytes)
        assert isinstance(result, PdfExtractionResult)
        assert isinstance(result.text, str)
        assert isinstance(result.page_count, int)
        assert isinstance(result.char_count, int)
        assert isinstance(result.success, bool)


class TestExtractAnalyst:
    """Tests for extract_analyst_from_pdf_text()."""

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("Report Title\nAnalyst 김기석\n02-3772-1234", "김기석"),
            ("Research Analyst: 박영호\nemail@company.com", "박영호"),
            ("투자의견 매수\nAnalyst: 이수정", "이수정"),
            ("담당애널리스트 홍길동 02-1234-5678", "홍길동"),
            ("담당애널리스트: 김철수\n전화: 02-1234-5678", "김철수"),
            ("문의처\n김기석\nks.kim@hanwha.com", "김기석"),
            ("담당 분석\n박영호\n02-3772-1234", "박영호"),
            ("담당자: 이수정\n02-1234-5678", "이수정"),
            ("This report contains no analyst info", None),
            ("", None),
            (None, None),
        ],
    )
    def test_extract_analyst(self, text: str | None, expected: str | None) -> None:
        assert extract_analyst_from_pdf_text(text) == expected


class TestExtractSector:
    """Tests for extract_sector_from_pdf_text()."""

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("기업분석\n업종: 반도체\n투자의견 매수", "반도체"),
            ("업종 : IT\n목표주가 50,000원", "IT"),
            ("섹터: 자동차\n분석일 2026.04.10", "자동차"),
            ("Sector: 화학\nTarget Price 100,000", "화학"),
            ("Industry: 바이오\n영업이익 500억원", "바이오"),
            ("업종: 전기전자\n주가 50,000원", "전기전자"),
            ("This report has no sector info", None),
            ("", None),
            (None, None),
        ],
    )
    def test_extract_sector(self, text: str | None, expected: str | None) -> None:
        assert extract_sector_from_pdf_text(text) == expected


class TestMetadataCombined:
    """Tests for combined metadata extraction scenarios."""

    def test_both_found(self) -> None:
        text = "기업분석\n업종: 반도체\nAnalyst 김기석\n02-3772-1234"
        assert extract_analyst_from_pdf_text(text) == "김기석"
        assert extract_sector_from_pdf_text(text) == "반도체"

    def test_analyst_only(self) -> None:
        text = "Analyst: 박영호\nSome report content"
        assert extract_analyst_from_pdf_text(text) == "박영호"
        assert extract_sector_from_pdf_text(text) is None

    def test_sector_only(self) -> None:
        text = "기업 분석 보고서\n업종: 반도체\nReport content here"
        assert extract_analyst_from_pdf_text(text) is None
        assert extract_sector_from_pdf_text(text) == "반도체"

    def test_neither_found(self) -> None:
        text = "Just some random report text without metadata"
        assert extract_analyst_from_pdf_text(text) is None
        assert extract_sector_from_pdf_text(text) is None
