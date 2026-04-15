"""ClassificationAgent: group CanonicalReports by brokerage, ticker, sector, analyst."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

import structlog

from src.agents.base import BaseAgent
from src.schemas.daily_result import ClassificationResult
from src.schemas.report import CanonicalReport

logger = structlog.get_logger()


def classify_reports(reports: list[CanonicalReport]) -> ClassificationResult:
    """Group reports by brokerage, ticker, sector, analyst.

    Args:
        reports: List of CanonicalReport to classify.

    Returns:
        ClassificationResult with groupings.
    """
    by_brokerage: dict[str, list[str]] = defaultdict(list)
    by_ticker: dict[str, list[str]] = defaultdict(list)
    by_sector: dict[str, list[str]] = defaultdict(list)
    by_analyst: dict[str, list[str]] = defaultdict(list)

    for r in reports:
        cid = r.canonical_id
        by_brokerage[r.brokerage].append(cid)
        if r.ticker:
            by_ticker[r.ticker].append(cid)
        if r.sector:
            by_sector[r.sector].append(cid)
        by_analyst[r.analyst].append(cid)

    return ClassificationResult(
        by_brokerage=dict(by_brokerage),
        by_ticker=dict(by_ticker),
        by_sector=dict(by_sector),
        by_analyst=dict(by_analyst),
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

        result = classify_reports(reports)

        logger.info(
            "classification_summary",
            brokerages=len(result.by_brokerage),
            tickers=len(result.by_ticker),
            sectors=len(result.by_sector),
            analysts=len(result.by_analyst),
        )

        return [result]
