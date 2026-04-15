<!--
=== Sync Impact Report ===
Version change: 0.0.0 → 1.0.0 (MAJOR - initial ratification)
Modified principles: N/A (initial version)
Added sections:
  - Core Principles (10 principles: I~X)
  - Technology & Operational Constraints
  - Development Workflow & Quality Gates
  - Governance
Removed sections: N/A
Templates requiring updates:
  - .specify/templates/plan-template.md: ✅ compatible (Constitution Check section is generic)
  - .specify/templates/spec-template.md: ✅ compatible (no constitution-specific references)
  - .specify/templates/tasks-template.md: ✅ compatible (phase structure accommodates agent-based tasks)
  - .specify/templates/commands/*.md: ✅ no command templates found
Follow-up TODOs: none
===
-->

# Report Agent Constitution

## Core Principles

### I. Data Accuracy First (NON-NEGOTIABLE)

- "당일 리포트"는 반드시 출처의 날짜 정보(본문 텍스트, HTML 메타데이터,
  PDF 속성 등)를 통해 검증된 경우에만 포함한다.
- 날짜가 불명확하거나 파싱 불가능한 경우 기본적으로 결과에서 제외하고,
  별도로 `UNVERIFIED` 상태로 표시하여 수동 검토 대상으로 분류한다.
- 모든 리포트 레코드는 다음 필수 필드를 포함해야 한다:
  - `source_url`: 원본 페이지 또는 파일의 URL
  - `published_date`: 발행일 (ISO 8601, timezone-aware)
  - `brokerage`: 증권사명 (정규화된 형태)
  - `analyst`: 애널리스트명
  - `title`: 리포트 제목
- 필수 필드가 하나라도 누락된 레코드는 최종 결과에 포함하지 않는다.

### II. Source Traceability

- 모든 최종 결과물은 원본 페이지 또는 파일로 역추적 가능해야 한다.
- 파이프라인의 각 단계(수집 → 파싱 → 검증 → 중복제거 → 요약 → 출력)는
  구조화된 로그를 남겨야 한다. 로그에는 최소한 timestamp, stage, input_id,
  output_id, status를 포함한다.
- 최종 결과물의 모든 항목에는 반드시 `source_url` 필드를 포함하며,
  해당 URL은 접근 가능한 원본 리소스를 가리켜야 한다.

### III. Collection Ethics & Compliance

- 사전에 승인된 사이트 목록(allowlist)에 등록된 출처에서만 수집한다.
  미등록 사이트로의 자동 수집은 금지한다.
- 각 대상 사이트의 `robots.txt` 지시사항을 준수한다.
- 서비스 약관(ToS)에서 자동 수집을 금지하는 경우 해당 사이트를 제외한다.
- 인증이 필요한 페이지는 정당한 자격 증명이 있는 경우에만 접근하며,
  세션 우회, 캡차 회피 등의 수단을 사용하지 않는다.
- 각 사이트별로 정의된 rate limit을 초과하지 않는다.
  rate limit이 명시되지 않은 경우 보수적인 기본값(예: 1 req/sec)을 적용한다.
- 유료 콘텐츠 또는 접근 차단된 콘텐츠를 우회하여 수집하지 않는다.

### IV. Daily Determinism

- 시스템은 "특정 날짜"를 기준으로 동작한다.
  모든 파이프라인 실행은 명시적인 `target_date` 파라미터를 받는다.
- 기본 타임존은 `Asia/Seoul` (KST, UTC+9)로 설정한다.
  날짜 경계 판단은 항상 이 타임존 기준으로 수행한다.
- 동일한 `target_date`와 동일한 입력 데이터에 대해 동일한 결과가
  산출되어야 한다 (결정적 처리).
- 외부 상태(네트워크 시점, 사이트 변경 등)에 의한 비결정성은
  캐싱 또는 스냅샷을 통해 최소화한다.

### V. Deduplication & Normalization

- 동일 리포트가 복수 형식(PDF, HTML, 재게시 등)으로 존재하는 경우
  하나의 canonical 레코드로 통합한다.
- 다음 필드는 표준화된 형태로 정규화한다:
  - `title`: 불필요한 접두/접미사 제거, 공백 정규화
  - `brokerage`: 정규화된 증권사명 매핑 테이블 사용
  - `ticker`/`stock_name`: 종목 코드 및 종목명 표준화
  - `published_date`: ISO 8601 형식, timezone-aware
- 단순 중복(동일 콘텐츠의 재게시)과 수정본(리비전)을 구분한다.
  수정본은 별도 표시하되 최신 버전을 primary로 취급한다.

### VI. Summary Quality & Anti-Hallucination (NON-NEGOTIABLE)

- 요약은 원문에 명시적으로 존재하는 사실 정보만을 기반으로 작성한다.
- 목표주가, 실적 수치, 투자 의견 등 수치/판단 정보는 원문에서
  직접 추출한 경우에만 포함하며, 임의로 생성하지 않는다.
- 원문에 해당 정보가 존재하지 않는 경우 필드 값을 `null` 또는
  "정보 없음"으로 명시한다. 추측으로 채우지 않는다.
- 생성된 요약 텍스트와 원문에서 직접 추출한 정보는 구조적으로 분리하여
  소비자가 구별할 수 있도록 한다 (예: `extracted` vs `generated` 태그).

### VII. Agent Role Separation

- 파이프라인의 각 책임을 독립된 agent로 분리한다:
  수집(Collector) / 검증(Validator) / 정규화(Normalizer) /
  중복제거(Deduplicator) / 요약(Summarizer) / 분류(Classifier) /
  출력(Publisher).
- Agent 간 데이터 전달은 구조화된 스키마(JSON Schema 등)를 사용하며,
  스키마는 버전 관리한다.
- 개별 agent의 실패가 전체 파이프라인의 실패로 이어지지 않도록
  격리(isolation)하여 설계한다. 실패한 agent의 결과는 건너뛰거나
  부분 결과로 처리한다.
- 각 agent는 독립적으로 테스트, 배포, 교체 가능해야 한다.

### VIII. Testability

- 각 사이트 파서는 저장된 샘플 HTML/PDF 기반의 스냅샷 테스트를
  포함해야 한다. 실제 네트워크 호출 없이 파서 동작을 검증할 수 있어야 한다.
- 날짜 추출 로직은 다양한 날짜 형식에 대한 파라미터화된 테스트를
  포함해야 한다.
- 중복 제거 로직은 알려진 중복 쌍에 대한 검증 테스트를 포함해야 한다.
- 분류 로직은 기대 카테고리와 실제 결과를 비교하는 테스트를 포함해야 한다.
- 요약 생성기는 환각 검출 테스트(원문에 없는 수치가 요약에 등장하는지)를
  포함해야 한다.

### IX. Operational Stability

- 파이프라인은 중간 단계에서 중단된 경우 해당 단계부터 재시작 가능한
  checkpoint 구조를 가져야 한다.
- 모든 실패는 구조화된 에러 로그로 기록한다. 로그에는 최소한 timestamp,
  stage, error_type, error_message, affected_item_id를 포함한다.
- 재시도(retry) 로직은 최대 횟수와 backoff 간격이 제한되어야 하며,
  무한 재시도는 금지한다. 기본값: 최대 3회, exponential backoff.
- 외부 서비스 장애 시 graceful degradation을 적용한다.

### X. Output Practicality

- 최종 결과물은 투자자가 하루치 리포트 현황을 5분 이내에 파악할 수
  있는 형태여야 한다.
- 사람이 읽기 좋은 요약(Markdown/HTML)과 프로그래밍 방식으로 소비 가능한
  구조화 데이터(JSON) 두 가지 형태를 모두 제공한다.
- 결과물은 증권사별, 종목별, 섹터별 등 다양한 기준으로 정렬/필터링이
  가능한 구조여야 한다.

## Technology & Operational Constraints

- **Language**: Python 3.11+
- **Timezone**: 모든 날짜/시간 처리는 `Asia/Seoul` 기준.
  datetime 객체는 항상 timezone-aware로 생성한다.
- **Allowlist 관리**: 수집 대상 사이트 목록은 설정 파일로 관리하며,
  각 사이트별 rate limit, 파서 타입, 인증 방식을 명시한다.
- **데이터 형식**: Agent 간 통신 및 중간 데이터는 JSON Schema로
  정의된 구조를 사용한다.
- **로깅**: 구조화된 JSON 로그를 표준으로 사용한다.
  로그 레벨은 DEBUG, INFO, WARNING, ERROR로 구분한다.
- **의존성**: 외부 API 또는 LLM 호출에 대한 의존은 명시적으로
  추상화하여, mock/stub으로 교체 가능해야 한다.

## Development Workflow & Quality Gates

- **Gate 1 — Schema Compliance**: 모든 agent의 입출력은 정의된
  JSON Schema에 부합해야 한다. 스키마 위반 시 파이프라인 진행을 차단한다.
- **Gate 2 — Parser Snapshot Test**: 새로운 사이트 파서를 추가하거나
  기존 파서를 수정할 때, 최소 3개의 샘플 기반 스냅샷 테스트를 통과해야 한다.
- **Gate 3 — Date Extraction Accuracy**: 날짜 추출 로직 변경 시
  기존 테스트 케이스 전체 통과 필수.
- **Gate 4 — Hallucination Check**: 요약 로직 변경 시 환각 검출
  테스트를 통과해야 한다.
- **Gate 5 — Determinism Verification**: 동일 입력에 대해 동일 출력이
  나오는지 검증하는 테스트를 포함한다.
- **Code Review**: 모든 PR은 이 헌법의 원칙 준수 여부를 체크리스트로
  확인한 후 병합한다.

## Governance

- 이 헌법은 프로젝트의 모든 설계 및 구현 의사결정을 지배한다.
  헌법과 충돌하는 구현은 허용되지 않는다.
- 헌법 개정은 다음 절차를 따른다:
  1. 변경 사유 및 영향 범위를 문서화한다.
  2. 기존 원칙과의 충돌 여부를 검토한다.
  3. Sync Impact Report를 작성하고 관련 템플릿을 갱신한다.
  4. 버전을 시맨틱 버저닝에 따라 증가시킨다.
- 버전 정책:
  - MAJOR: 원칙의 삭제 또는 근본적 재정의 (하위 호환 불가)
  - MINOR: 새로운 원칙 추가 또는 기존 원칙의 실질적 확장
  - PATCH: 문구 수정, 오타, 비의미적 개선
- `NON-NEGOTIABLE`로 표시된 원칙(I, VI)은 MAJOR 버전 변경 없이
  완화하거나 제거할 수 없다.
- 모든 PR 리뷰에서 헌법 준수 여부를 확인한다.

**Version**: 1.0.0 | **Ratified**: 2026-04-10 | **Last Amended**: 2026-04-10
