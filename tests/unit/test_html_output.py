"""Unit tests for HTML output generation."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from src.output.html import generate_html, write_html
from src.schemas.daily_result import (
    ClassificationResult,
    DailyResult,
    PipelineStats,
)
from src.schemas.report import CanonicalReport
from src.schemas.summary import ExtractedInfo, GeneratedSummary, Summary


def _make_daily_result() -> DailyResult:
    report = CanonicalReport(
        canonical_id="c1",
        title="HBM 중심 AI 반도체 수요 강세",
        published_date=date(2026, 4, 10),
        brokerage="미래에셋증권",
        analyst="N/A",
        ticker="000660",
        stock_name="SK하이닉스",
        source_urls=["https://example.com/1"],
        primary_url="https://example.com/1",
        body_text="본문",
        duplicate_count=1,
    )
    summary = Summary(
        canonical_id="c1",
        extracted=ExtractedInfo(target_price=230000, rating="BUY"),
        generated=GeneratedSummary(
            key_points=["HBM 매출 증가", "AI 수요 확대"],
            one_line="HBM 매출 급증에 따른 실적 개선",
        ),
    )
    return DailyResult(
        target_date=date(2026, 4, 10),
        total_discovered=30,
        total_validated=28,
        total_unverified=2,
        total_deduplicated=25,
        reports=[report],
        summaries=[summary],
        classifications=ClassificationResult(
            by_brokerage={"미래에셋증권": ["c1"]},
            by_ticker={"000660": ["c1"]},
        ),
        pipeline_stats=PipelineStats(
            total_discovered=30,
            total_fetched=30,
            total_parsed=30,
            total_validated=28,
            total_deduplicated=25,
            total_summarized=25,
            duration_ms=5000,
        ),
    )


def test_generate_html_contains_expected_sections():
    result = _make_daily_result()
    html = generate_html(result)

    assert "<!DOCTYPE html>" in html
    assert "일일 리포트 요약 — 2026-04-10" in html
    # Stats
    assert "30</strong>건" in html
    # Brokerage section
    assert "미래에셋증권" in html
    # Title
    assert "HBM 중심 AI 반도체 수요 강세" in html
    # Ticker section
    assert "SK하이닉스" in html
    assert "000660" in html
    # Summary
    assert "HBM 매출 급증에 따른 실적 개선" in html
    assert "HBM 매출 증가" in html
    # Extracted
    assert "230,000원" in html
    assert "BUY" in html
    # Pipeline stats table
    assert "파이프라인 통계" in html
    assert "5000ms" in html


def test_generate_html_escapes_special_chars():
    result = _make_daily_result()
    result.reports[0].title = '<script>alert("xss")</script>'
    html = generate_html(result)

    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_write_html_creates_file(tmp_path: Path):
    result = _make_daily_result()
    out_path = write_html(result, tmp_path)

    assert out_path.exists()
    assert out_path.name == "daily_report.html"
    content = out_path.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content


def test_generate_html_empty_reports():
    result = DailyResult(target_date=date(2026, 4, 10))
    html = generate_html(result)

    assert "<!DOCTYPE html>" in html
    assert "2026-04-10" in html
    assert "파이프라인 통계" in html
