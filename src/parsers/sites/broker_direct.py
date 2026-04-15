"""broker_direct site parser stub.

Placeholder for 증권사 직접 리서치센터 parser.
Currently disabled in sites.yaml — to be implemented when specific
broker research center URLs and page structures are available.
"""

from __future__ import annotations

from src.parsers.base import BaseSiteParser
from src.parsers.registry import register
from src.schemas.report import ParsedReport, ParseStatus, RawReport


class BrokerDirectParser(BaseSiteParser):
    """Stub parser for 증권사 직접 리서치센터."""

    @property
    def site_id(self) -> str:
        return "broker_direct"

    async def discover_reports(self, html_content: str, base_url: str) -> list[RawReport]:
        """Not implemented — returns empty list."""
        return []

    async def parse_report(self, raw: RawReport) -> ParsedReport:
        """Not implemented — returns failed ParsedReport."""
        return ParsedReport(
            raw_id=raw.raw_id,
            title=None,
            source_url=raw.discovered_url,
            parse_status=ParseStatus.FAILED,
            parse_errors=["broker_direct parser not implemented"],
        )


register("broker_direct", BrokerDirectParser)
