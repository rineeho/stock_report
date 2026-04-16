"""BaseSiteParser abstract class with discover/parse and multi-strategy date extraction."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from datetime import date

import structlog
from bs4 import BeautifulSoup

from src.schemas.report import DateSource, ParsedReport, RawReport

logger = structlog.get_logger()


class BaseSiteParser(ABC):
    """Abstract base class for site-specific parsers.

    Subclasses must implement discover_reports() and parse_report().
    """

    @property
    @abstractmethod
    def site_id(self) -> str:
        """Return the site identifier."""

    @abstractmethod
    async def discover_reports(self, html_content: str, base_url: str) -> list[RawReport]:
        """Discover report URLs from a listing page.

        Args:
            html_content: HTML content of the listing page.
            base_url: Base URL for resolving relative links.

        Returns:
            List of RawReport with discovered_url set.
        """

    @abstractmethod
    async def parse_report(self, raw: RawReport) -> ParsedReport:
        """Parse a single report and extract metadata.

        Args:
            raw: RawReport with raw_content populated.

        Returns:
            ParsedReport with extracted metadata.
        """

    def get_page_url(self, base_url: str, page: int) -> str | None:
        """Return URL for the given page number (1-indexed).

        Returns None if pagination is not supported.
        Subclasses should override this to enable multi-page discovery.
        """
        return None

    def extract_date_multi_strategy(self, html_content: str) -> tuple[date | None, DateSource | None]:
        """Multi-strategy date extraction per R10.

        Strategy order: HTML meta tags → JSON-LD → body regex patterns.

        Args:
            html_content: HTML content to extract date from.

        Returns:
            Tuple of (extracted_date, source_strategy) or (None, None).
        """
        from src.utils.timezone import parse_date_kst

        soup = BeautifulSoup(html_content, "lxml")

        # Strategy 1: HTML meta tags
        for meta_name in [
            "article:published_time",
            "og:article:published_time",
            "date",
            "DC.date",
            "pubdate",
        ]:
            meta = soup.find("meta", attrs={"property": meta_name}) or soup.find(
                "meta", attrs={"name": meta_name}
            )
            if meta and meta.get("content"):
                d = parse_date_kst(meta["content"][:10])
                if d:
                    return d, DateSource.META_TAG

        # Strategy 2: JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                import json

                data = json.loads(script.string or "")
                if isinstance(data, dict):
                    for key in ["datePublished", "dateCreated", "dateModified"]:
                        if key in data:
                            d = parse_date_kst(str(data[key])[:10])
                            if d:
                                return d, DateSource.JSON_LD
            except (json.JSONDecodeError, TypeError):
                continue

        # Strategy 3: Body text regex patterns
        text = soup.get_text()
        patterns = [
            r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})",  # 2026-04-10, 2026.04.10
            r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일",  # 2026년 4월 10일
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                # Take the first reasonable date
                for m in matches:
                    try:
                        d = date(int(m[0]), int(m[1]), int(m[2]))
                        # Sanity check: within last 30 days
                        from src.utils.timezone import today_kst

                        if abs((today_kst() - d).days) <= 30:
                            return d, DateSource.BODY_PATTERN
                    except ValueError:
                        continue

        return None, None
