"""SummarizationAgent: generate summaries for CanonicalReports via LLM."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import structlog

from src.agents.base import BaseAgent
from src.config.settings import LLMConfig
from src.schemas.report import CanonicalReport
from src.schemas.summary import ExtractedInfo, GeneratedSummary, Summary
from src.summarizer.llm_client import BaseLLMClient, create_llm_client
from src.summarizer.prompt_templates import SYSTEM_PROMPT, build_summary_prompt

logger = structlog.get_logger()

_INACCESSIBLE = "본문 접근 불가"


class SummarizationAgent(BaseAgent):
    """Generates summaries for each CanonicalReport.

    Uses LLM to produce extracted (from original) + generated (LLM summary).
    Per FR-023: body_text=None → "본문 접근 불가".
    Per Constitution VI: extracted fields must come from source only.
    """

    def __init__(self, llm_config: LLMConfig | None = None, llm_client: BaseLLMClient | None = None) -> None:
        if llm_client:
            self.llm = llm_client
        elif llm_config:
            self.llm = create_llm_client(llm_config)
        else:
            from src.summarizer.llm_client import MockLLMClient
            self.llm = MockLLMClient()

    @property
    def stage_name(self) -> str:
        return "summarize"

    async def process(
        self, items: list[CanonicalReport], target_date: date, **kwargs: Any
    ) -> list[Summary]:
        results: list[Summary] = []

        for item in items:
            if isinstance(item, dict):
                item = CanonicalReport(**item)

            try:
                summary = await self._summarize_report(item)
                results.append(summary)
            except Exception as exc:
                logger.warning("summarize_failed", canonical_id=item.canonical_id, error=str(exc))
                # Create fallback summary
                results.append(self._fallback_summary(item))

        return results

    async def _summarize_report(self, report: CanonicalReport) -> Summary:
        """Generate summary for a single report."""
        prompt = build_summary_prompt(
            title=report.title,
            brokerage=report.brokerage,
            stock_name=report.stock_name,
            ticker=report.ticker,
            body_text=report.body_text,
        )

        raw_response = await self.llm.generate(prompt, system=SYSTEM_PROMPT)
        data = self._parse_response(raw_response)

        extracted_data = data.get("extracted", {})
        generated_data = data.get("generated", {})

        extracted = ExtractedInfo(
            target_price=extracted_data.get("target_price"),
            previous_target_price=extracted_data.get("previous_target_price"),
            target_price_change=extracted_data.get("target_price_change"),
            rating=extracted_data.get("rating"),
            earnings=extracted_data.get("earnings"),
            analyst=extracted_data.get("analyst"),
            sector=extracted_data.get("sector"),
        )

        key_points = generated_data.get("key_points", ["요약 생성 실패"])
        if not key_points:
            key_points = ["요약 생성 실패"]

        generated = GeneratedSummary(
            key_points=key_points[:5],
            one_line=generated_data.get("one_line", report.title),
            opinion_summary=generated_data.get("opinion_summary"),
        )

        return Summary(
            canonical_id=report.canonical_id,
            extracted=extracted,
            generated=generated,
        )

    def _parse_response(self, raw: str) -> dict:
        """Parse LLM JSON response, handling markdown code blocks."""
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            text = "\n".join(lines)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning("llm_response_parse_failed", raw=text[:200])
            return {}

    def _fallback_summary(self, report: CanonicalReport) -> Summary:
        """Create a minimal summary when LLM fails."""
        return Summary(
            canonical_id=report.canonical_id,
            extracted=ExtractedInfo(target_price=None, rating=None, earnings=None, analyst=None, sector=None),
            generated=GeneratedSummary(
                key_points=["요약 생성 실패"],
                one_line=report.title,
                opinion_summary=None,
            ),
        )
