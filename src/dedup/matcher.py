"""Deduplication matcher: 3-stage dedup with revision detection per R7.

Stage 1: URL fingerprint (exact URL match)
Stage 2: Metadata match (title + brokerage + date + ticker)
Stage 3: Content similarity / Revision detection (title similarity with same brokerage+ticker)
"""

from __future__ import annotations

import re
import uuid
from collections import defaultdict

import structlog

from src.schemas.report import DeduplicationGroup, MatchType, NormalizedReport

logger = structlog.get_logger()

# Revision indicators in title
_REVISION_PATTERNS = [
    r"\(수정\)",
    r"\(정정\)",
    r"\(업데이트\)",
    r"\(revised\)",
    r"\(updated\)",
    r"_v\d+",
]


def _normalize_title(title: str) -> str:
    """Strip revision markers and whitespace for comparison."""
    t = title.strip()
    for pat in _REVISION_PATTERNS:
        t = re.sub(pat, "", t, flags=re.IGNORECASE)
    return t.strip()


def _is_revision_variant(title_a: str, title_b: str) -> bool:
    """Check if two titles differ only by revision markers."""
    norm_a = _normalize_title(title_a)
    norm_b = _normalize_title(title_b)
    return norm_a == norm_b and title_a != title_b


def _metadata_key(r: NormalizedReport) -> str:
    """Build a dedup key from title + brokerage + date + ticker."""
    return f"{r.title}|{r.brokerage}|{r.published_date}|{r.ticker or ''}"


def _base_key(r: NormalizedReport) -> str:
    """Build a base key ignoring title variations (for revision detection)."""
    return f"{_normalize_title(r.title)}|{r.brokerage}|{r.published_date}|{r.ticker or ''}"


def _cross_site_key(r: NormalizedReport) -> str:
    """Build a dedup key from brokerage + date + ticker (title excluded)."""
    return f"{r.brokerage}|{r.published_date}|{r.ticker or ''}"


def _fuzzy_title_match(a: str, b: str) -> bool:
    """Fuzzy title comparison to handle Naver's truncation (..) pattern."""
    if a == b:
        return True
    shorter, longer = sorted([a, b], key=len)
    # 수정본(revision) 차이는 여기서 잡지 않음 — Stage 3에서 처리
    if _is_revision_variant(a, b):
        return False
    # 네이버 잘림 패턴: "제목.." 또는 "제목..."
    clean = shorter.rstrip(".").rstrip()
    return len(clean) >= 5 and longer.startswith(clean)


