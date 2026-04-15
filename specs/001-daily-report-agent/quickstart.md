# Quickstart: Daily Stock Report Agent System

## Prerequisites

- Python 3.11+
- pip (패키지 관리자)
- LLM API 키 (OpenAI 또는 Anthropic)

## Setup

```bash
# 1. 저장소 클론 및 디렉토리 진입
git clone <repository-url>
cd report

# 2. 가상 환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. 의존성 설치
pip install -e .

# 4. 환경 변수 설정
cp .env.example .env
# .env 파일을 열어 LLM API 키 설정
```

## Configuration

### 사이트 설정 (src/config/sites.yaml)

```yaml
sites:
  - site_id: example_site
    name: "예시 증권사 리서치"
    base_url: "https://example.com/research"
    parser_type: example_site
    rate_limit_rps: 1.0
    auth_type: none
    enabled: true
```

### 새 사이트 추가

1. `src/parsers/sites/` 하위에 파서 파일 생성
2. `BaseSiteParser`를 상속하여 `discover()`, `parse()` 메서드 구현
3. `src/config/sites.yaml`에 사이트 항목 추가
4. `tests/fixtures/sites/{site_id}/`에 샘플 파일 추가
5. `tests/snapshot/test_parsers.py`에 스냅샷 테스트 추가

## Usage

```bash
# 오늘 리포트 수집 및 요약
report-agent run

# 특정 날짜 지정
report-agent run --date 2026-04-10

# 결과 확인
cat data/output/2026-04-10/daily_report.md
```

## Verification

```bash
# 전체 테스트 실행
pytest

# 파서 스냅샷 테스트만
pytest tests/snapshot/

# 환각 검출 테스트만
pytest tests/hallucination/

# 설정 검증 (실제 수집 없이)
report-agent run --dry-run
```

## Troubleshooting

- **"No reports found"**: 해당 날짜에 리포트가 없거나, 사이트 접근에 실패한 경우.
  `data/logs/{date}/pipeline.jsonl`을 확인한다.
- **파서 오류**: 사이트 구조가 변경되었을 수 있다.
  `report-agent sites test <site_id>`로 파서 동작을 확인한다.
- **Rate limit 초과**: `sites.yaml`에서 `rate_limit_rps` 값을 낮춘다.
- **LLM API 오류**: `.env` 파일의 API 키를 확인한다.
  요약 단계만 실패한 경우, `--from-stage summarize`로 재시작할 수 있다.
