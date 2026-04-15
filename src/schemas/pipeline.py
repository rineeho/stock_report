"""Pipeline log and stage result schemas per data-model.md and pipeline-stages.json."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


def _uuid() -> str:
    return str(uuid.uuid4())


class StageName(StrEnum):
    DISCOVER = "discover"
    FETCH = "fetch"
    PARSE = "parse"
    VALIDATE = "validate"
    NORMALIZE = "normalize"
    DEDUPLICATE = "deduplicate"
    SUMMARIZE = "summarize"
    CLASSIFY = "classify"
    AGGREGATE = "aggregate"
    OUTPUT = "output"


class LogStatus(StrEnum):
    STARTED = "started"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class StageStats(BaseModel):
    """Stage execution statistics per pipeline-stages.json contract."""

    total_input: int = 0
    total_output: int = 0
    total_failed: int = 0
    total_skipped: int = 0
    duration_ms: int = 0


class StageError(BaseModel):
    """Stage-level error record."""

    item_id: str
    error_type: str
    message: str


class StageEnvelope(BaseModel):
    """Stage output envelope per pipeline-stages.json contract."""

    stage: str
    target_date: date
    timestamp: datetime
    items: list[Any] = Field(default_factory=list)
    stats: StageStats = Field(default_factory=StageStats)
    errors: list[StageError] = Field(default_factory=list)


class PipelineLog(BaseModel):
    """파이프라인 실행 로그 엔트리."""

    log_id: str = Field(default_factory=_uuid)
    timestamp: datetime
    stage: StageName
    input_id: str | None = None
    output_id: str | None = None
    status: LogStatus
    error_type: str | None = None
    error_message: str | None = None
    duration_ms: int | None = None
    metadata: dict[str, Any] | None = None
