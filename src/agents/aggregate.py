"""AggregationAgent: assemble DailyResult from pipeline outputs."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import structlog

from src.agents.base import BaseAgent
from src.schemas.daily_result import ClassificationResult, DailyResult, PipelineStats
from src.schemas.report import CanonicalReport
from src.schemas.summary import Summary
from src.utils.timezone import KST

logger = structlog.get_logger()


class AggregationAgent(BaseAgent):
    """Assembles DailyResult from all pipeline stage outputs.

    Receives classification results from classify stage and
    collects CanonicalReports + Summaries from pipeline context.
    """

    @property
    def stage_name(self) -> str:
        return "aggregate"

    async def process(
        self, items: list[Any], target_date: date, **kwargs: Any
    ) -> list[DailyResult]:
        """Aggregate all pipeline outputs into a DailyResult.

        The items from the previous stage (classify) are ClassificationResults.
        CanonicalReports and Summaries come from kwargs or pipeline context.
        """
        # Items from classify stage
        classification = ClassificationResult()
        if items:
            item = items[0]
            if isinstance(item, dict):
                classification = ClassificationResult(**item)
            elif isinstance(item, ClassificationResult):
                classification = item

        # Get pipeline context
        canonical_reports = kwargs.get("canonical_reports", [])
        summaries = kwargs.get("summaries", [])
        pipeline_stats = kwargs.get("pipeline_stats", PipelineStats())

        if isinstance(pipeline_stats, dict):
            pipeline_stats = PipelineStats(**pipeline_stats)

        # Build reports list
        reports = []
        for r in canonical_reports:
            if isinstance(r, dict):
                r = CanonicalReport(**r)
            reports.append(r)

        summary_list = []
        for s in summaries:
            if isinstance(s, dict):
                s = Summary(**s)
            summary_list.append(s)

        result = DailyResult(
            target_date=target_date,
            total_discovered=pipeline_stats.total_discovered,
            total_fetched=pipeline_stats.total_fetched,
            total_validated=pipeline_stats.total_validated,
            total_unverified=pipeline_stats.total_unverified,
            total_deduplicated=len(reports),
            reports=reports,
            summaries=summary_list,
            classifications=classification,
            pipeline_stats=pipeline_stats,
            created_at=datetime.now(KST),
        )

        logger.info(
            "aggregation_complete",
            reports=len(reports),
            summaries=len(summary_list),
        )

        return [result]
