"""NormalizationAgent: apply normalizers, filter missing required fields."""

from __future__ import annotations

from datetime import date
from typing import Any

import structlog

from src.agents.base import BaseAgent
from src.normalizers.brokerage import normalize_brokerage
from src.normalizers.ticker import normalize_stock_name, normalize_ticker_code
from src.schemas.report import NormalizedReport, ValidatedReport, ValidationStatus

logger = structlog.get_logger()

_INACCESSIBLE_PLACEHOLDER = "본문 접근 불가"
_UNKNOWN_ANALYST = "N/A"


class NormalizationAgent(BaseAgent):
    """Normalizes reports and filters out those missing required fields.

    Per Constitution I + FR-007: 5 required fields must be present.
    Only VERIFIED reports proceed (UNVERIFIED/REJECTED are dropped here).
    """

    @property
    def stage_name(self) -> str:
        return "normalize"

    async def process(
        self, items: list[ValidatedReport], target_date: date, **kwargs: Any
    ) -> list[NormalizedReport]:
        results: list[NormalizedReport] = []
        skipped = 0

        for validated in items:
            # Only process verified reports
            if validated.validation_status != ValidationStatus.VERIFIED:
                skipped += 1
                continue

            # Normalize fields
            title = validated.title.strip() if validated.title else None
            published_date = validated.published_date
            brokerage = normalize_brokerage(validated.brokerage) if validated.brokerage else None
            analyst = validated.analyst.strip() if validated.analyst else _UNKNOWN_ANALYST
            ticker = normalize_ticker_code(validated.ticker)
            stock_name = normalize_stock_name(validated.stock_name)
            source_url = validated.source_url

            # Constitution I: all 5 required fields must be present
            required = {
                "title": title,
                "published_date": published_date,
                "brokerage": brokerage,
                "analyst": analyst,
                "source_url": source_url,
            }
            missing = [k for k, v in required.items() if not v]
            if missing:
                logger.warning(
                    "normalized_missing_required_fields",
                    missing=missing,
                    url=source_url,
                )
                skipped += 1
                continue

            # FR-023: inaccessible body text
            body_text = validated.body_text
            if body_text is None:
                body_text = _INACCESSIBLE_PLACEHOLDER

            results.append(
                NormalizedReport(
                    validated_id=validated.validated_id,
                    title=title,
                    published_date=published_date,
                    brokerage=brokerage,
                    analyst=analyst,
                    ticker=ticker,
                    stock_name=stock_name,
                    sector=validated.sector,
                    source_url=source_url,
                    body_text=body_text,
                    pdf_url=validated.pdf_url,
                )
            )

        logger.info(
            "normalization_summary",
            output=len(results),
            skipped=skipped,
        )
        return results
