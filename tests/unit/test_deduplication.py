"""Deduplication tests: URL exact match, metadata match, revision detection.

Per task T045: URL exact match, metadata match, different ticker same title, revision detection.
"""

from __future__ import annotations

from datetime import date

from src.schemas.report import MatchType, NormalizedReport


def _make_normalized(
    *,
    url: str = "https://example.com/report/1",
    title: str = "삼성전자 목표주가 상향",
    brokerage: str = "미래에셋증권",
    analyst: str = "김성민",
    ticker: str | None = "005930",
    stock_name: str | None = "삼성전자",
    published_date: date = date(2026, 4, 10),
    body_text: str | None = "본문 내용",
    normalized_id: str | None = None,
) -> NormalizedReport:
    kw: dict = dict(
        validated_id="v1",
        title=title,
        published_date=published_date,
        brokerage=brokerage,
        analyst=analyst,
        ticker=ticker,
        stock_name=stock_name,
        source_url=url,
        body_text=body_text,
    )
    if normalized_id:
        kw["normalized_id"] = normalized_id
    return NormalizedReport(**kw)


class TestURLExactMatch:
    """Stage 1: identical URL → deduplicate."""

    def test_same_url_deduplicates(self):
        from src.dedup.matcher import find_duplicates

        r1 = _make_normalized(url="https://a.com/r1", normalized_id="n1")
        r2 = _make_normalized(url="https://a.com/r1", normalized_id="n2")

        groups = find_duplicates([r1, r2])
        assert len(groups) == 1
        assert groups[0].match_type == MatchType.URL_EXACT
        assert len(groups[0].member_ids) == 2

    def test_different_urls_kept_separate(self):
        from src.dedup.matcher import find_duplicates

        r1 = _make_normalized(url="https://a.com/r1", normalized_id="n1")
        r2 = _make_normalized(url="https://a.com/r2", normalized_id="n2", title="다른 제목")

        groups = find_duplicates([r1, r2])
        assert len(groups) == 2


class TestMetadataMatch:
    """Stage 2: same title+brokerage+date → deduplicate."""

    def test_same_metadata_different_url_deduplicates(self):
        from src.dedup.matcher import find_duplicates

        r1 = _make_normalized(
            url="https://naver.com/r1",
            title="삼성전자 실적 전망",
            brokerage="미래에셋증권",
            normalized_id="n1",
        )
        r2 = _make_normalized(
            url="https://hankyung.com/r1",
            title="삼성전자 실적 전망",
            brokerage="미래에셋증권",
            normalized_id="n2",
        )

        groups = find_duplicates([r1, r2])
        assert len(groups) == 1
        assert groups[0].match_type == MatchType.METADATA_MATCH
        assert len(groups[0].member_ids) == 2

    def test_same_title_different_brokerage_kept_separate(self):
        from src.dedup.matcher import find_duplicates

        r1 = _make_normalized(
            url="https://a.com/r1",
            title="삼성전자 실적 전망",
            brokerage="미래에셋증권",
            normalized_id="n1",
        )
        r2 = _make_normalized(
            url="https://a.com/r2",
            title="삼성전자 실적 전망",
            brokerage="한국투자증권",
            normalized_id="n2",
        )

        groups = find_duplicates([r1, r2])
        assert len(groups) == 2


class TestDifferentTickerSameTitle:
    """Same title and brokerage but different ticker → kept separate."""

    def test_different_ticker_same_title_not_deduplicated(self):
        from src.dedup.matcher import find_duplicates

        r1 = _make_normalized(
            url="https://a.com/r1",
            title="1분기 실적 전망",
            brokerage="미래에셋증권",
            ticker="005930",
            normalized_id="n1",
        )
        r2 = _make_normalized(
            url="https://a.com/r2",
            title="1분기 실적 전망",
            brokerage="미래에셋증권",
            ticker="000660",
            normalized_id="n2",
        )

        groups = find_duplicates([r1, r2])
        assert len(groups) == 2


class TestRevisionDetection:
    """Same title+brokerage+ticker, slightly different title → revision."""

    def test_revision_detected(self):
        from src.dedup.matcher import find_duplicates

        r1 = _make_normalized(
            url="https://a.com/r1",
            title="삼성전자 실적 전망",
            brokerage="미래에셋증권",
            ticker="005930",
            normalized_id="n1",
        )
        r2 = _make_normalized(
            url="https://a.com/r2",
            title="삼성전자 실적 전망 (수정)",
            brokerage="미래에셋증권",
            ticker="005930",
            normalized_id="n2",
        )

        groups = find_duplicates([r1, r2])
        assert len(groups) == 1
        assert groups[0].is_revision is True


class TestSingleReport:
    """Single report → single group, no dedup."""

    def test_single_report(self):
        from src.dedup.matcher import find_duplicates

        r1 = _make_normalized(normalized_id="n1")
        groups = find_duplicates([r1])
        assert len(groups) == 1
        assert groups[0].member_ids == ["n1"]
        assert groups[0].is_revision is False
