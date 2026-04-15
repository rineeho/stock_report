# Data Model: Daily Stock Report Agent System

**Date**: 2026-04-10
**Branch**: `001-daily-report-agent`

## Entity Relationship Overview

```text
Site 1───* RawReport 1───1 ParsedReport 1───1 ValidatedReport
                                                     │
                                                     1
                                                     │
                                              NormalizedReport
                                                     │
                                                     *
                                                     │
                                            DeduplicationGroup
                                                     │
                                                     1
                                                     │
                                             CanonicalReport 1───1 Summary
                                                     │
                                                     *
                                                     │
                                              Classification
                                                     │
                                                     *
                                                     │
                                               DailyResult
```

## Entities

### Site

수집 대상 사이트 설정. allowlist에 등록된 사이트만 수집 대상이 된다.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| site_id | string | YES | 고유 식별자 (예: "hankyung", "naver_research") |
| name | string | YES | 표시명 (예: "한국경제 리서치") |
| base_url | string | YES | 사이트 기본 URL |
| parser_type | string | YES | 사용할 파서 식별자 |
| rate_limit_rps | float | YES | 초당 요청 수 제한 (기본: 1.0) |
| auth_type | string | NO | 인증 방식 (none, cookie, api_key) |
| auth_config | object | NO | 인증 세부 설정 |
| enabled | boolean | YES | 활성 상태 (기본: true) |
| robots_txt_url | string | YES | robots.txt URL (자동 생성) |

**Validation rules**:
- rate_limit_rps MUST be > 0 and <= 10
- parser_type MUST match a registered parser in the registry
- enabled=false인 사이트는 수집에서 제외

### RawReport

수집 단계에서 발견된 원시 리포트 항목. 아직 파싱/검증되지 않은 상태.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| raw_id | string (UUID) | YES | 고유 식별자 |
| site_id | string | YES | 출처 사이트 ID |
| discovered_url | string | YES | 발견된 URL |
| content_type | enum | YES | html, pdf, unknown |
| raw_content | bytes/string | NO | 다운로드된 원본 콘텐츠 |
| fetch_status | enum | YES | success, failed, skipped |
| fetch_error | string | NO | 실패 시 에러 메시지 |
| fetched_at | datetime (tz) | YES | 다운로드 시각 (KST) |

### ParsedReport

파싱 단계에서 추출된 메타데이터를 포함하는 리포트.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| parsed_id | string (UUID) | YES | 고유 식별자 |
| raw_id | string | YES | 원본 RawReport 참조 |
| title | string | NO | 추출된 제목 |
| published_date | date | NO | 추출된 발행일 |
| published_date_source | enum | NO | meta_tag, json_ld, body_pattern, filename |
| brokerage | string | NO | 추출된 증권사명 (원본 형태) |
| analyst | string | NO | 추출된 애널리스트명 |
| ticker | string | NO | 추출된 종목 코드 |
| stock_name | string | NO | 추출된 종목명 |
| sector | string | NO | 추출된 산업/섹터 |
| body_text | string | NO | 본문 텍스트 (요약용) |
| parse_status | enum | YES | success, partial, failed |
| parse_errors | list[string] | NO | 파싱 중 발생한 경고/에러 |

**Validation rules**:
- parse_status=success이면 title, published_date, brokerage는 NOT NULL이어야 한다
- published_date는 합리적 범위 내여야 한다 (최근 30일 이내)

### ValidatedReport

날짜 검증을 통과한 리포트.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| validated_id | string (UUID) | YES | 고유 식별자 |
| parsed_id | string | YES | 원본 ParsedReport 참조 |
| target_date | date | YES | 검증 기준 날짜 |
| date_match | boolean | YES | target_date와 일치 여부 |
| validation_status | enum | YES | verified, unverified, rejected |
| rejection_reason | string | NO | 거부 사유 |

**State transitions**:
- published_date == target_date → `verified`
- published_date is NULL → `unverified`
- published_date != target_date → `rejected`

### NormalizedReport

정규화된 리포트. 필드 값이 표준화된 형태.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| normalized_id | string (UUID) | YES | 고유 식별자 |
| validated_id | string | YES | 원본 ValidatedReport 참조 |
| title | string | YES | 정규화된 제목 |
| published_date | date | YES | ISO 8601, KST |
| brokerage | string | YES | 정규화된 증권사명 |
| analyst | string | YES | 정규화된 애널리스트명 |
| ticker | string | NO | 표준화된 종목 코드 |
| stock_name | string | NO | 표준화된 종목명 |
| sector | string | NO | 표준화된 산업/섹터 |
| source_url | string | YES | 원본 URL |
| body_text | string | NO | 본문 텍스트 |

