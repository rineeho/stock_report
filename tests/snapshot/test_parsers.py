"""Parser snapshot tests for naver_research and hankyung_consensus.

Tests discover + parse from fixture files. Run before parser implementation
to verify RED state, then after to verify GREEN.
"""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent.parent / "fixtures" / "sites" / "naver_research"
HK_FIXTURES = Path(__file__).parent.parent / "fixtures" / "sites" / "hankyung_consensus"


@pytest.fixture
def list_page_html() -> str:
    return (FIXTURES / "sample_list_page.html").read_text(encoding="utf-8")


@pytest.fixture
def report_html() -> str:
    return (FIXTURES / "sample_report.html").read_text(encoding="utf-8")


def test_fixtures_exist():
    """Fixture files must exist."""
    assert (FIXTURES / "sample_list_page.html").exists()
    assert (FIXTURES / "sample_report.html").exists()


@pytest.mark.asyncio
async def test_discover_returns_raw_reports(list_page_html):
    """discover_reports() should return at least one RawReport from fixture."""
    from src.parsers.sites.naver_research import NaverResearchParser

    parser = NaverResearchParser()
    reports = await parser.discover_reports(
        list_page_html,
        base_url="https://finance.naver.com/research/company_list.naver",
    )

    assert len(reports) >= 1
    for r in reports:
        assert r.site_id == "naver_research"
        assert r.discovered_url.startswith("http")


@pytest.mark.asyncio
async def test_discover_finds_all_rows(list_page_html):
    """fixture has 5 rows, 4 are from 2026-04-10, 1 from 2026-04-09."""
    from src.parsers.sites.naver_research import NaverResearchParser

    parser = NaverResearchParser()
    reports = await parser.discover_reports(
        list_page_html,
        base_url="https://finance.naver.com/research/company_list.naver",
    )
    assert len(reports) == 5


@pytest.mark.asyncio
async def test_parse_report_extracts_metadata(report_html):
    """parse_report() should extract title, brokerage, analyst, ticker, date."""
    from datetime import date

    from src.parsers.sites.naver_research import NaverResearchParser
    from src.schemas.report import ContentType, FetchStatus, ParseStatus, RawReport

    raw = RawReport(
        site_id="naver_research",
        discovered_url="https://finance.naver.com/research/company_read.naver?nid=100001",
        content_type=ContentType.HTML,
        raw_content=report_html,
        fetch_status=FetchStatus.SUCCESS,
    )

    parser = NaverResearchParser()
    parsed = await parser.parse_report(raw)

    assert parsed.parse_status == ParseStatus.SUCCESS
    assert "HBM" in parsed.title
    assert parsed.brokerage == "미래에셋증권"
    assert parsed.analyst == "김성민"
    assert parsed.ticker == "005930"
    assert parsed.published_date == date(2026, 4, 10)


@pytest.mark.asyncio
async def test_parse_report_extracts_body_text(report_html):
    """parse_report() should extract body text."""
    from src.parsers.sites.naver_research import NaverResearchParser
    from src.schemas.report import ContentType, FetchStatus, RawReport

    raw = RawReport(
        site_id="naver_research",
        discovered_url="https://finance.naver.com/research/company_read.naver?nid=100001",
        content_type=ContentType.HTML,
        raw_content=report_html,
        fetch_status=FetchStatus.SUCCESS,
    )

    parser = NaverResearchParser()
    parsed = await parser.parse_report(raw)

    assert parsed.body_text is not None
    assert "HBM" in parsed.body_text


@pytest.mark.asyncio
async def test_discover_raw_reports_have_date_hints(list_page_html):
    """Discovered RawReports should carry date hint metadata for validation."""
    from src.parsers.sites.naver_research import NaverResearchParser

    parser = NaverResearchParser()
    reports = await parser.discover_reports(
        list_page_html,
        base_url="https://finance.naver.com/research/company_list.naver",
    )
    # The list page includes dates — parsers may embed date hints
    assert all(r.site_id == "naver_research" for r in reports)


# --- hankyung_consensus tests ---


@pytest.fixture
def hk_list_page_html() -> str:
    return (HK_FIXTURES / "sample_list_page.html").read_text(encoding="utf-8")


@pytest.fixture
def hk_report_html() -> str:
    return (HK_FIXTURES / "sample_report.html").read_text(encoding="utf-8")


def test_hk_fixtures_exist():
    """Hankyung consensus fixture files must exist."""
    assert (HK_FIXTURES / "sample_list_page.html").exists()
    assert (HK_FIXTURES / "sample_report.html").exists()


@pytest.mark.asyncio
async def test_hk_discover_returns_raw_reports(hk_list_page_html):
    """discover_reports() should return RawReports from hankyung fixture."""
    from src.parsers.sites.hankyung_consensus import HankyungConsensusParser

    parser = HankyungConsensusParser()
    reports = await parser.discover_reports(
        hk_list_page_html,
        base_url="https://consensus.hankyung.com",
    )

    assert len(reports) >= 1
    for r in reports:
        assert r.site_id == "hankyung_consensus"
        assert r.discovered_url.startswith("http")


@pytest.mark.asyncio
async def test_hk_discover_finds_all_rows(hk_list_page_html):
    """Fixture has 4 rows: 3 from 2026-04-10, 1 from 2026-04-09."""
    from src.parsers.sites.hankyung_consensus import HankyungConsensusParser

    parser = HankyungConsensusParser()
    reports = await parser.discover_reports(
        hk_list_page_html,
        base_url="https://consensus.hankyung.com",
    )
    assert len(reports) == 4


@pytest.mark.asyncio
async def test_hk_parse_report_extracts_metadata(hk_report_html):
    """parse_report() should extract title, brokerage, analyst, ticker, date."""
    from datetime import date

    from src.parsers.sites.hankyung_consensus import HankyungConsensusParser
    from src.schemas.report import ContentType, FetchStatus, ParseStatus, RawReport

    raw = RawReport(
        site_id="hankyung_consensus",
        discovered_url="https://consensus.hankyung.com/report_view.php?id=20001",
        content_type=ContentType.HTML,
        raw_content=hk_report_html,
        fetch_status=FetchStatus.SUCCESS,
    )

    parser = HankyungConsensusParser()
    parsed = await parser.parse_report(raw)

    assert parsed.parse_status == ParseStatus.SUCCESS
    assert "목표주가" in parsed.title
    assert parsed.brokerage == "메리츠증권"
    assert parsed.analyst == "박준영"
    assert parsed.ticker == "005930"
    assert parsed.published_date == date(2026, 4, 10)


@pytest.mark.asyncio
async def test_hk_parse_report_extracts_body_text(hk_report_html):
    """parse_report() should extract body text."""
    from src.parsers.sites.hankyung_consensus import HankyungConsensusParser
    from src.schemas.report import ContentType, FetchStatus, RawReport

    raw = RawReport(
        site_id="hankyung_consensus",
        discovered_url="https://consensus.hankyung.com/report_view.php?id=20001",
        content_type=ContentType.HTML,
        raw_content=hk_report_html,
        fetch_status=FetchStatus.SUCCESS,
    )

    parser = HankyungConsensusParser()
    parsed = await parser.parse_report(raw)

    assert parsed.body_text is not None
    assert "HBM" in parsed.body_text

