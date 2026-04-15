"""DailyResult schema per data-model.md."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from src.schemas.report import CanonicalReport
from src.schemas.summary import Summary


def _uuid() -> str:
    return str(uuid.uuid4())


class ClassificationResult(BaseModel):
    """분류 결과."""

    by_brokerage: dict[str, list[str]] = Field(default_factory=dict)
    by_ticker: dict[str, list[str]] = Field(default_factory=dict)
    by_sector: dict[str, list[str]] = Field(default_factory=dict)
    by_analyst: dict[str, list[str]] = Field(default_factory=dict)


class PipelineStats(BaseModel):
    """파이프라인 실행 통계."""

    total_discovered: int = 0
    total_fetched: int = 0
    total_parsed: int = 0
    total_validated: int = 0
    total_unverified: int = 0
    total_rejected: int = 0
    total_normalized: int = 0
    total_deduplicated: int = 0
    total_summarized: int = 0
    total_classified: int = 0
    duration_ms: int = 0


class DailyResult(BaseModel):
    """하루 전체 처리 결과."""

    result_id: str = Field(default_factory=_uuid)
    target_date: date
    total_discovered: int = 0
    total_fetched: int = 0
    total_validated: int = 0
    total_unverified: int = 0
    total_deduplicated: int = 0
    reports: list[CanonicalReport] = Field(default_factory=list)
    summaries: list[Summary] = Field(default_factory=list)
    classifications: ClassificationResult = Field(default_factory=ClassificationResult)
    pipeline_stats: PipelineStats = Field(default_factory=PipelineStats)
    created_at: datetime | None = None
