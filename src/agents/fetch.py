"""FetchAgent: download HTML/PDF via rate-limited HTTP client."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

import structlog

from src.agents.base import BaseAgent
from src.parsers.pdf_extractor import extract_text_from_pdf
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
        Also downloads and extracts text from PDF when pdf_url is in metadata_hint.
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
                updated = await self._enrich_with_pdf(updated)
                results.append(updated)
                continue

            try:
                response = await self.http.get(raw.discovered_url, site_id=raw.site_id)
                content_type = _detect_content_type(
                    raw.discovered_url,
                    response.headers.get("content-type", ""),
                )

                if content_type == ContentType.PDF:
                    # PDF response: extract text directly, don't store binary as text
                    result = extract_text_from_pdf(response.content)
                    updated = raw.model_copy(
                        update={
                            "content_type": ContentType.PDF,
                            "pdf_text": result.text if result.success else None,
                            "fetch_status": FetchStatus.SUCCESS,
                            "fetched_at": datetime.now().astimezone(),
                        }
                    )
                    results.append(updated)
                    logger.debug(
                        "fetched_pdf",
                        url=raw.discovered_url,
                        pages=result.page_count,
                        success=result.success,
                    )
                    continue

                updated = raw.model_copy(
                    update={
                        "raw_content": response.text,
                        "content_type": content_type,
                        "fetch_status": FetchStatus.SUCCESS,
                        "fetched_at": datetime.now().astimezone(),
                    }
                )
                updated = await self._enrich_with_pdf(updated)
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

    async def _enrich_with_pdf(self, raw: RawReport) -> RawReport:
        """Download PDF and extract text if pdf_url is in metadata_hint.

        PDF text is extracted using pdfplumber (text-selectable PDFs only).
        On failure, returns the original RawReport unchanged.
        """
        if not raw.metadata_hint:
            return raw

        try:
            hint = json.loads(raw.metadata_hint)
        except (ValueError, TypeError):
            return raw

        pdf_url = hint.get("pdf_url")
        if not pdf_url:
            return raw

        try:
            response = await self.http.get(pdf_url, site_id=raw.site_id)
            result = extract_text_from_pdf(response.content)
            if result.success:
                logger.info(
                    "pdf_extracted",
                    url=pdf_url,
                    pages=result.page_count,
                    chars=result.char_count,
                )
                return raw.model_copy(update={"pdf_text": result.text})
            else:
                logger.debug(
                    "pdf_extraction_unsuccessful",
                    url=pdf_url,
                    error=result.error,
                )
        except Exception as exc:
            logger.warning("pdf_fetch_failed", url=pdf_url, error=str(exc))

        return raw
