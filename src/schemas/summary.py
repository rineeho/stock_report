"""Summary schema with extracted/generated separation per data-model.md."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


def _uuid() -> str:
    return str(uuid.uuid4())


class ExtractedInfo(BaseModel):
    """원문에서 직접 추출한 정보. 없으면 null."""

    target_price: float | None = None
    previous_target_price: float | None = None
    target_price_change: str | None = None  # "상향" / "하향" / "유지" / null
    rating: str | None = None
    earnings: str | None = None
    analyst: str | None = None
    sector: str | None = None


class GeneratedSummary(BaseModel):
    """LLM이 생성한 요약."""

    key_points: list[str] = Field(min_length=1, max_length=5)
    one_line: str = Field(min_length=1)
    opinion_summary: str | None = None


class Summary(BaseModel):
    """리포트 요약. extracted(원문 추출)와 generated(생성 요약) 분리."""

    summary_id: str = Field(default_factory=_uuid)
    canonical_id: str
    extracted: ExtractedInfo
    generated: GeneratedSummary
