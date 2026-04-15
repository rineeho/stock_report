---

description: "Task list for Daily Stock Report Agent System"
---

# Tasks: Daily Stock Report Agent System

**Input**: Design documents from `/specs/001-daily-report-agent/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Included per Constitution Principle VIII (Testability) — parser snapshot tests, date extraction tests, deduplication tests, hallucination detection tests.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependencies, and directory structure

- [x] T001 Create project directory structure per plan.md (src/, tests/, data/ with all subdirectories)
- [x] T002 Initialize Python project with pyproject.toml: httpx, beautifulsoup4, lxml, pdfplumber, pydantic, structlog, pytest, pytest-snapshot
- [x] T003 [P] Configure ruff for linting and formatting in pyproject.toml
- [x] T004 [P] Create .env.example with LLM API key placeholders and default settings
- [x] T005 [P] Create .gitignore for Python project (data/cache/, data/logs/, .env, __pycache__/)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 Define all pydantic schemas in src/schemas/report.py (RawReport, ParsedReport, ValidatedReport, NormalizedReport, CanonicalReport, DeduplicationGroup) per data-model.md
- [x] T007 [P] Define Summary schema in src/schemas/summary.py with extracted/generated separation per data-model.md
- [x] T008 [P] Define DailyResult schema in src/schemas/daily_result.py per data-model.md
- [x] T009 [P] Define PipelineLog and StageResult schemas in src/schemas/pipeline.py per data-model.md
- [x] T010 Implement settings loader in src/config/settings.py (timezone=Asia/Seoul, data paths, LLM config, log level)
- [x] T011 [P] Create initial src/config/sites.yaml with 3 sites: naver_research (https://finance.naver.com/research/company_list.naver), hankyung_consensus, broker_direct
- [x] T012 Implement BaseAgent abstract class in src/agents/base.py (run method, input/output schema validation, error handling, logging hooks)
- [x] T013 Implement pipeline orchestrator in src/pipeline/orchestrator.py (sequential agent execution, stage envelope creation per pipeline-stages.json contract)
- [x] T014 [P] Implement checkpoint manager in src/pipeline/checkpoint.py (save/load JSON per stage to data/cache/{target_date}/)
- [x] T015 [P] Implement structured pipeline logger in src/pipeline/logger.py using structlog (JSONL output to data/logs/{target_date}/pipeline.jsonl)
- [x] T016 [P] Implement rate-limited async HTTP client in src/utils/http.py (per-site token bucket from sites.yaml, retry with max 3 attempts + exponential backoff)
- [x] T017 [P] Implement robots.txt checker in src/utils/robots.py (fetch and cache robots.txt, check URL permission)
- [x] T018 [P] Implement timezone utilities in src/utils/timezone.py (Asia/Seoul date boundary, today_kst(), is_same_date_kst())
- [x] T019 Implement BaseSiteParser abstract class in src/parsers/base.py (discover_reports(), parse_report() methods, sample fixture path convention)
- [x] T020 [P] Implement parser registry in src/parsers/registry.py (site_id → parser class mapping, auto-discovery)
- [x] T021 Implement CLI entry point skeleton in src/main.py (argparse: --date, --sites, --from-stage, --output-dir, --format, --verbose, --dry-run per cli-interface.md)

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — 당일 리포트 일괄 수집 및 열람 (Priority: P1) MVP

**Goal**: 특정 날짜를 지정하여 승인된 사이트에서 당일 기업분석 리포트를 수집하고, 날짜 검증된 리포트만 정리된 목록으로 확인

**Independent Test**: 네이버 리서치 파서에 대해 샘플 HTML로 수집 → 파싱 → 검증 → 정규화 파이프라인을 실행하여 당일 리포트만 결과에 포함되는지 확인

### Tests for User Story 1

- [x] T022 [P] [US1] Create sample HTML fixture for naver_research list page in tests/fixtures/sites/naver_research/sample_list_page.html
- [x] T023 [P] [US1] Create sample report fixture (HTML) in tests/fixtures/sites/naver_research/sample_report.html
- [x] T024 [P] [US1] Write parser snapshot test for naver_research in tests/snapshot/test_parsers.py (discover + parse from fixture)
- [x] T025 [P] [US1] Write parameterized date extraction tests in tests/unit/test_date_extraction.py (meta_tag, json_ld, body_pattern, Korean date formats)
- [x] T026 [P] [US1] Write normalization tests in tests/unit/test_normalization.py (brokerage name mapping, ticker standardization, date format unification)

### Implementation for User Story 1

- [x] T027 [US1] Implement SourceDiscoveryAgent in src/agents/source_discovery.py (iterate enabled sites, call parser.discover_reports(), output RawReport list with discovered URLs)
- [x] T028 [US1] Implement naver_research parser in src/parsers/sites/naver_research.py (discover: parse company_list.naver HTML for report links; parse: extract title, date, brokerage, analyst, ticker from report page)
- [x] T029 [US1] Implement FetchAgent in src/agents/fetch.py (download HTML/PDF via rate-limited HTTP client, set fetch_status, handle failures gracefully per FR-018)
- [x] T030 [US1] Implement ParseAgent in src/agents/parse.py (route to site-specific parser via registry, extract metadata into ParsedReport, handle parse failures)
- [x] T031 [US1] Implement multi-strategy date extraction in src/parsers/base.py (HTML meta → JSON-LD → body regex pattern matching per R10)
- [x] T032 [US1] Implement ValidationAgent in src/agents/validate.py (compare published_date to target_date in KST, set validation_status: verified/unverified/rejected per data-model)
- [x] T033 [P] [US1] Implement brokerage name normalizer in src/normalizers/brokerage.py (mapping table: variant names → canonical name)
- [x] T034 [P] [US1] Implement ticker/stock name normalizer in src/normalizers/ticker.py (code ↔ name standardization)
- [x] T035 [P] [US1] Implement date normalizer in src/normalizers/date.py (various Korean date formats → ISO 8601 KST)
- [x] T036 [US1] Implement NormalizationAgent in src/agents/normalize.py (apply brokerage/ticker/date normalizers, filter out reports missing required 5 fields per Constitution I)
- [x] T037 [US1] Wire US1 pipeline in src/main.py (discover → fetch → parse → validate → normalize, save checkpoint per stage, output validated+normalized report list as JSON)
- [x] T038 [US1] Implement basic JSON list output for US1 verification in src/output/json_output.py (NormalizedReport list → data/output/{date}/validated_reports.json)

**Checkpoint**: US1 complete — 당일 리포트 수집, 검증, 정규화된 목록을 JSON으로 확인 가능

---

## Phase 4: User Story 2 — 리포트 핵심 요약 확인 (Priority: P2)

**Goal**: 수집된 각 리포트에 대해 한국어 핵심 요약 생성. 원문에 없는 정보는 생성하지 않음.

**Independent Test**: 샘플 리포트 5건에 대해 요약을 생성하고, 목표주가/실적 수치가 원문에 없는 경우 "정보 없음"으로 표시되는지, extracted/generated가 분리되는지 검증

### Tests for User Story 2

- [x] T039 [P] [US2] Write hallucination detection test in tests/hallucination/test_summary_accuracy.py (원문에 없는 수치가 요약에 등장하면 실패)
- [x] T040 [P] [US2] Write unit test for extracted/generated separation in tests/unit/test_summary_schema.py

### Implementation for User Story 2

- [x] T041 [US2] Implement LLM client abstraction layer in src/summarizer/llm_client.py (provider-agnostic interface, OpenAI/Anthropic adapters, mock adapter for testing)
- [x] T042 [US2] Implement Korean summarization prompt templates in src/summarizer/prompt_templates.py (structured output: key_points, one_line, opinion_summary; anti-hallucination instructions; extracted field extraction prompts)
- [x] T043 [US2] Implement SummarizationAgent in src/agents/summarize.py (call LLM for each CanonicalReport, build Summary with extracted+generated, handle body_text=None as "본문 접근 불가" per FR-023)
- [x] T044 [US2] Wire US2 into pipeline in src/pipeline/orchestrator.py (add summarize stage after normalize, save 07_summarized.json checkpoint)

**Checkpoint**: US2 complete — 리포트별 한국어 요약이 extracted/generated 분리되어 생성됨

---

## Phase 5: User Story 3 — 중복 리포트 통합 (Priority: P3)

**Goal**: 동일 리포트(PDF/HTML/재게시)를 하나의 canonical 항목으로 통합. 단순 중복과 수정본 구분.

**Independent Test**: 동일 리포트가 HTML+PDF 형태로 2개 사이트에서 수집된 샘플에서 1건으로 통합되는지, 동일 제목/다른 종목은 유지되는지 확인

### Tests for User Story 3

- [x] T045 [P] [US3] Write deduplication tests in tests/unit/test_deduplication.py (URL exact match, metadata match, different ticker same title, revision detection)

### Implementation for User Story 3

- [x] T046 [US3] Implement dedup matcher in src/dedup/matcher.py (3-stage: URL fingerprint → title+brokerage+date match → content similarity; revision detection logic per R7)
- [x] T047 [US3] Implement DeduplicationAgent in src/agents/deduplicate.py (group NormalizedReports into DeduplicationGroups, select canonical per group, merge source_urls, mark revisions)
- [x] T048 [US3] Wire US3 into pipeline in src/pipeline/orchestrator.py (add deduplicate stage after normalize, save 06_deduplicated.json checkpoint; reorder: summarize operates on CanonicalReports)

**Checkpoint**: US3 complete — 중복이 통합되고 수정본이 구분된 CanonicalReport 목록 생성

---

## Phase 6: User Story 4 — 분류별 탐색 (Priority: P4)

**Goal**: 수집된 리포트를 증권사별, 종목별, 산업별, 애널리스트별로 그룹화

**Independent Test**: 메타데이터가 있는 리포트 10건에 대해 종목별, 증권사별 그룹화 결과가 올바른지 확인

### Tests for User Story 4

- [x] T049 [P] [US4] Write classification tests in tests/unit/test_classification.py (group by brokerage, ticker, sector, analyst)

### Implementation for User Story 4

- [x] T050 [US4] Implement ClassificationAgent in src/agents/classify.py (group CanonicalReports by brokerage, ticker, sector, analyst; output Classification records)
- [x] T051 [US4] Wire US4 into pipeline in src/pipeline/orchestrator.py (add classify stage after summarize, save 08_classified.json checkpoint)

**Checkpoint**: US4 complete — 리포트가 다양한 기준으로 분류됨

---

## Phase 7: User Story 5 — 최종 결과물 생성 (Priority: P5)

**Goal**: 하루 전체 리포트 현황을 Markdown 요약 + JSON 구조화 데이터 두 가지 형태로 생성

**Independent Test**: 처리 완료된 리포트 세트에 대해 data/output/{date}/ 하위에 daily_report.md와 daily_report.json이 모두 생성되는지 확인

### Implementation for User Story 5

- [x] T052 [US5] Implement AggregationAgent in src/agents/aggregate.py (assemble DailyResult from CanonicalReports + Summaries + Classifications + pipeline stats)
- [x] T053 [P] [US5] Implement Markdown output generator in src/output/markdown.py (증권사별/종목별 그룹 헤더, 리포트 요약 목록, 통계 요약, source URL 포함)
- [x] T054 [P] [US5] Implement JSON output generator in src/output/json_output.py (DailyResult schema → daily_report.json, validated against report-schema.json contract)
- [x] T055 [US5] Implement OutputAgent in src/agents/output.py (call markdown + json generators, write to data/output/{target_date}/)
- [x] T056 [US5] Wire US5 into pipeline in src/pipeline/orchestrator.py (add aggregate + output stages, save 09_aggregated.json checkpoint, write final outputs)
- [x] T057 [US5] Update CLI in src/main.py to support --format flag (json/md/all) and --output-dir override per cli-interface.md

**Checkpoint**: US5 complete — 전체 파이프라인이 end-to-end로 동작하며 Markdown + JSON 결과물 생성

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 추가 사이트 파서, 통합 테스트, 운영 안정성 향상

- [x] T058 [P] Implement hankyung_consensus parser in src/parsers/sites/hankyung_consensus.py (discover + parse for 한경컨센서스)
- [x] T059 [P] Create sample fixtures for hankyung_consensus in tests/fixtures/sites/hankyung_consensus/
- [x] T060 [P] Write parser snapshot test for hankyung_consensus in tests/snapshot/test_parsers.py
- [x] T061 [P] Implement broker_direct parser stub in src/parsers/sites/broker_direct.py (placeholder for 증권사 직접 리서치센터)
- [x] T062 Write integration test for full pipeline in tests/integration/test_pipeline.py (fixture-based end-to-end: discover → output with sample data)
- [x] T063 [P] Write agent chain data passing test in tests/integration/test_agent_chain.py (verify stage envelope schema compliance between each agent pair)
- [x] T064 Implement CLI utility commands in src/main.py (sites list, sites test, cache list, cache clear per cli-interface.md)
- [x] T065 [P] Add --dry-run mode to pipeline orchestrator in src/pipeline/orchestrator.py (validate config, check site accessibility, report without actual collection)
- [x] T066 Run quickstart.md validation (follow quickstart steps end-to-end and verify)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational — core pipeline MVP
- **US2 (Phase 4)**: Depends on US1 (needs parsed/validated reports to summarize)
- **US3 (Phase 5)**: Depends on US1 (needs normalized reports to deduplicate). Can run in parallel with US2.
- **US4 (Phase 6)**: Depends on US1 (needs metadata for classification). Can run in parallel with US2/US3.
- **US5 (Phase 7)**: Depends on US1 + US2 + US3 + US4 (aggregates all results)
- **Polish (Phase 8)**: Can start after US1 for parsers; full integration after US5

### User Story Dependencies

```text
Phase 1 (Setup) → Phase 2 (Foundation)
                        │
                        ▼
                   Phase 3 (US1: 수집/검증) ──────────────────┐
                        │                                      │
                  ┌─────┼─────────┐                           │
                  ▼     ▼         ▼                           │
            Phase 4  Phase 5  Phase 6                         │
            (US2:    (US3:    (US4:                           │
             요약)   중복제거)  분류)                           │
                  │     │         │                           │
                  └─────┼─────────┘                           │
                        ▼                                      │
                   Phase 7 (US5: 결과 생성) ◄─────────────────┘
                        │
                        ▼
                   Phase 8 (Polish)
