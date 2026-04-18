"""Unit tests for FetchAgent PDF fetching integration."""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import MagicMock

import pytest

from src.agents.fetch import FetchAgent
from src.schemas.report import ContentType, FetchStatus, RawReport

TARGET = date(2026, 4, 10)


class _AsyncMockClient:
    """Simple async mock for RateLimitedClient.get()."""

    def __init__(self, responses):
        self._responses = list(responses)
        self._call_count = 0

    async def get(self, url, site_id=None, **kwargs):
        idx = self._call_count
        self._call_count += 1
        resp = self._responses[idx]
        if isinstance(resp, Exception):
            raise resp
        return resp

    @property
    def call_count(self):
        return self._call_count


def _make_raw_report(pdf_url="", extra_hint=None):
    """Helper to build a RawReport with optional pdf_url in metadata_hint."""
    hint = {"title": "Test Report", "brokerage": "테스트증권", "pdf_url": pdf_url}
    if extra_hint:
        hint.update(extra_hint)
    return RawReport(
        site_id="naver_research",
        discovered_url="https://example.com/report/1",
        content_type=ContentType.UNKNOWN,
        metadata_hint=json.dumps(hint, ensure_ascii=False),
        fetch_status=FetchStatus.SKIPPED,
    )


def _mock_html_response():
    resp = MagicMock()
    resp.text = "<html><body>Report content</body></html>"
    resp.status_code = 200
    resp.headers = {"content-type": "text/html"}
    return resp


def _mock_pdf_response(pdf_bytes):
    resp = MagicMock()
    resp.content = pdf_bytes
    resp.status_code = 200
    resp.headers = {"content-type": "application/pdf"}
    return resp


class TestFetchAgentPdf:
    """Tests for PDF fetching within FetchAgent."""

    @pytest.mark.asyncio
    async def test_fetches_pdf_when_url_available(self, sample_pdf_bytes):
        """FetchAgent should fetch PDF and extract text when pdf_url is in hint."""
        client = _AsyncMockClient([
            _mock_html_response(),
            _mock_pdf_response(sample_pdf_bytes),
        ])

        agent = FetchAgent(http_client=client)
        raw = _make_raw_report(pdf_url="https://example.com/report.pdf")
        results = await agent.process([raw], TARGET)

        assert len(results) == 1
        assert results[0].fetch_status == FetchStatus.SUCCESS
        assert results[0].raw_content is not None
        assert results[0].pdf_text is not None
        assert len(results[0].pdf_text) > 0

    @pytest.mark.asyncio
    async def test_html_success_when_pdf_fails(self):
        """HTML fetch should succeed even if PDF fetch raises an exception."""
        client = _AsyncMockClient([
            _mock_html_response(),
            Exception("PDF download timeout"),
        ])

        agent = FetchAgent(http_client=client)
        raw = _make_raw_report(pdf_url="https://example.com/report.pdf")
        results = await agent.process([raw], TARGET)

        assert len(results) == 1
        assert results[0].fetch_status == FetchStatus.SUCCESS
        assert results[0].raw_content is not None
        assert results[0].pdf_text is None  # Gracefully None

    @pytest.mark.asyncio
    async def test_no_pdf_fetch_when_no_url(self):
        """FetchAgent should not attempt PDF fetch when no pdf_url in hint."""
        client = _AsyncMockClient([_mock_html_response()])

        agent = FetchAgent(http_client=client)
        raw = _make_raw_report(pdf_url="")
        results = await agent.process([raw], TARGET)

        assert len(results) == 1
        assert results[0].pdf_text is None
        # Only 1 HTTP call (HTML), not 2
        assert client.call_count == 1

    @pytest.mark.asyncio
    async def test_no_pdf_fetch_when_no_metadata_hint(self):
        """Reports without metadata_hint should skip PDF fetch."""
        client = _AsyncMockClient([_mock_html_response()])

        agent = FetchAgent(http_client=client)
        raw = RawReport(
            site_id="naver_research",
            discovered_url="https://example.com/report/1",
            metadata_hint=None,
        )
        results = await agent.process([raw], TARGET)

        assert len(results) == 1
        assert results[0].pdf_text is None

    @pytest.mark.asyncio
    async def test_pdf_text_none_when_extraction_fails(self):
        """PDF text should be None when PDF content is not text-selectable."""
        fake_pdf = b"%PDF-1.0\ngarbage content that is not valid pdf structure"
        client = _AsyncMockClient([
            _mock_html_response(),
            _mock_pdf_response(fake_pdf),
        ])

        agent = FetchAgent(http_client=client)
        raw = _make_raw_report(pdf_url="https://example.com/report.pdf")
        results = await agent.process([raw], TARGET)

        assert len(results) == 1
        assert results[0].fetch_status == FetchStatus.SUCCESS
        assert results[0].raw_content is not None
        assert results[0].pdf_text is None  # Extraction failed gracefully
