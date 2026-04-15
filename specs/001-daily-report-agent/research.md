# Research: Daily Stock Report Agent System

**Date**: 2026-04-10
**Branch**: `001-daily-report-agent`

## R1: HTTP Client Selection

**Decision**: httpx (async 지원)
**Rationale**: asyncio 기반으로 여러 사이트를 동시에 수집할 수 있으며,
rate limiting, timeout, retry를 세밀하게 제어할 수 있다.
requests 대비 async 지원이 네이티브이고, connection pooling이 우수하다.
**Alternatives considered**:
- `requests`: 동기 전용, 동시 수집 시 threading 필요
- `aiohttp`: 가능하나 httpx의 API가 더 직관적이고 sync/async 모두 지원

## R2: HTML Parsing

**Decision**: beautifulsoup4 + lxml parser
**Rationale**: 한국 금융 사이트의 불규칙한 HTML을 안정적으로 처리.
lxml 파서가 속도와 관용성(malformed HTML 처리) 면에서 최적.
**Alternatives considered**:
- `scrapy`: 프레임워크 수준으로 과도. 단일 파이프라인에서 agent별로
  제어하기 어려움
- `selectolax`: 빠르지만 생태계가 작고, 한국어 사이트 호환성 검증 부족

## R3: PDF Text Extraction

**Decision**: pdfplumber
**Rationale**: 테이블 구조가 포함된 증권 리포트 PDF에서 구조적 텍스트
추출에 강점. pdfminer 기반이지만 API가 훨씬 사용하기 쉽다.
**Alternatives considered**:
- `PyPDF2/pypdf`: 단순 텍스트 추출은 가능하나, 테이블 추출 불가
- `camelot`: 테이블 전문이지만, 설치 복잡 (Ghostscript 의존)
- `pymupdf`: 빠르지만 라이선스 제약 (AGPL)

## R4: Schema Validation

**Decision**: pydantic v2
**Rationale**: Agent 간 데이터 전달에 사용되는 JSON 구조를 Python 타입으로
정의하고 자동 검증. JSON Schema 자동 생성 기능으로 계약 문서화 용이.
**Alternatives considered**:
- `dataclasses + jsonschema`: 가능하나 검증 코드를 별도로 작성해야 함
- `attrs + cattrs`: 유사하지만 pydantic의 JSON Schema 자동 생성이 우위

## R5: Structured Logging

**Decision**: structlog
**Rationale**: JSON 구조화 로그를 자연스럽게 생성. 파이프라인의 각 단계별
로그에 context 정보(stage, item_id 등)를 쉽게 바인딩 가능.
**Alternatives considered**:
- `logging` (stdlib): JSON 포맷터를 수동 구성해야 하며, context 바인딩 불편
- `loguru`: 사용하기 쉽지만 구조화 로그 목적에서 structlog이 더 적합

## R6: LLM Summarization

**Decision**: OpenAI/Anthropic API (추상화 계층으로 교체 가능)
**Rationale**: 요약 품질이 핵심이므로 고성능 LLM 사용. 추상화 계층을 두어
provider를 설정으로 전환 가능하게 한다. 환각 방지를 위해 structured output과
원문 기반 프롬프트를 사용한다.
**Alternatives considered**:
- 로컬 LLM (ollama): 비용 절감 가능하나, 한국어 금융 요약 품질이 부족
- 규칙 기반 요약: 품질 한계가 명확하고, 리포트 형식 다양성에 대응 불가

## R7: 중복 제거 전략

**Decision**: 다단계 매칭 (URL fingerprint → 제목+증권사+날짜 매칭 →
콘텐츠 유사도)
**Rationale**: 단일 기준으로는 중복 판별이 불완전. URL이 동일한 경우는
즉시 중복 처리하고, URL이 다른 경우 메타데이터 조합으로 후보를 추린 뒤
필요시 콘텐츠 유사도로 최종 판별한다.
**Alternatives considered**:
- URL 기반만: PDF 재배포, URL 변형 시 놓침
- 콘텐츠 해시만: 포맷 차이(HTML vs PDF)로 동일 리포트도 해시 불일치
- 제목만: 동일 제목, 다른 종목 케이스에서 오탐

## R8: Checkpoint / 재시작 전략

**Decision**: 파일 기반 단계별 JSON 스냅샷
**Rationale**: 각 agent 처리 완료 시 결과를 `data/cache/{target_date}/`에
JSON으로 저장. 재실행 시 마지막 완료 단계의 캐시를 로드하여 다음 단계부터
진행. 별도 DB나 메시지 큐 없이 파일 시스템만으로 구현 가능.
**Alternatives considered**:
- Redis/RabbitMQ: 인프라 복잡도 증가, 단일 머신에서 과도
- SQLite: 가능하나 JSON 파일이 디버깅/검사에 더 직관적

## R9: Rate Limiting 구현

**Decision**: httpx + 커스텀 rate limiter (token bucket)
**Rationale**: 사이트별로 다른 rate limit을 적용해야 하므로,
사이트 설정(sites.yaml)에서 읽은 값으로 per-site token bucket을 구성.
**Alternatives considered**:
- `ratelimit` 라이브러리: 기능은 충분하나, per-site 세분화에 추가 래핑 필요
- 고정 sleep: 단순하지만 사이트별 차별화 불가

## R10: 날짜 추출 전략

**Decision**: 다단계 추출 (HTML meta → 구조화 데이터 → 본문 패턴 매칭)
**Rationale**: 사이트마다 날짜 표기 위치와 형식이 다르므로,
1) HTML meta 태그 (article:published_time, date 등)
2) JSON-LD / schema.org 구조화 데이터
3) 본문 내 정규식 패턴 매칭
순서로 시도하여 가장 신뢰도 높은 소스를 우선 채택한다.
**Alternatives considered**:
- 본문 패턴만: meta 정보가 있는 경우 불필요하게 느리고 오탐 가능
- 파일 시스템 날짜: 다운로드 시점이지 발행일이 아님
