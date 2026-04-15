"""ParseAgent: route to site-specific parser and extract metadata."""

from __future__ import annotations

from datetime import date
from typing import Any

import structlog

from src.agents.base import BaseAgent
from src.parsers.registry import get_parser
from src.schemas.report import FetchStatus, ParsedReport, ParseStatus, RawReport

logger = structlog.get_logger()


class ParseAgent(BaseAgent):
    """Routes each RawReport to the appropriate site parser."""

    @property
    def stage_name(self) -> str:
        return "parse"

    async def process(
        self, items: list[RawReport], target_date: date, **kwargs: Any
    ) -> list[ParsedReport]:
        """Parse each successfully-fetched RawReport.

        Failed fetches are converted to ParsedReport with FAILED status
        so downstream stages can account for them in stats.
        """
        results: list[ParsedReport] = []

        for raw in items:
            if raw.fetch_status == FetchStatus.FAILED or (raw.raw_content is None and raw.metadata_hint is None):
                results.append(
                    ParsedReport(
                        raw_id=raw.raw_id,
                        source_url=raw.discovered_url,
                        parse_status=ParseStatus.FAILED,
                        parse_errors=["fetch_failed: " + (raw.fetch_error or "no_content")],
                    )
                )
                continue

            parser = get_parser(raw.site_id)
            if parser is None:
                results.append(
                    ParsedReport(
                        raw_id=raw.raw_id,
                        source_url=raw.discovered_url,
                        parse_status=ParseStatus.FAILED,
                        parse_errors=[f"no_parser_for_site:{raw.site_id}"],
                    )
                )
                continue

            try:
                parsed = await parser.parse_report(raw)
                results.append(parsed)
            except Exception as exc:
                logger.warning("parse_failed", url=raw.discovered_url, error=str(exc))
                results.append(
                    ParsedReport(
                        raw_id=raw.raw_id,
                        source_url=raw.discovered_url,
                        parse_status=ParseStatus.FAILED,
                        parse_errors=[f"parse_error:{exc}"],
                    )
                )

        return results
