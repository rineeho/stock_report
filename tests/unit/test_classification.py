"""Classification tests: group by brokerage, ticker, sector, analyst."""

from __future__ import annotations

from datetime import date

from src.schemas.report import CanonicalReport


def _make_report(**overrides) -> CanonicalReport:
    defaults = dict(
        title="테스트 리포트",
        published_date=date(2026, 4, 10),
        brokerage="미래에셋증권",
        analyst="김성민",
        ticker="005930",
        stock_name="삼성전자",
        sector="반도체",
        source_urls=["https://example.com/r1"],
        primary_url="https://example.com/r1",
        has_revision=False,
        duplicate_count=1,
    )
    defaults.update(overrides)
    return CanonicalReport(**defaults)


class TestClassificationByBrokerage:
    def test_group_by_brokerage(self):
        from src.agents.classify import classify_reports

        reports = [
            _make_report(canonical_id="c1", brokerage="미래에셋증권"),
            _make_report(canonical_id="c2", brokerage="미래에셋증권"),
            _make_report(canonical_id="c3", brokerage="한국투자증권"),
        ]
        result = classify_reports(reports)
        assert len(result.by_brokerage["미래에셋증권"]) == 2
        assert len(result.by_brokerage["한국투자증권"]) == 1


class TestClassificationByTicker:
    def test_group_by_ticker(self):
        from src.agents.classify import classify_reports

        reports = [
            _make_report(canonical_id="c1", ticker="005930"),
            _make_report(canonical_id="c2", ticker="005930"),
            _make_report(canonical_id="c3", ticker="000660"),
        ]
        result = classify_reports(reports)
        assert len(result.by_ticker["005930"]) == 2
        assert len(result.by_ticker["000660"]) == 1


class TestClassificationBySector:
    def test_group_by_sector(self):
        from src.agents.classify import classify_reports

        reports = [
            _make_report(canonical_id="c1", sector="반도체"),
            _make_report(canonical_id="c2", sector="반도체"),
            _make_report(canonical_id="c3", sector="자동차"),
        ]
        result = classify_reports(reports)
        assert len(result.by_sector["반도체"]) == 2
        assert len(result.by_sector["자동차"]) == 1

    def test_none_sector_excluded(self):
        from src.agents.classify import classify_reports

        reports = [
            _make_report(canonical_id="c1", sector=None),
            _make_report(canonical_id="c2", sector="반도체"),
        ]
        result = classify_reports(reports)
        assert "반도체" in result.by_sector
        assert None not in result.by_sector


class TestClassificationByAnalyst:
    def test_group_by_analyst(self):
        from src.agents.classify import classify_reports

        reports = [
            _make_report(canonical_id="c1", analyst="김성민"),
            _make_report(canonical_id="c2", analyst="김성민"),
            _make_report(canonical_id="c3", analyst="박지연"),
        ]
        result = classify_reports(reports)
        assert len(result.by_analyst["김성민"]) == 2
        assert len(result.by_analyst["박지연"]) == 1


class TestEmptyInput:
    def test_empty_reports(self):
        from src.agents.classify import classify_reports

        result = classify_reports([])
        assert result.by_brokerage == {}
        assert result.by_ticker == {}
