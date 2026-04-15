"""SourceDiscoveryAgent: discovers report URLs from all enabled sites."""

from __future__ import annotations

from datetime import date
from typing import Any

import structlog

from src.agents.base import BaseAgent
from src.config.settings import SiteConfig
from src.parsers.registry import get_parser
from src.schemas.report import RawReport
from src.utils.http import RateLimitedClient

logger = structlog.get_logger()


class SourceDiscoveryAgent(BaseAgent):
    """Discovers report URLs from all enabled sites by fetching their listing pages."""

    def __init__(
        self,
        sites: list[SiteConfig],
        http_client: RateLimitedClient,
    ) -> None:
        self.sites = sites
        self.http = http_client

    @property
    def stage_name(self) -> str:
        return "discover"

    async def process(
        self, items: list[Any], target_date: date, **kwargs: Any
    ) -> list[RawReport]:
        """Fetch listing pages and discover report URLs.

        Args:
            items: Ignored (first stage).
            target_date: Target date for collection.

        Returns:
            List of RawReport with discovered_url set.
        """
        all_reports: list[RawReport] = []

        for site in self.sites:
            parser = get_parser(site.parser_type)
            if parser is None:
                logger.warning("no_parser_for_site", site_id=site.site_id)
                continue

            try:
                response = await self.http.get(site.base_url, site_id=site.site_id)
                html = response.text

                site_reports = await parser.discover_reports(html, base_url=site.base_url)
                logger.info(
                    "site_discovered",
                    site_id=site.site_id,
                    count=len(site_reports),
                )
                all_reports.extend(site_reports)

            except Exception as exc:
                # Per FR-018: isolate site failure, continue with other sites
                logger.error(
                    "site_discovery_failed",
                    site_id=site.site_id,
                    error=str(exc),
                )

        return all_reports
