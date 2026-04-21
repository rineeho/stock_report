"""ClassificationAgent: group CanonicalReports by brokerage, ticker, sector, analyst, theme."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

import structlog

from src.agents.base import BaseAgent
from src.schemas.daily_result import ClassificationResult
from src.schemas.report import CanonicalReport
from src.scrapers.naver_theme import load_mapping

logger = structlog.get_logger()


def _load_theme_lookup() -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """테마 매핑 JSON에서 ticker_to_themes, stock_to_themes 로드.

    Returns:
        (ticker_to_themes, stock_to_themes) — 파일 없으면 빈 dict 쌍.
    """
    from src.config.settings import load_settings

    settings = load_settings()
    mapping = load_mapping(settings.theme_mapping_path)
    if not mapping:
        return {}, {}
    return mapping.get("ticker_to_themes", {}), mapping.get("stock_to_themes", {})


def classify_reports(
    reports: list[CanonicalReport],
    ticker_to_themes: dict[str, list[str]] | None = None,
    stock_to_themes: dict[str, list[str]] | None = None,
) -> ClassificationResult:
    """Group reports by brokerage, ticker, sector, analyst, theme.

    Args:
        reports: List of CanonicalReport to classify.
        ticker_to_themes: 티커→테마 매핑 (없으면 빈 dict).
        stock_to_themes: 종목명→테마 매핑 (없으면 빈 dict).

    Returns:
        ClassificationResult with groupings.
    """
    if ticker_to_themes is None:
        ticker_to_themes = {}
    if stock_to_themes is None:
        stock_to_themes = {}

    by_brokerage: dict[str, list[str]] = defaultdict(list)
    by_ticker: dict[str, list[str]] = defaultdict(list)
    by_sector: dict[str, list[str]] = defaultdict(list)
    by_analyst: dict[str, list[str]] = defaultdict(list)
    by_theme: dict[str, list[str]] = defaultdict(list)

    for r in reports:
        cid = r.canonical_id
        by_brokerage[r.brokerage].append(cid)
        if r.ticker:
            by_ticker[r.ticker].append(cid)
        if r.sector:
            by_sector[r.sector].append(cid)
        by_analyst[r.analyst].append(cid)

        # 테마 매핑: ticker 우선, stock_name fallback
        themes: list[str] = []
        if r.ticker and r.ticker in ticker_to_themes:
            themes = ticker_to_themes[r.ticker]
        elif r.stock_name and r.stock_name in stock_to_themes:
            themes = stock_to_themes[r.stock_name]

        for theme in themes:
            by_theme[theme].append(cid)

    return ClassificationResult(
        by_brokerage=dict(by_brokerage),
        by_ticker=dict(by_ticker),
        by_sector=dict(by_sector),
        by_analyst=dict(by_analyst),
        by_theme=dict(by_theme),
    )


class ClassificationAgent(BaseAgent):
    """Groups CanonicalReports by various criteria."""

    @property
    def stage_name(self) -> str:
        return "classify"

    async def process(
        self, items: list[Any], target_date: date, **kwargs: Any
    ) -> list[ClassificationResult]:
        reports: list[CanonicalReport] = []
        for item in items:
            if isinstance(item, CanonicalReport):
                reports.append(item)
            elif isinstance(item, dict) and "brokerage" in item:
                reports.append(CanonicalReport(**item))
            # Skip non-CanonicalReport items (e.g., Summary from summarize stage)

        # If no canonical reports in items, load from deduplicate checkpoint
        if not reports:
            checkpoint = kwargs.get("checkpoint_manager")
            if checkpoint:
                from src.schemas.pipeline import StageEnvelope
                cached = checkpoint.load(target_date, "deduplicate")
                if cached:
                    for envelope_data in cached:
                        if isinstance(envelope_data, StageEnvelope):
                            for it in envelope_data.items:
                                if isinstance(it, dict):
                                    reports.append(CanonicalReport(**it))
                                elif isinstance(it, CanonicalReport):
                                    reports.append(it)
                        elif isinstance(envelope_data, dict):
                            reports.append(CanonicalReport(**envelope_data))
                        elif isinstance(envelope_data, CanonicalReport):
                            reports.append(envelope_data)

        # 테마 매핑 로드
        ticker_to_themes, stock_to_themes = _load_theme_lookup()

        result = classify_reports(reports, ticker_to_themes, stock_to_themes)

        logger.info(
            "classification_summary",
            brokerages=len(result.by_brokerage),
            tickers=len(result.by_ticker),
            sectors=len(result.by_sector),
            analysts=len(result.by_analyst),
            themes=len(result.by_theme),
        )

        return [result]
