# Implementation Plan: Daily Stock Report Agent System

**Branch**: `001-daily-report-agent` | **Date**: 2026-04-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-daily-report-agent/spec.md`

## Summary

여러 금융/증권사 사이트에서 매일 발행되는 주식 리포트를 자동으로 수집하고,
당일 리포트만 선별하여 정리하는 agent 기반 파이프라인 시스템을 구현한다.
10개의 독립 agent(Source Discovery → Fetch → Parse → Validate → Normalize →
Deduplicate → Summarize → Classify → Aggregate → Output)가 순차 파이프라인으로
연결되며, 각 단계의 결과는 JSON으로 저장되어 재시작 및 디버깅이 가능하다.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: httpx (HTTP client), beautifulsoup4 (HTML parsing),
pdfplumber (PDF extraction), pydantic (schema validation), structlog (logging),
openai/anthropic SDK (LLM summarization)
**Storage**: 파일 시스템 기반 JSON 저장 (각 단계별 중간 결과), SQLite (선택적 인덱싱)
**Testing**: pytest, pytest-snapshot (파서 스냅샷 테스트)
**Target Platform**: Linux/macOS/Windows (단일 머신, CLI 실행)
**Project Type**: CLI tool + library (agent pipeline)
**Performance Goals**: 3~5개 사이트에서 일일 리포트 100건 이내 처리, 전체 파이프라인 10분 이내 완료
**Constraints**: rate limit 준수 (사이트별 1 req/sec 기본), LLM API 비용 최소화
**Scale/Scope**: 초기 3~5개 사이트, 일일 리포트 50~100건, 단일 사용자

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I | Data Accuracy First | PASS | FR-004~007: 날짜 검증 + 필수 필드 체크 구현 예정 |
| II | Source Traceability | PASS | FR-017: 각 단계 구조화된 로그, source_url 유지 |
| III | Collection Ethics | PASS | FR-002, FR-015~016: allowlist + robots.txt + rate limit |
| IV | Daily Determinism | PASS | FR-001, FR-020~021: target_date + Asia/Seoul + 결정적 처리 |
| V | Deduplication & Normalization | PASS | FR-008~009, FR-022: canonical 통합 + 정규화 |
| VI | Summary Quality & Anti-Hallucination | PASS | FR-010~012: extracted/generated 분리, 환각 방지 |
| VII | Agent Role Separation | PASS | 10개 agent 독립 설계, JSON Schema 기반 통신 |
| VIII | Testability | PASS | pytest-snapshot 기반 파서 테스트, 파라미터화 테스트 |
| IX | Operational Stability | PASS | FR-018~019: checkpoint 재시작, 실패 격리 |
| X | Output Practicality | PASS | FR-014: Markdown + JSON 이중 출력 |

**Gate Result**: ALL PASS — Phase 0 진행 가능

## Project Structure

### Documentation (this feature)

```text
specs/001-daily-report-agent/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── report-schema.json
│   ├── pipeline-stages.json
│   └── cli-interface.md
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── __init__.py
├── main.py                    # CLI 진입점 + 파이프라인 오케스트레이터
├── config/
│   ├── __init__.py
│   ├── settings.py            # 전역 설정 (timezone, paths, LLM config)
│   └── sites.yaml             # 사이트 allowlist 설정
├── schemas/
│   ├── __init__.py
│   ├── report.py              # Report, RawReport, ValidatedReport 등
│   ├── summary.py             # Summary (extracted + generated)
│   ├── daily_result.py        # DailyResult
│   └── pipeline.py            # PipelineLog, StageResult
├── agents/
│   ├── __init__.py
│   ├── base.py                # BaseAgent 추상 클래스
│   ├── source_discovery.py    # SourceDiscoveryAgent
│   ├── fetch.py               # FetchAgent
│   ├── parse.py               # ParseAgent
│   ├── validate.py            # ValidationAgent
│   ├── normalize.py           # NormalizationAgent
│   ├── deduplicate.py         # DeduplicationAgent
│   ├── summarize.py           # SummarizationAgent
│   ├── classify.py            # ClassificationAgent
│   ├── aggregate.py           # AggregationAgent
│   └── output.py              # OutputAgent
├── parsers/
│   ├── __init__.py
│   ├── base.py                # BaseSiteParser 추상 클래스
│   ├── registry.py            # 파서 레지스트리 (사이트명 → 파서 매핑)
│   └── sites/                 # 사이트별 파서 구현
│       ├── __init__.py
│       └── example_site.py    # 예시 사이트 파서
├── normalizers/
│   ├── __init__.py
│   ├── brokerage.py           # 증권사명 정규화 매핑
│   ├── ticker.py              # 종목 코드/명 표준화
│   └── date.py                # 날짜 형식 통일
├── dedup/
│   ├── __init__.py
│   └── matcher.py             # 중복 판별 로직 (유사도, fingerprint)
├── summarizer/
│   ├── __init__.py
│   ├── llm_client.py          # LLM API 추상화 계층
│   └── prompt_templates.py    # 요약 프롬프트 템플릿
├── output/
│   ├── __init__.py
│   ├── markdown.py            # Markdown 결과 생성기
│   └── json_output.py         # JSON 결과 생성기
├── pipeline/
│   ├── __init__.py
│   ├── orchestrator.py        # 파이프라인 실행 + checkpoint 관리
│   ├── checkpoint.py          # 중간 결과 저장/로드
│   └── logger.py              # 구조화된 파이프라인 로그
└── utils/
    ├── __init__.py
    ├── http.py                # rate-limited HTTP 클라이언트
    ├── robots.py              # robots.txt 파서/체커
    └── timezone.py            # Asia/Seoul 날짜 유틸리티

tests/
├── conftest.py
├── fixtures/                  # 샘플 HTML/PDF 파일
│   └── sites/
│       └── example_site/
│           ├── sample_list_page.html
│           └── sample_report.pdf
├── unit/
│   ├── test_date_extraction.py
│   ├── test_normalization.py
│   ├── test_deduplication.py
│   └── test_classification.py
├── snapshot/
│   └── test_parsers.py        # 파서 스냅샷 테스트
├── integration/
│   ├── test_pipeline.py       # 전체 파이프라인 통합 테스트
│   └── test_agent_chain.py    # agent 간 데이터 전달 테스트
└── hallucination/
    └── test_summary_accuracy.py  # 환각 검출 테스트

data/
├── cache/                     # 단계별 중간 결과 캐시
│   └── {target_date}/
│       ├── 01_discovered.json
│       ├── 02_fetched.json
│       ├── 03_parsed.json
│       ├── 04_validated.json
│       ├── 05_normalized.json
│       ├── 06_deduplicated.json
│       ├── 07_summarized.json
│       ├── 08_classified.json
│       └── 09_aggregated.json
├── output/                    # 최종 결과물
│   └── {target_date}/
│       ├── daily_report.md
│       └── daily_report.json
└── logs/                      # 파이프라인 실행 로그
    └── {target_date}/
        └── pipeline.jsonl
```

**Structure Decision**: 단일 프로젝트 구조. agent 기반 파이프라인이지만
모두 하나의 Python 패키지 내에서 실행되므로, `src/` 하위에 역할별 모듈로
분리한다. `data/` 디렉토리에 단계별 캐시와 최종 출력을 분리하여
checkpoint 기반 재시작을 지원한다.

## Complexity Tracking

> No Constitution Check violations. This section is intentionally empty.
