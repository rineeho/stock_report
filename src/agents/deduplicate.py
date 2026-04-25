"""DeduplicationAgent: group NormalizedReports, select canonical, merge source_urls."""

from __future__ import annotations

from datetime import date
from typing import Any

import structlog

from src.agents.base import BaseAgent
from src.dedup.matcher import find_duplicates
from src.schemas.report import CanonicalReport, NormalizedReport

logger = structlog.get_logger()

# URL patterns that are PDF downloads, not detail pages
_PDF_DOWNLOAD_PATTERNS = ("downpdf", "/download/", ".pdf")


def _pick_primary_url(all_urls: list[str], default: str) -> str:
    """Select the best primary URL, preferring browseable detail pages over PDF downloads."""
    for url in all_urls:
        if not any(pat in url for pat in _PDF_DOWNLOAD_PATTERNS):
            return url
    # No browseable URL found; fall back to list page for known sites
    if "consensus.hankyung.com" in default:
        return "https://consensus.hankyung.com/analysis/list?skinType=business"
    return default


class DeduplicationAgent(BaseAgent):
    """Groups NormalizedReports by duplicates and produces CanonicalReports.

    Each DeduplicationGroup selects one canonical report; duplicates'
    source_urls are merged into the canonical.
    """

    @property
    def stage_name(self) -> str:
        return "deduplicate"

    async def process(
        self, items: list[NormalizedReport], target_date: date, **kwargs: Any
    ) -> list[CanonicalReport]:
        # Build lookup by normalized_id
        lookup: dict[str, NormalizedReport] = {}
        for item in items:
            if isinstance(item, dict):
                item = NormalizedReport(**item)
            lookup[item.normalized_id] = item

        groups = find_duplicates(list(lookup.values()))

        results: list[CanonicalReport] = []
        for group in groups:
            canonical = lookup.get(group.canonical_id)
            if canonical is None:
                continue

            # Merge source_urls from all members
            all_urls = []
            for mid in group.member_ids:
                member = lookup.get(mid)
                if member and member.source_url not in all_urls:
                    all_urls.append(member.source_url)

            # Pick best primary_url: prefer detail page over PDF download
            primary_url = _pick_primary_url(all_urls, canonical.source_url)

            results.append(
                CanonicalReport(
                    canonical_id=group.canonical_id,
                    title=canonical.title,
                    published_date=canonical.published_date,
                    brokerage=canonical.brokerage,
                    analyst=canonical.analyst,
                    ticker=canonical.ticker,
                    stock_name=canonical.stock_name,
                    sector=canonical.sector,
                    market_type=canonical.market_type,
                    is_ai_generated=canonical.is_ai_generated,
                    source_urls=all_urls,
                    primary_url=primary_url,
                    body_text=canonical.body_text,
                    pdf_url=canonical.pdf_url,
                    has_revision=group.is_revision,
                    duplicate_count=len(group.member_ids),
                )
            )

        logger.info(
            "dedup_agent_summary",
            input=len(items),
            output=len(results),
            duplicates_merged=len(items) - len(results),
        )

        return results