def find_duplicates(reports: list[NormalizedReport]) -> list[DeduplicationGroup]:
    """Find duplicate groups among normalized reports.

    3-stage deduplication:
    1. URL exact match
    2. Metadata match (title + brokerage + date + ticker)
    3. Revision detection (normalized title + brokerage + ticker)

    Args:
        reports: List of NormalizedReport to deduplicate.

    Returns:
        List of DeduplicationGroup. Each report appears in exactly one group.
    """
    if not reports:
        return []

    # Track which report IDs are already grouped
    grouped: set[str] = set()
    groups: list[DeduplicationGroup] = []

    # Stage 1: URL exact match
    url_buckets: dict[str, list[NormalizedReport]] = defaultdict(list)
    for r in reports:
        url_buckets[r.source_url].append(r)

    for _url, bucket in url_buckets.items():
        if len(bucket) > 1:
            member_ids = [r.normalized_id for r in bucket]
            groups.append(
                DeduplicationGroup(
                    group_id=str(uuid.uuid4()),
                    canonical_id=member_ids[0],
                    member_ids=member_ids,
                    match_type=MatchType.URL_EXACT,
                    is_revision=False,
                )
            )
            grouped.update(member_ids)

    remaining = [r for r in reports if r.normalized_id not in grouped]

    # Stage 2: Metadata exact match (title + brokerage + date + ticker)
    meta_buckets: dict[str, list[NormalizedReport]] = defaultdict(list)
    for r in remaining:
        meta_buckets[_metadata_key(r)].append(r)

    new_remaining = []
    for _key, bucket in meta_buckets.items():
        if len(bucket) > 1:
            member_ids = [r.normalized_id for r in bucket]
            groups.append(
                DeduplicationGroup(
                    group_id=str(uuid.uuid4()),
                    canonical_id=member_ids[0],
                    member_ids=member_ids,
                    match_type=MatchType.METADATA_MATCH,
                    is_revision=False,
                )
            )
            grouped.update(member_ids)
        else:
            new_remaining.extend(bucket)

    remaining = new_remaining

    # Stage 2.5: Cross-site matching (brokerage + date + ticker, fuzzy title)
    cross_buckets: dict[str, list[NormalizedReport]] = defaultdict(list)
    for r in remaining:
        if r.ticker:  # ticker가 None이면 스킵 (오탐 방지)
            cross_buckets[_cross_site_key(r)].append(r)

    new_remaining2 = [r for r in remaining if not r.ticker]
    for _key, bucket in cross_buckets.items():
        if len(bucket) > 1:
            # 버킷 내 퍼지 매칭으로 그룹 형성
            matched_ids: set[str] = set()
            for i, a in enumerate(bucket):
                for b in bucket[i + 1 :]:
                    if _fuzzy_title_match(a.title, b.title):
                        matched_ids.add(a.normalized_id)
                        matched_ids.add(b.normalized_id)

            if matched_ids:
                member_ids = [r.normalized_id for r in bucket if r.normalized_id in matched_ids]
                groups.append(
                    DeduplicationGroup(
                        group_id=str(uuid.uuid4()),
                        canonical_id=member_ids[0],
                        member_ids=member_ids,
                        match_type=MatchType.CROSS_SITE,
                        is_revision=False,
                    )
                )
                grouped.update(matched_ids)
                # 매칭 안 된 것만 남김
                new_remaining2.extend(r for r in bucket if r.normalized_id not in matched_ids)
            else:
                new_remaining2.extend(bucket)
        else:
            new_remaining2.extend(bucket)

    remaining = new_remaining2

    # Stage 3: Revision detection (normalized-title + brokerage + date + ticker)
    base_buckets: dict[str, list[NormalizedReport]] = defaultdict(list)
    for r in remaining:
        base_buckets[_base_key(r)].append(r)

    for _key, bucket in base_buckets.items():
        if len(bucket) > 1:
            # Check if they are revision variants
            titles = [r.title for r in bucket]
            has_revision = any(
                _is_revision_variant(a, b)
                for i, a in enumerate(titles)
                for b in titles[i + 1:]
            )

            member_ids = [r.normalized_id for r in bucket]
            groups.append(
                DeduplicationGroup(
                    group_id=str(uuid.uuid4()),
                    canonical_id=member_ids[-1],  # latest (revision) as canonical
                    member_ids=member_ids,
                    match_type=MatchType.CONTENT_SIMILAR,
                    is_revision=has_revision,
                    revision_order=member_ids if has_revision else None,
                )
            )
            grouped.update(member_ids)
        else:
            # Single item — becomes its own group
            r = bucket[0]
            groups.append(
                DeduplicationGroup(
                    group_id=str(uuid.uuid4()),
                    canonical_id=r.normalized_id,
                    member_ids=[r.normalized_id],
                    match_type=MatchType.URL_EXACT,  # default for singletons
                    is_revision=False,
                )
            )
            grouped.add(r.normalized_id)

    # Any still ungrouped (shouldn't happen, but safety)
    for r in reports:
        if r.normalized_id not in grouped:
            groups.append(
                DeduplicationGroup(
                    group_id=str(uuid.uuid4()),
                    canonical_id=r.normalized_id,
                    member_ids=[r.normalized_id],
                    match_type=MatchType.URL_EXACT,
                    is_revision=False,
                )
            )

    logger.info(
        "dedup_result",
        total_input=len(reports),
        total_groups=len(groups),
        total_revisions=sum(1 for g in groups if g.is_revision),
    )

    return groups
