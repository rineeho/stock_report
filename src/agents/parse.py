"""ParseAgent: route to site-specific parser and extract metadata."""

from __future__ import annotations

from datetime import date
from typing import Any

import structlog

from src.agents.base import BaseAgent
from src.config.settings import LLMConfig
from src.parsers.pdf_extractor import extract_metadata_via_llm
from src.parsers.registry import get_parser
from src.schemas.report import FetchStatus, ParsedReport, ParseStatus, RawReport
from src.summarizer.llm_client import BaseLLMClient, create_llm_client

logger = structlog.get_logger()


class ParseAgent(BaseAgent):
    """Routes each RawReport to the appropriate site parser."""

    def __init__(
        self,
        llm_config: LLMConfig | None = None,
        llm_client: BaseLLMClient | None = None,
    ) -> None:
        if llm_client:
            self._llm_client = llm_client
        elif llm_config and llm_config.api_key:
            self._llm_client = create_llm_client(llm_config)
        else:
            self._llm_client = None

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
            if isinstance(raw, dict):
                raw = RawReport(**raw)
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

                # LLM fallback: if analyst/sector/market_type missing and pdf_text available
                if self._llm_client and raw.pdf_text and (
                    not parsed.analyst or not parsed.sector or not parsed.market_type
                ):
                    try:
                        llm_meta = await extract_metadata_via_llm(raw.pdf_text, self._llm_client)
                        if not parsed.analyst and llm_meta.get("analyst"):
                            parsed.analyst = llm_meta["analyst"]
                            logger.info("llm_fallback_analyst", analyst=parsed.analyst, url=raw.discovered_url)
                        if not parsed.sector and llm_meta.get("sector"):
                            parsed.sector = llm_meta["sector"]
                            logger.info("llm_fallback_sector", sector=parsed.sector, url=raw.discovered_url)
                        if not parsed.market_type and llm_meta.get("market_type"):
                            parsed.market_type = llm_meta["market_type"]
                            logger.info("llm_fallback_market_type", market_type=parsed.market_type, url=raw.discovered_url)
                    except Exception as llm_exc:
                        logger.warning("llm_metadata_fallback_failed", error=str(llm_exc))

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