**Validation rules**:
- 필수 5필드(title, published_date, brokerage, analyst, source_url) 모두 NOT NULL
  → 누락 시 최종 결과에서 제외 (Constitution I)

### DeduplicationGroup

중복 판별 결과. 동일 리포트를 그룹으로 묶음.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| group_id | string (UUID) | YES | 중복 그룹 식별자 |
| canonical_id | string | YES | 대표 레코드의 normalized_id |
| member_ids | list[string] | YES | 그룹 내 모든 normalized_id |
| match_type | enum | YES | url_exact, metadata_match, content_similar |
| is_revision | boolean | YES | 수정본 여부 |
| revision_order | list[string] | NO | 수정본 순서 (최신이 마지막) |

### CanonicalReport

중복 제거 후 최종 대표 리포트.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| canonical_id | string (UUID) | YES | 고유 식별자 |
| title | string | YES | 정규화된 제목 |
| published_date | date | YES | 발행일 (KST) |
| brokerage | string | YES | 증권사명 |
| analyst | string | YES | 애널리스트명 |
| ticker | string | NO | 종목 코드 |
| stock_name | string | NO | 종목명 |
| sector | string | NO | 산업/섹터 |
| source_urls | list[string] | YES | 모든 출처 URL (중복 포함) |
| primary_url | string | YES | 대표 URL |
| body_text | string | NO | 본문 텍스트 |
| has_revision | boolean | YES | 수정본 존재 여부 |
| duplicate_count | integer | YES | 발견된 중복 수 |

### Summary

리포트 요약. extracted(원문 추출)와 generated(생성 요약)를 분리.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| summary_id | string (UUID) | YES | 고유 식별자 |
| canonical_id | string | YES | 대상 CanonicalReport 참조 |
| extracted | object | YES | 원문 직접 추출 정보 |
| extracted.target_price | number/null | YES | 목표주가 (없으면 null) |
| extracted.rating | string/null | YES | 투자 의견 (없으면 null) |
| extracted.earnings | string/null | YES | 실적 정보 (없으면 null) |
| generated | object | YES | LLM 생성 요약 |
| generated.key_points | list[string] | YES | 핵심 포인트 (3~5개) |
| generated.one_line | string | YES | 한 줄 요약 |
| generated.opinion_summary | string | NO | 투자 의견 요약 |

**Validation rules**:
- extracted 필드는 원문에 없으면 반드시 null (Constitution VI)
- generated 필드에 수치 정보가 포함되면 환각 검출 대상

### Classification

리포트 분류 정보.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| canonical_id | string | YES | 대상 CanonicalReport 참조 |
| by_brokerage | string | YES | 증권사 기준 그룹명 |
| by_ticker | string | NO | 종목 기준 그룹명 |
| by_sector | string | NO | 산업 기준 그룹명 |
| by_analyst | string | YES | 애널리스트 기준 그룹명 |

### DailyResult

하루 전체 처리 결과.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| result_id | string (UUID) | YES | 고유 식별자 |
| target_date | date | YES | 대상 날짜 |
| total_discovered | integer | YES | 발견된 리포트 수 |
| total_fetched | integer | YES | 다운로드 성공 수 |
| total_validated | integer | YES | 날짜 검증 통과 수 |
| total_unverified | integer | YES | 검증 불가 수 |
| total_deduplicated | integer | YES | 중복 제거 후 최종 수 |
| reports | list[CanonicalReport] | YES | 최종 리포트 목록 |
| summaries | list[Summary] | YES | 요약 목록 |
| classifications | object | YES | 분류 결과 |
| pipeline_stats | object | YES | 파이프라인 실행 통계 |
| created_at | datetime (tz) | YES | 결과 생성 시각 (KST) |

### PipelineLog

파이프라인 실행 로그 엔트리.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| log_id | string (UUID) | YES | 고유 식별자 |
| timestamp | datetime (tz) | YES | 로그 시각 (KST) |
| stage | enum | YES | discover, fetch, parse, validate, normalize, deduplicate, summarize, classify, aggregate, output |
| input_id | string | NO | 입력 항목 ID |
| output_id | string | NO | 출력 항목 ID |
| status | enum | YES | started, success, failed, skipped |
| error_type | string | NO | 에러 타입 |
| error_message | string | NO | 에러 메시지 |
| duration_ms | integer | NO | 처리 소요 시간 (ms) |
| metadata | object | NO | 추가 컨텍스트 정보 |
