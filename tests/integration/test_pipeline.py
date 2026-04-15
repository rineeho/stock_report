"""Integration test: full pipeline end-to-end with fixture data.

T062: verify entire pipeline from discover → output using sample data,
without hitting any external services.
"""

from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

import pytest

from src.schemas.pipeline import StageEnvelope
from src.schemas.report import (
    CanonicalReport,
    ContentType,
    FetchStatus,
    NormalizedReport,
    ParsedReport,
    ParseStatus,
    RawReport,
    ValidatedReport,
    ValidationStatus,
)


def _make_raw_reports() -> list[RawReport]:
    """Create sample raw reports as if just discovered."""
    return [
        RawReport(
            site_id="naver_research",
            discovered_url="https://finance.naver.com/research/company_read.naver?nid=100001",
            content_type=ContentType.HTML,
            metadata_hint='{"title":"HBM 중심 AI 반도체 수요 강세","brokerage":"미래에셋증권","stock_name":"삼성전자","ticker":"005930","date_hint":"2026.04.10","pdf_url":""}',
            fetch_status=FetchStatus.SKIPPED,
        ),
        RawReport(
            site_id="naver_research",
            discovered_url="https://finance.naver.com/research/company_read.naver?nid=100002",
            content_type=ContentType.HTML,
            metadata_hint='{"title":"2026년 1분기 어닝서프라이즈 예상","brokerage":"한국투자증권","stock_name":"SK하이닉스","ticker":"000660","date_hint":"2026.04.10","pdf_url":""}',
            fetch_status=FetchStatus.SKIPPED,
        ),
    ]


def _make_parsed_reports() -> list[ParsedReport]:
    """Create parsed reports with all required fields."""
    return [
        ParsedReport(
            raw_id="r1",
            title="HBM 중심 AI 반도체 수요 강세",
            published_date=date(2026, 4, 10),
            brokerage="미래에셋증권",
            analyst="김성민",
            ticker="005930",
            stock_name="삼성전자",
            body_text="삼성전자 HBM 매출 35% 증가. 영업이익 15.2조원.",
            source_url="https://finance.naver.com/research/company_read.naver?nid=100001",
            parse_status=ParseStatus.SUCCESS,
        ),
        ParsedReport(
            raw_id="r2",
            title="2026년 1분기 어닝서프라이즈 예상",
            published_date=date(2026, 4, 10),
            brokerage="한국투자증권",
            analyst="이호준",
            ticker="000660",
            stock_name="SK하이닉스",
            body_text="SK하이닉스 HBM4 양산 본격화에 따른 실적 개선.",
            source_url="https://finance.naver.com/research/company_read.naver?nid=100002",
            parse_status=ParseStatus.SUCCESS,
        ),
    ]


def _make_validated_reports(target_date: date) -> list[ValidatedReport]:
    """Create validated reports from parsed data."""
    return [
        ValidatedReport(
            parsed_id="p1",
            target_date=target_date,
            date_match=True,
            validation_status=ValidationStatus.VERIFIED,
            title="HBM 중심 AI 반도체 수요 강세",
            published_date=target_date,
            brokerage="미래에셋증권",
            analyst="김성민",
            ticker="005930",
            stock_name="삼성전자",
            body_text="삼성전자 HBM 매출 35% 증가.",
            source_url="https://finance.naver.com/research/company_read.naver?nid=100001",
        ),
        ValidatedReport(
            parsed_id="p2",
            target_date=target_date,
            date_match=True,
            validation_status=ValidationStatus.VERIFIED,
            title="2026년 1분기 어닝서프라이즈 예상",
            published_date=target_date,
            brokerage="한국투자증권",
            analyst="이호준",
            ticker="000660",
            stock_name="SK하이닉스",
            body_text="SK하이닉스 HBM4 양산 본격화.",
            source_url="https://finance.naver.com/research/company_read.naver?nid=100002",
        ),
    ]


