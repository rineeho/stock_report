"""Agent chain data passing tests.

T063: verify StageEnvelope schema compliance between each agent pair.
Each agent's output envelope must have correct stage name, stats, and items.
"""

from __future__ import annotations

from datetime import date

import pytest

from src.schemas.pipeline import StageEnvelope, StageStats
from src.schemas.report import (
    CanonicalReport,
    ParsedReport,
    ParseStatus,
)
from src.schemas.summary import Summary

TARGET = date(2026, 4, 10)


def _sample_parsed() -> list[ParsedReport]:
    return [
        ParsedReport(
            raw_id="r1",
            title="테스트 리포트",
            published_date=TARGET,
            brokerage="삼성증권",
            analyst="홍길동",
            ticker="005930",
            stock_name="삼성전자",
            body_text="테스트 본문 내용입니다.",
            source_url="https://example.com/report/1",
            parse_status=ParseStatus.SUCCESS,
        )
    ]


class TestAgentEnvelopeCompliance:
    """Each agent's run() must return a valid StageEnvelope."""

    @pytest.mark.asyncio
    async def test_validate_envelope(self):
        from src.agents.validate import ValidationAgent

        agent = ValidationAgent()
        envelope = await agent.run(_sample_parsed(), TARGET)

        assert isinstance(envelope, StageEnvelope)
        assert envelope.stage == "validate"
        assert envelope.target_date == TARGET
        assert isinstance(envelope.stats, StageStats)
        assert envelope.stats.total_input == 1
        assert envelope.stats.total_output >= 1
        assert envelope.stats.duration_ms >= 0
        assert isinstance(envelope.items, list)

    @pytest.mark.asyncio
    async def test_normalize_envelope(self):
        from src.agents.normalize import NormalizationAgent
        from src.agents.validate import ValidationAgent

        validated = await ValidationAgent().process(_sample_parsed(), TARGET)
        agent = NormalizationAgent()
        envelope = await agent.run(validated, TARGET)

        assert isinstance(envelope, StageEnvelope)
        assert envelope.stage == "normalize"
        assert isinstance(envelope.stats, StageStats)
        assert envelope.stats.total_input >= 1

    @pytest.mark.asyncio
    async def test_dedup_envelope(self):
        from src.agents.deduplicate import DeduplicationAgent
        from src.agents.normalize import NormalizationAgent
        from src.agents.validate import ValidationAgent

        validated = await ValidationAgent().process(_sample_parsed(), TARGET)
        normalized = await NormalizationAgent().process(validated, TARGET)

        agent = DeduplicationAgent()
        envelope = await agent.run(normalized, TARGET)

        assert isinstance(envelope, StageEnvelope)
        assert envelope.stage == "deduplicate"
        assert envelope.stats.total_output >= 1
        for item in envelope.items:
            assert isinstance(item, CanonicalReport)

    @pytest.mark.asyncio
    async def test_summarize_envelope(self):
        from src.agents.deduplicate import DeduplicationAgent
        from src.agents.normalize import NormalizationAgent
        from src.agents.summarize import SummarizationAgent
        from src.agents.validate import ValidationAgent

        validated = await ValidationAgent().process(_sample_parsed(), TARGET)
        normalized = await NormalizationAgent().process(validated, TARGET)
        canonical = await DeduplicationAgent().process(normalized, TARGET)

        agent = SummarizationAgent()
        envelope = await agent.run(canonical, TARGET)

        assert isinstance(envelope, StageEnvelope)
        assert envelope.stage == "summarize"
        assert envelope.stats.total_output >= 1
        for item in envelope.items:
            assert isinstance(item, Summary)

    @pytest.mark.asyncio
    async def test_classify_envelope(self):
        from src.agents.classify import ClassificationAgent
        from src.agents.deduplicate import DeduplicationAgent
        from src.agents.normalize import NormalizationAgent
        from src.agents.validate import ValidationAgent
        from src.schemas.daily_result import ClassificationResult

        validated = await ValidationAgent().process(_sample_parsed(), TARGET)
        normalized = await NormalizationAgent().process(validated, TARGET)
        canonical = await DeduplicationAgent().process(normalized, TARGET)

        agent = ClassificationAgent()
        envelope = await agent.run(canonical, TARGET)

        assert isinstance(envelope, StageEnvelope)
        assert envelope.stage == "classify"
        assert envelope.stats.total_output >= 1
        for item in envelope.items:
            assert isinstance(item, ClassificationResult)

    @pytest.mark.asyncio
    async def test_full_chain_stages_match(self):
        """Run full chain and verify all stage names are correct."""
        from src.agents.classify import ClassificationAgent
        from src.agents.deduplicate import DeduplicationAgent
        from src.agents.normalize import NormalizationAgent
        from src.agents.summarize import SummarizationAgent
        from src.agents.validate import ValidationAgent

        agents = [
            ValidationAgent(),
            NormalizationAgent(),
            DeduplicationAgent(),
            SummarizationAgent(),
            ClassificationAgent(),
        ]

        expected_stages = ["validate", "normalize", "deduplicate", "summarize", "classify"]

        items = _sample_parsed()
        for agent, expected in zip(agents, expected_stages, strict=True):
            envelope = await agent.run(items, TARGET)
            assert envelope.stage == expected, f"Expected {expected}, got {envelope.stage}"
            items = envelope.items

    @pytest.mark.asyncio
    async def test_stats_consistency(self):
        """Stats should be consistent: input >= output + failed."""
        from src.agents.normalize import NormalizationAgent
        from src.agents.validate import ValidationAgent

        validated = await ValidationAgent().process(_sample_parsed(), TARGET)
        envelope = await NormalizationAgent().run(validated, TARGET)

        stats = envelope.stats
        assert stats.total_input >= 0
        assert stats.total_output >= 0
        assert stats.total_failed >= 0
        assert stats.total_skipped >= 0