```

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Schemas/models before agents
- Agents before pipeline wiring
- Core logic before integration

### Parallel Opportunities

- Phase 1: T003, T004, T005 can run in parallel
- Phase 2: T007, T008, T009, T011, T014, T015, T016, T017, T018, T020 can run in parallel (after T006)
- Phase 3: T022~T026 (tests) can run in parallel; T033, T034, T035 (normalizers) can run in parallel
- Phase 4: T039, T040 (tests) can run in parallel
- Phase 4, 5, 6 can run in parallel after Phase 3 completion
- Phase 8: T058~T061 (additional parsers) can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all US1 test fixtures and tests together:
Task: "Create sample HTML fixture for naver_research list page"
Task: "Create sample report fixture (HTML)"
Task: "Write parser snapshot test for naver_research"
Task: "Write parameterized date extraction tests"
Task: "Write normalization tests"

# Launch all US1 normalizers together (after schemas):
Task: "Implement brokerage name normalizer in src/normalizers/brokerage.py"
Task: "Implement ticker/stock name normalizer in src/normalizers/ticker.py"
Task: "Implement date normalizer in src/normalizers/date.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: 네이버 리서치에서 오늘 날짜 리포트를 수집하여 검증된 목록이 JSON으로 출력되는지 확인
5. Demo if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 (수집/검증) → MVP! 당일 리포트 목록 확인 가능
3. US3 (중복 제거) → 중복 없는 깔끔한 목록
4. US2 (요약) → 각 리포트 핵심 요약 추가
5. US4 (분류) → 증권사/종목별 탐색 가능
6. US5 (결과 생성) → Markdown + JSON 최종 결과물
7. Polish → 추가 사이트, 통합 테스트, 운영 안정성

### Recommended Execution (Solo Developer)

Phase 1 → Phase 2 → Phase 3 (US1) → Phase 5 (US3) → Phase 4 (US2) → Phase 6 (US4) → Phase 7 (US5) → Phase 8

*Note*: US3 (중복 제거)를 US2 (요약)보다 먼저 구현하면, 중복 제거된 CanonicalReport에 대해서만 LLM 요약을 실행하여 API 비용을 절감할 수 있다.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Constitution Principle VIII requires tests for parsers, date extraction, dedup, and hallucination
