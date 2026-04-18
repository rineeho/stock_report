"""Unit tests for HankyungConsensusParser."""

from __future__ import annotations

import json
from datetime import date

import pytest

from src.parsers.sites.hankyung_consensus import HankyungConsensusParser
from src.schemas.report import ContentType, FetchStatus, ParseStatus, RawReport


@pytest.fixture
def parser() -> HankyungConsensusParser:
    return HankyungConsensusParser()


# ---------------------------------------------------------------------------
# HTML fixtures
# ---------------------------------------------------------------------------

LISTING_HTML = """\
<html><body>
<div class="table_style01">
<table>
  <thead>
  <tr>
    <th>작성일</th><th>제목</th><th>적정가격</th>
    <th>투자의견</th><th>작성자</th><th>제공출처</th>
    <th>기업정보</th><th>차트</th><th>첨부파일</th>
  </tr>
  </thead>
  <tbody>
  <tr class="first">
    <td class="first txt_number">2026-04-17</td>
    <td class="text_l"><a href="/analysis/downpdf?report_idx=648548">코스모신소재(005070) HBM 수혜 본격화</a></td>
    <td class="text_r txt_number">70,000</td>
    <td>Buy</td>
    <td>김기석</td>
    <td>한화투자증권</td>
    <td></td><td></td><td></td>
  </tr>
  <tr>
    <td class="first txt_number">2026-04-16</td>
    <td class="text_l"><a href="/analysis/downpdf?report_idx=648500">삼성전자(005930) 실적 리뷰</a></td>
    <td class="text_r txt_number">80,000</td>
    <td>Hold</td>
    <td>박영호</td>
    <td>미래에셋증권</td>
    <td></td><td></td><td></td>
  </tr>
  </tbody>
</table>
</div>
</body></html>
"""

LISTING_HTML_NO_TABLE = "<html><body><p>No table here</p></body></html>"

LISTING_HTML_SHORT_ROWS = """\
<html><body>
<div class="table_style01">
<table><tbody>
  <tr><td>Only</td><td>Two</td></tr>
</tbody></table>
</div>
</body></html>
"""


# ---------------------------------------------------------------------------
# discover_reports tests
# ---------------------------------------------------------------------------

class TestDiscoverReports:
    """Tests for discover_reports()."""

    @pytest.mark.asyncio
    async def test_discovers_two_reports(self, parser: HankyungConsensusParser) -> None:
        reports = await parser.discover_reports(LISTING_HTML, "https://consensus.hankyung.com")
        assert len(reports) == 2

    @pytest.mark.asyncio
    async def test_first_report_fields(self, parser: HankyungConsensusParser) -> None:
        reports = await parser.discover_reports(LISTING_HTML, "https://consensus.hankyung.com")
        r = reports[0]
        assert r.site_id == "hankyung_consensus"
        assert r.content_type == ContentType.PDF
        assert "648548" in r.discovered_url
        assert r.metadata_hint is not None

        hint = json.loads(r.metadata_hint)
        assert hint["stock_name"] == "코스모신소재"
        assert hint["ticker"] == "005070"
        assert hint["brokerage"] == "한화투자증권"
        assert hint["analyst"] == "김기석"
        assert hint["date_hint"] == "2026-04-17"
        assert hint["target_price"] == "70,000"
        assert hint["opinion"] == "Buy"
        assert "648548" in hint["pdf_url"]

    @pytest.mark.asyncio
    async def test_second_report_fields(self, parser: HankyungConsensusParser) -> None:
        reports = await parser.discover_reports(LISTING_HTML, "https://consensus.hankyung.com")
        hint = json.loads(reports[1].metadata_hint)
        assert hint["stock_name"] == "삼성전자"
        assert hint["ticker"] == "005930"
        assert hint["brokerage"] == "미래에셋증권"
        assert hint["analyst"] == "박영호"

    @pytest.mark.asyncio
    async def test_no_table_returns_empty(self, parser: HankyungConsensusParser) -> None:
        reports = await parser.discover_reports(LISTING_HTML_NO_TABLE, "https://consensus.hankyung.com")
        assert reports == []

    @pytest.mark.asyncio
    async def test_short_rows_skipped(self, parser: HankyungConsensusParser) -> None:
        reports = await parser.discover_reports(LISTING_HTML_SHORT_ROWS, "https://consensus.hankyung.com")
        assert reports == []

    @pytest.mark.asyncio
    async def test_metadata_stored_in_metadata_hint(self, parser: HankyungConsensusParser) -> None:
        """Metadata should be in metadata_hint (not raw_content) for FetchAgent PDF enrichment."""
        reports = await parser.discover_reports(LISTING_HTML, "https://consensus.hankyung.com")
        for r in reports:
            assert r.metadata_hint is not None
            assert r.raw_content is None


# ---------------------------------------------------------------------------
# get_page_url tests
# ---------------------------------------------------------------------------

class TestGetPageUrl:
    def test_with_date(self, parser: HankyungConsensusParser) -> None:
        url = parser.get_page_url("", page=2, target_date=date(2026, 4, 17))
        assert "sdate=2026-04-17" in url
        assert "edate=2026-04-17" in url
        assert "now_page=2" in url
        assert "skinType=business" in url

    def test_without_date(self, parser: HankyungConsensusParser) -> None:
        url = parser.get_page_url("", page=1)
        assert "now_page=1" in url
        assert "sdate=&edate=" in url or "sdate=&" in url


# ---------------------------------------------------------------------------
# parse_report tests
# ---------------------------------------------------------------------------

