"""BaseAgent abstract class for pipeline agents.

Each agent: validates input → processes → validates output → logs.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any

import structlog

from src.schemas.pipeline import StageEnvelope, StageError, StageStats

logger = structlog.get_logger()


class BaseAgent(ABC):
    """Abstract base class for all pipeline agents."""

    @property
    @abstractmethod
    def stage_name(self) -> str:
        """Return the stage name for this agent (e.g., 'discover', 'fetch')."""

    @abstractmethod
    async def process(self, items: list[Any], target_date: date, **kwargs: Any) -> list[Any]:
        """Process input items and return output items.

        Args:
            items: Input items from previous stage.
            target_date: The target date for processing.
            **kwargs: Additional context.

        Returns:
            Processed output items.
        """

    async def run(self, items: list[Any], target_date: date, **kwargs: Any) -> StageEnvelope:
        """Execute the agent with logging and envelope creation.

        Args:
            items: Input items from previous stage.
            target_date: The target date for processing.
            **kwargs: Additional context.

        Returns:
            StageEnvelope with results, stats, and errors.
        """
        log = logger.bind(stage=self.stage_name, target_date=str(target_date))
        log.info("stage_started", input_count=len(items))

        start_ms = time.monotonic_ns() // 1_000_000
        errors: list[StageError] = []

        try:
            output = await self.process(items, target_date, **kwargs)
        except Exception as exc:
            log.error("stage_failed", error=str(exc))
            errors.append(StageError(item_id="*", error_type=type(exc).__name__, message=str(exc)))
            output = []

        duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms

        stats = StageStats(
            total_input=len(items),
            total_output=len(output),
            total_failed=len(errors),
            total_skipped=len(items) - len(output) - len(errors),
            duration_ms=duration_ms,
        )

        log.info(
            "stage_completed",
            output_count=len(output),
            failed_count=len(errors),
            duration_ms=duration_ms,
        )

        return StageEnvelope(
            stage=self.stage_name,
            target_date=target_date,
            timestamp=datetime.now().astimezone(),
            items=output,
            stats=stats,
            errors=errors,
        )
