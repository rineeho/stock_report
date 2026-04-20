"""ValidationAgent: compare published_date to target_date in KST."""

from __future__ import annotations

from datetime import date
from typing import Any

import structlog

from src.agents.base import BaseAgent
from src.schemas.report import ParsedReport, ParseStatus, ValidatedReport, ValidationStatus

logger = structlog.get_logger()


class ValidationAgent(BaseAgent):
    """Validates each ParsedReport's date against target_date.

    State transitions per data-model.md:
    - published_date == target_date → VERIFIED
    - published_date is None → UNVERIFIED
    - published_date != target_date → REJECTED
    """

    @property
    def stage_name(self) -> str:
        return "validate"

    async def process(
        self, items: list[ParsedReport], target_date: date, **kwargs: Any
    ) -> list[ValidatedReport]:
        """Validate all parsed reports; return all (including rejected/unverified).

        Per spec FR-005: rejected/unverified are still returned but marked.
        NormalizationAgent will filter out rejected ones.
        """
        results: list[ValidatedReport] = []

        for parsed in items:
            if parsed.parse_status == ParseStatus.FAILED:
                # Skip entirely failed parses
                continue

            if parsed.published_date is None:
                status = ValidationStatus.UNVERIFIED
                date_match = False
                rejection_reason = None
            elif parsed.published_date == target_date:
                status = ValidationStatus.VERIFIED
                date_match = True
                rejection_reason = None
            else:
                status = ValidationStatus.REJECTED
                date_match = False
                rejection_reason = (
                    f"date_mismatch: {parsed.published_date} != {target_date}"
                )
                logger.debug(
                    "report_rejected",
                    title=parsed.title,
                    published=str(parsed.published_date),
                    target=str(target_date),
                )

            results.append(
                ValidatedReport(
                    parsed_id=parsed.parsed_id,
                    target_date=target_date,
                    date_match=date_match,
                    validation_status=status,
                    rejection_reason=rejection_reason,
                    title=parsed.title,
                    published_date=parsed.published_date,
                    published_date_source=parsed.published_date_source,
                    brokerage=parsed.brokerage,
                    analyst=parsed.analyst,
                    ticker=parsed.ticker,
                    stock_name=parsed.stock_name,
                    sector=parsed.sector,
                    market_type=parsed.market_type,
                    body_text=parsed.body_text,
                    source_url=parsed.source_url,
                    pdf_url=parsed.pdf_url,
                )
            )

        verified = sum(1 for r in results if r.validation_status == ValidationStatus.VERIFIED)
        unverified = sum(1 for r in results if r.validation_status == ValidationStatus.UNVERIFIED)
        rejected = sum(1 for r in results if r.validation_status == ValidationStatus.REJECTED)
        logger.info(
            "validation_summary",
            verified=verified,
            unverified=unverified,
            rejected=rejected,
        )

        return results
