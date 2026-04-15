"""FetchAgent: download HTML/PDF via rate-limited HTTP client."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import structlog

from src.agents.base import BaseAgent
from src.schemas.report import ContentType, FetchStatus, RawReport
from src.utils.http import RateLimitedClient

logger = structlog.get_logger()


def _detect_content_type(url: str, content_type_header: str) -> ContentType:
    if "pdf" in url.lower() or "pdf" in content_type_header.lower():
        return ContentType.PDF
    if "html" in content_type_header.lower():
        return ContentType.HTML
    return ContentType.UNKNOWN


class FetchAgent(BaseAgent):
    """Downloads report content for each RawReport."""

    def __init__(self, http_client: RateLimitedClient) -> None:
        self.http = http_client

    @property
    def stage_name(self) -> str:
        return "fetch"

    async def process(
        self, items: list[RawReport], target_date: date, **kwargs: Any
    ) -> list[RawReport]:
        """Fetch raw_content for each RawReport that has a hint (not full HTML).

        Reports that already have full HTML content (raw_content starts with '<')
        are passed through without a second fetch.
        """
        results: list[RawReport] = []

        for raw in items:
            # Already has full HTML from discovery step
            if raw.raw_content and raw.raw_content.strip().startswith("<"):
                updated = raw.model_copy(
                    update={
                        "fetch_status": FetchStatus.SUCCESS,
                        "fetched_at": datetime.now().astimezone(),
                    }
                )
                results.append(updated)
                continue

            try:
                response = await self.http.get(raw.discovered_url, site_id=raw.site_id)
                content_type = _detect_content_type(
                    raw.discovered_url,
                    response.headers.get("content-type", ""),
                )
                updated = raw.model_copy(
                    update={
                        "raw_content": response.text,
                        "content_type": content_type,
                        "fetch_status": FetchStatus.SUCCESS,
                        "fetched_at": datetime.now().astimezone(),
                    }
                )
                results.append(updated)
                logger.debug("fetched", url=raw.discovered_url, status=response.status_code)

            except Exception as exc:
                # Per FR-018: isolate failure, mark report as failed
                logger.warning("fetch_failed", url=raw.discovered_url, error=str(exc))
                updated = raw.model_copy(
                    update={
                        "fetch_status": FetchStatus.FAILED,
                        "fetch_error": str(exc),
                        "fetched_at": datetime.now().astimezone(),
                    }
                )
                results.append(updated)

        return results