def _make_raw(hint_overrides: dict | None = None, pdf_text: str | None = None) -> RawReport:
    """Build a RawReport with metadata_hint for testing parse_report."""
    hint = {
        "title": "HBM 수혜 본격화",
        "brokerage": "한화투자증권",
        "stock_name": "코스모신소재",
        "ticker": "005070",
        "date_hint": "2026-04-17",
        "analyst": "김기석",
        "target_price": "70,000",
        "opinion": "Buy",
        "pdf_url": "https://consensus.hankyung.com/analysis/downpdf?report_idx=648548",
    }
    if hint_overrides:
        hint.update(hint_overrides)
    return RawReport(
        site_id="hankyung_consensus",
        discovered_url=hint["pdf_url"],
        content_type=ContentType.PDF,
        metadata_hint=json.dumps(hint, ensure_ascii=False),
        pdf_text=pdf_text,
        fetch_status=FetchStatus.SUCCESS,
    )


class TestParseReport:
    """Tests for parse_report()."""

    @pytest.mark.asyncio
    async def test_success_from_hint(self, parser: HankyungConsensusParser) -> None:
        raw = _make_raw()
        parsed = await parser.parse_report(raw)
        assert parsed.parse_status == ParseStatus.SUCCESS
        assert parsed.title == "HBM 수혜 본격화"
        assert parsed.brokerage == "한화투자증권"
        assert parsed.stock_name == "코스모신소재"
        assert parsed.ticker == "005070"
        assert parsed.analyst == "김기석"
        assert parsed.published_date == date(2026, 4, 17)
        assert "648548" in parsed.pdf_url

    @pytest.mark.asyncio
    async def test_pdf_text_provides_body(self, parser: HankyungConsensusParser) -> None:
        raw = _make_raw(pdf_text="PDF body content here")
        parsed = await parser.parse_report(raw)
        assert parsed.body_text == "PDF body content here"

    @pytest.mark.asyncio
    async def test_pdf_text_fills_sector(self, parser: HankyungConsensusParser) -> None:
        raw = _make_raw(pdf_text="기업분석\n업종: 반도체\nAnalyst 김기석")
        parsed = await parser.parse_report(raw)
        assert parsed.sector == "반도체"

    @pytest.mark.asyncio
    async def test_pdf_text_fills_analyst_when_missing(self, parser: HankyungConsensusParser) -> None:
        raw = _make_raw(
            hint_overrides={"analyst": None},
            pdf_text="Research Analyst 박영호\nemail@company.com",
        )
        parsed = await parser.parse_report(raw)
        assert parsed.analyst == "박영호"

    @pytest.mark.asyncio
    async def test_hint_analyst_takes_priority(self, parser: HankyungConsensusParser) -> None:
        """Listing-page analyst should not be overridden by PDF analyst."""
        raw = _make_raw(pdf_text="Research Analyst 박영호\nemail@company.com")
        parsed = await parser.parse_report(raw)
        assert parsed.analyst == "김기석"  # from hint, not PDF

    @pytest.mark.asyncio
    async def test_missing_title_partial(self, parser: HankyungConsensusParser) -> None:
        raw = _make_raw(hint_overrides={"title": ""})
        parsed = await parser.parse_report(raw)
        assert parsed.parse_status == ParseStatus.FAILED
        assert "title_missing" in parsed.parse_errors

    @pytest.mark.asyncio
    async def test_missing_date_error(self, parser: HankyungConsensusParser) -> None:
        raw = _make_raw(hint_overrides={"date_hint": ""})
        parsed = await parser.parse_report(raw)
        assert "published_date_missing" in parsed.parse_errors
        assert parsed.parse_status == ParseStatus.PARTIAL

    @pytest.mark.asyncio
    async def test_no_metadata_hint(self, parser: HankyungConsensusParser) -> None:
        raw = RawReport(
            site_id="hankyung_consensus",
            discovered_url="https://example.com/report.pdf",
            metadata_hint=None,
        )
        parsed = await parser.parse_report(raw)
        assert parsed.parse_status == ParseStatus.FAILED


# ---------------------------------------------------------------------------
# FetchAgent integration: PDF response handling
# ---------------------------------------------------------------------------

class TestFetchAgentPdfIntegration:
    """Test that FetchAgent correctly handles PDF URLs from hankyung_consensus."""

    @pytest.mark.asyncio
    async def test_pdf_response_extracts_text(self, sample_pdf_bytes: bytes) -> None:
        from unittest.mock import MagicMock

        from src.agents.fetch import FetchAgent

        resp = MagicMock()
        resp.content = sample_pdf_bytes
        resp.text = "garbage"
        resp.status_code = 200
        resp.headers = {"content-type": "application/pdf"}

        class _MockClient:
            async def get(self, url, site_id=None, **kwargs):
                return resp

        agent = FetchAgent(http_client=_MockClient())
        raw = RawReport(
            site_id="hankyung_consensus",
            discovered_url="https://consensus.hankyung.com/analysis/downpdf?report_idx=648548",
            content_type=ContentType.PDF,
            metadata_hint=json.dumps({"pdf_url": "https://example.com/report.pdf"}),
        )
        results = await agent.process([raw], date(2026, 4, 17))

        assert len(results) == 1
        assert results[0].fetch_status == FetchStatus.SUCCESS
        assert results[0].content_type == ContentType.PDF
        assert results[0].pdf_text is not None
        assert "Samsung" in results[0].pdf_text
        # raw_content should NOT be set to binary garbage
        assert results[0].raw_content is None
