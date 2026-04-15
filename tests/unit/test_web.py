"""Unit tests for web data_loader and FastAPI endpoints."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from src.schemas.daily_result import (
    ClassificationResult,
    DailyResult,
    PipelineStats,
)
from src.schemas.report import CanonicalReport
from src.schemas.summary import ExtractedInfo, GeneratedSummary, Summary
from src.web.app import create_app
from src.web.data_loader import list_available_dates, load_daily_result


def _make_daily_result() -> DailyResult:
    report = CanonicalReport(
        canonical_id="c1",
        title="테스트 리포트",
        published_date=date(2026, 4, 10),
        brokerage="테스트증권",
        analyst="N/A",
        ticker="000660",
        stock_name="SK하이닉스",
        source_urls=["https://example.com/1"],
        primary_url="https://example.com/1",
        body_text="본문 텍스트",
        duplicate_count=1,
    )
    summary = Summary(
        canonical_id="c1",
        extracted=ExtractedInfo(target_price=230000, rating="BUY"),
        generated=GeneratedSummary(
            key_points=["핵심 포인트 1"],
            one_line="한줄 요약",
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
            by_brokerage={"테스트증권": ["c1"]},
            by_ticker={"000660": ["c1"]},
        ),
        pipeline_stats=PipelineStats(total_discovered=30, duration_ms=5000),
    )


@pytest.fixture()
def data_dir(tmp_path: Path) -> Path:
    """Create a temporary data output directory with a sample report."""
    date_dir = tmp_path / "2026-04-10"
    date_dir.mkdir()
    result = _make_daily_result()
    with open(date_dir / "daily_report.json", "w", encoding="utf-8") as f:
        json.dump(result.model_dump(mode="json"), f, ensure_ascii=False)
    return tmp_path


# --- data_loader tests ---

def test_list_available_dates(data_dir: Path):
    dates = list_available_dates(data_dir)
    assert dates == ["2026-04-10"]


def test_list_available_dates_empty(tmp_path: Path):
    assert list_available_dates(tmp_path) == []


def test_load_daily_result(data_dir: Path):
    result = load_daily_result("2026-04-10", data_dir)
    assert result is not None
    assert len(result.reports) == 1
    assert result.reports[0].title == "테스트 리포트"


def test_load_daily_result_not_found(data_dir: Path):
    assert load_daily_result("2099-01-01", data_dir) is None


# --- API tests ---

@pytest.fixture()
def client(data_dir: Path) -> TestClient:
    app = create_app(data_dir=data_dir)
    return TestClient(app)


def test_api_dates(client: TestClient):
    resp = client.get("/api/dates")
    assert resp.status_code == 200
    assert "2026-04-10" in resp.json()["dates"]


def test_api_summary(client: TestClient):
    resp = client.get("/api/reports/2026-04-10/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["report_count"] == 1
    assert "테스트증권" in data["brokerage_counts"]


def test_api_report_list(client: TestClient):
    resp = client.get("/api/reports/2026-04-10/list")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["reports"][0]["title"] == "테스트 리포트"
    assert data["reports"][0]["summary"] is not None


def test_api_report_list_filter_brokerage(client: TestClient):
    resp = client.get("/api/reports/2026-04-10/list?brokerage=테스트증권")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1

    resp2 = client.get("/api/reports/2026-04-10/list?brokerage=없는증권")
    assert resp2.status_code == 200
    assert resp2.json()["count"] == 1  # no filter applied for unknown brokerage


def test_api_report_detail(client: TestClient):
    resp = client.get("/api/reports/2026-04-10/detail/c1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "테스트 리포트"
    assert data["summary"]["generated"]["one_line"] == "한줄 요약"


def test_api_404_date(client: TestClient):
    resp = client.get("/api/reports/2099-01-01/summary")
    assert resp.status_code == 404


def test_api_404_report(client: TestClient):
    resp = client.get("/api/reports/2026-04-10/detail/nonexistent")
    assert resp.status_code == 404


def test_serve_index(client: TestClient):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "리포트 대시보드" in resp.text