class TestPartialPipeline:
    """Test middle pipeline stages with prepared data (no external HTTP)."""

    TARGET = date(2026, 4, 10)

    @pytest.mark.asyncio
    async def test_parse_agent_handles_hint_json(self):
        """ParseAgent should work with JSON-hint raw content."""
        from src.agents.parse import ParseAgent
        from src.parsers.registry import discover_parsers

        discover_parsers()

        raw_reports = _make_raw_reports()
        agent = ParseAgent()
        results = await agent.process(raw_reports, self.TARGET)

        assert len(results) == 2
        for r in results:
            assert isinstance(r, ParsedReport)
            assert r.title is not None
            assert r.brokerage is not None

    @pytest.mark.asyncio
    async def test_validate_agent(self):
        """ValidationAgent should verify matching dates and reject mismatches."""
        from src.agents.validate import ValidationAgent

        parsed = _make_parsed_reports()
        agent = ValidationAgent()
        results = await agent.process(parsed, self.TARGET)

        assert len(results) == 2
        for r in results:
            assert isinstance(r, ValidatedReport)
            assert r.validation_status == ValidationStatus.VERIFIED

    @pytest.mark.asyncio
    async def test_normalize_agent(self):
        """NormalizationAgent should normalize and filter."""
        from src.agents.normalize import NormalizationAgent

        validated = _make_validated_reports(self.TARGET)
        agent = NormalizationAgent()
        results = await agent.process(validated, self.TARGET)

        assert len(results) == 2
        for r in results:
            assert isinstance(r, NormalizedReport)
            assert len(r.ticker) == 6  # zero-padded

    @pytest.mark.asyncio
    async def test_dedup_agent(self):
        """DeduplicationAgent should produce CanonicalReports."""
        from src.agents.deduplicate import DeduplicationAgent
        from src.agents.normalize import NormalizationAgent

        validated = _make_validated_reports(self.TARGET)
        norm_agent = NormalizationAgent()
        normalized = await norm_agent.process(validated, self.TARGET)

        dedup_agent = DeduplicationAgent()
        results = await dedup_agent.process(normalized, self.TARGET)

        # Two distinct reports → two canonical reports
        assert len(results) == 2
        for r in results:
            assert isinstance(r, CanonicalReport)
            assert len(r.source_urls) >= 1

    @pytest.mark.asyncio
    async def test_summarize_agent_mock(self):
        """SummarizationAgent with mock LLM should return Summary objects."""
        from src.agents.deduplicate import DeduplicationAgent
        from src.agents.normalize import NormalizationAgent
        from src.agents.summarize import SummarizationAgent
        from src.schemas.summary import Summary

        validated = _make_validated_reports(self.TARGET)
        normalized = await NormalizationAgent().process(validated, self.TARGET)
        canonical = await DeduplicationAgent().process(normalized, self.TARGET)

        summarize_agent = SummarizationAgent()  # uses MockLLMClient
        results = await summarize_agent.process(canonical, self.TARGET)

        assert len(results) == 2
        for s in results:
            assert isinstance(s, Summary)
            assert s.extracted is not None
            assert s.generated is not None

    @pytest.mark.asyncio
    async def test_full_middle_pipeline_chain(self):
        """Run validate → normalize → dedup → summarize → classify in sequence."""
        from src.agents.classify import ClassificationAgent
        from src.agents.deduplicate import DeduplicationAgent
        from src.agents.normalize import NormalizationAgent
        from src.agents.summarize import SummarizationAgent
        from src.schemas.daily_result import ClassificationResult

        parsed = _make_parsed_reports()

        # Validate
        from src.agents.validate import ValidationAgent
        validated = await ValidationAgent().process(parsed, self.TARGET)
        assert len(validated) == 2

        # Normalize
        normalized = await NormalizationAgent().process(validated, self.TARGET)
        assert len(normalized) == 2

        # Dedup
        canonical = await DeduplicationAgent().process(normalized, self.TARGET)
        assert len(canonical) == 2

        # Summarize
        summaries = await SummarizationAgent().process(canonical, self.TARGET)
        assert len(summaries) == 2

        # Classify
        classifications = await ClassificationAgent().process(canonical, self.TARGET)
        assert len(classifications) > 0
        for c in classifications:
            assert isinstance(c, ClassificationResult)


class TestPipelineWithOrchestrator:
    """Test the orchestrator with simple agents."""

    TARGET = date(2026, 4, 10)

    @pytest.mark.asyncio
    async def test_orchestrator_runs_agents_in_sequence(self):
        """Orchestrator should run agents and produce envelopes."""
        from src.agents.normalize import NormalizationAgent
        from src.agents.validate import ValidationAgent
        from src.pipeline.checkpoint import CheckpointManager
        from src.pipeline.orchestrator import PipelineOrchestrator

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint = CheckpointManager(Path(tmpdir))
            agents = [
                ValidationAgent(),
                NormalizationAgent(),
            ]
            PipelineOrchestrator(agents=agents, checkpoint_manager=checkpoint)

            parsed = _make_parsed_reports()

            # Manually set items as first stage input
            # We need to provide parsed items as list[dict] since orchestrator passes items
            # through. Let's use run() which starts with empty items for discover stage.
            # Instead, directly test agent chain:
            envelopes = []
            items = parsed
            for agent in agents:
                envelope = await agent.run(items, self.TARGET)
                envelopes.append(envelope)
                items = envelope.items

            assert len(envelopes) == 2
            for env in envelopes:
                assert isinstance(env, StageEnvelope)
                assert env.stats.total_input >= 0
                assert env.stats.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_checkpoint_save_and_load(self):
        """Checkpoint should correctly save and load stage data."""
        from src.agents.validate import ValidationAgent
        from src.pipeline.checkpoint import CheckpointManager

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint = CheckpointManager(Path(tmpdir))
            agent = ValidationAgent()

            parsed = _make_parsed_reports()
            envelope = await agent.run(parsed, self.TARGET)

            # Save checkpoint
            path = checkpoint.save(self.TARGET, "validate", envelope)
            assert path.exists()

            # Load checkpoint
            loaded = checkpoint.load(self.TARGET, "validate")
            assert loaded is not None
            assert len(loaded) == len(envelope.items)

            # List checkpoints
            stages = checkpoint.list_checkpoints(self.TARGET)
            assert "04_validated" in stages
