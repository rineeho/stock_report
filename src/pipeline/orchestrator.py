"""Pipeline orchestrator: sequential agent execution with checkpoint support."""

from __future__ import annotations

from datetime import date
from typing import Any

import structlog

from src.agents.base import BaseAgent
from src.pipeline.checkpoint import CheckpointManager
from src.schemas.daily_result import PipelineStats
from src.schemas.pipeline import StageEnvelope

logger = structlog.get_logger()

# Mapping from stage name to PipelineStats field
_STAGE_STAT_FIELD: dict[str, str] = {
    "discover": "total_discovered",
    "fetch": "total_fetched",
    "parse": "total_parsed",
    "validate": "total_validated",
    "normalize": "total_normalized",
    "deduplicate": "total_deduplicated",
    "summarize": "total_summarized",
    "classify": "total_classified",
}


class PipelineOrchestrator:
    """Orchestrates sequential execution of pipeline agents."""

    def __init__(
        self,
        agents: list[BaseAgent],
        checkpoint_manager: CheckpointManager,
        from_stage: str | None = None,
    ) -> None:
        self.agents = agents
        self.checkpoint = checkpoint_manager
        self.from_stage = from_stage
        self.envelopes: list[StageEnvelope] = []

    def _build_pipeline_stats(self) -> PipelineStats:
        """Build PipelineStats from collected stage envelopes."""
        stats_data: dict[str, Any] = {}
        total_duration = 0
        for env in self.envelopes:
            field = _STAGE_STAT_FIELD.get(env.stage)
            if field:
                stats_data[field] = env.stats.total_output
            total_duration += env.stats.duration_ms
        stats_data["duration_ms"] = total_duration
        return PipelineStats(**stats_data)

    async def run(self, target_date: date, **kwargs: Any) -> list[StageEnvelope]:
        """Run all agents sequentially.

        If from_stage is set, loads checkpoint data for stages before it
        and starts execution from that stage.

        Collects intermediate results (canonical reports, summaries, pipeline
        stats) and passes them to the aggregate stage via kwargs.
        """
        items: list[Any] = []
        skip = self.from_stage is not None
        # Collect intermediate stage outputs for the aggregate stage
        stage_outputs: dict[str, list[Any]] = {}

        for agent in self.agents:
            stage = agent.stage_name

            if skip:
                if stage == self.from_stage:
                    skip = False
                    # items already holds the previous stage's cached output
                    logger.info("stage_resuming", stage=stage, input_count=len(items))
                else:
                    # Load this stage's cached output and continue
                    cached = self.checkpoint.load(target_date, stage)
                    if cached is not None:
                        items = cached
                        stage_outputs[stage] = list(cached)
                        logger.info("checkpoint_skipped", stage=stage, item_count=len(items))
                    continue

            # Inject collected data for aggregate stage
            run_kwargs = dict(kwargs)
            if stage == "aggregate":
                run_kwargs["canonical_reports"] = stage_outputs.get("deduplicate", [])
                run_kwargs["summaries"] = stage_outputs.get("summarize", [])
                run_kwargs["pipeline_stats"] = self._build_pipeline_stats()

            envelope = await agent.run(items, target_date, **run_kwargs)
            self.envelopes.append(envelope)

            # Save checkpoint
            self.checkpoint.save(target_date, stage, envelope)

            # Track intermediate outputs
            stage_outputs[stage] = list(envelope.items)

            # Use output as next stage's input
            items = envelope.items

            if envelope.stats.total_output == 0 and envelope.stats.total_failed > 0:
                logger.warning("stage_produced_no_output", stage=stage)

        return self.envelopes
