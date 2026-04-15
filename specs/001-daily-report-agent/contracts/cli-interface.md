# CLI Interface Contract

## Primary Command

```
report-agent run [OPTIONS]
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--date` / `-d` | DATE (YYYY-MM-DD) | today (KST) | 수집 대상 날짜 |
| `--sites` / `-s` | STRING (comma-separated) | all enabled | 특정 사이트만 실행 |
| `--from-stage` | STRING | discover | 재시작할 단계 |
| `--output-dir` / `-o` | PATH | data/output/{date}/ | 결과 출력 경로 |
| `--format` / `-f` | STRING (json,md,all) | all | 출력 형식 |
| `--verbose` / `-v` | FLAG | false | 상세 로그 출력 |
| `--dry-run` | FLAG | false | 실제 수집 없이 설정 검증만 |

### Examples

```bash
# 오늘 날짜로 전체 파이프라인 실행
report-agent run

# 특정 날짜 지정
report-agent run --date 2026-04-10

# 특정 사이트만 수집
report-agent run --sites hankyung,naver_research

# 검증 단계부터 재시작 (이전 캐시 사용)
report-agent run --date 2026-04-10 --from-stage validate

# JSON만 출력
report-agent run --format json

# 설정 검증만 (수집 안 함)
report-agent run --dry-run
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | 성공 (모든 사이트 처리 완료) |
| 1 | 부분 성공 (일부 사이트 실패, 결과는 생성됨) |
| 2 | 설정 오류 (sites.yaml 문제, 잘못된 인자 등) |
| 3 | 전체 실패 (결과 생성 불가) |

### Output

성공 시 다음 파일이 생성된다:

```
data/output/{target_date}/
├── daily_report.md       # 사람 읽기용 Markdown 결과물
└── daily_report.json     # 구조화 데이터 (DailyResult 스키마)
```

## Utility Commands

```bash
# 사이트 목록 확인
report-agent sites list

# 특정 사이트 파서 테스트 (샘플 URL)
report-agent sites test <site_id> [--url <test_url>]

# 캐시 현황 확인
report-agent cache list [--date <date>]

# 특정 날짜 캐시 삭제
report-agent cache clear --date <date>
```

## Standard Output

- 진행 상황은 stderr로 출력 (progress bar, 단계별 상태)
- 최종 결과 요약은 stdout으로 출력
- 구조화된 로그는 `data/logs/{target_date}/pipeline.jsonl`로 기록
