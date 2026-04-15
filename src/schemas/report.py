"""Report schemas for the pipeline stages.

Defines: RawReport, ParsedReport, ValidatedReport, NormalizedReport,
DeduplicationGroup, CanonicalReport per data-model.md.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


def _uuid() -> str:
    return str(uuid.uuid4())


class ContentType(StrEnum):
    HTML = "html"
    PDF = "pdf"
    UNKNOWN = "unknown"


class FetchStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class ParseStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class ValidationStatus(StrEnum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    REJECTED = "rejected"


class DateSource(StrEnum):
    META_TAG = "meta_tag"
    JSON_LD = "json_ld"
    BODY_PATTERN = "body_pattern"
    FILENAME = "filename"


class MatchType(StrEnum):
    URL_EXACT = "url_exact"
    METADATA_MATCH = "metadata_match"
    CONTENT_SIMILAR = "content_similar"


class RawReport(BaseModel):
    """수집 단계에서 발견된 원시 리포트."""

    raw_id: str = Field(default_factory=_uuid)
    site_id: str
    discovered_url: str
    content_type: ContentType = ContentType.UNKNOWN
    raw_content: str | None = None
    metadata_hint: str | None = None  # JSON hint from discover, preserved through fetch
    fetch_status: FetchStatus = FetchStatus.SKIPPED
    fetch_error: str | None = None
    fetched_at: datetime | None = None


class ParsedReport(BaseModel):
    """파싱 단계에서 메타데이터가 추출된 리포트."""

    parsed_id: str = Field(default_factory=_uuid)
    raw_id: str
    title: str | None = None
    published_date: date | None = None
    published_date_source: DateSource | None = None
    brokerage: str | None = None
    analyst: str | None = None
    ticker: str | None = None
    stock_name: str | None = None
    sector: str | None = None
    body_text: str | None = None
    source_url: str = ""
    parse_status: ParseStatus = ParseStatus.FAILED
    parse_errors: list[str] = Field(default_factory=list)


class ValidatedReport(BaseModel):
    """날짜 검증을 통과한 리포트."""

    validated_id: str = Field(default_factory=_uuid)
    parsed_id: str
    target_date: date
    date_match: bool = False
    validation_status: ValidationStatus = ValidationStatus.UNVERIFIED
    rejection_reason: str | None = None
    # Carry forward parsed fields for downstream use
    title: str | None = None
    published_date: date | None = None
    published_date_source: DateSource | None = None
    brokerage: str | None = None
    analyst: str | None = None
    ticker: str | None = None
    stock_name: str | None = None
    sector: str | None = None
    body_text: str | None = None
    source_url: str = ""


class NormalizedReport(BaseModel):
    """정규화된 리포트. 필드 값이 표준화된 형태."""

    normalized_id: str = Field(default_factory=_uuid)
    validated_id: str
    title: str
    published_date: date
    brokerage: str
    analyst: str
    ticker: str | None = None
    stock_name: str | None = None
    sector: str | None = None
    source_url: str
    body_text: str | None = None


class DeduplicationGroup(BaseModel):
    """중복 판별 결과 그룹."""

    group_id: str = Field(default_factory=_uuid)
    canonical_id: str
    member_ids: list[str]
    match_type: MatchType
    is_revision: bool = False
    revision_order: list[str] | None = None


class CanonicalReport(BaseModel):
    """중복 제거 후 최종 대표 리포트."""

    canonical_id: str = Field(default_factory=_uuid)
    title: str
    published_date: date
    brokerage: str
    analyst: str
    ticker: str | None = None
    stock_name: str | None = None
    sector: str | None = None
    source_urls: list[str]
    primary_url: str
    body_text: str | None = None
    has_revision: bool = False
    duplicate_count: int = 1
