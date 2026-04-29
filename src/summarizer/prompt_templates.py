"""Korean summarization prompt templates with anti-hallucination instructions."""

from __future__ import annotations

SYSTEM_PROMPT = """당신은 한국 주식 리포트 요약 전문가입니다.
규칙:
1. 원문에 있는 정보만 추출하십시오.
2. 원문에 없는 수치(목표주가, 실적 등)를 절대 생성하지 마십시오.
3. 정보가 없으면 반드시 null로 표시하십시오.
4. 모든 출력은 한국어로 작성하십시오.
5. 반드시 아래 JSON 형식으로만 응답하십시오."""

SUMMARY_PROMPT_TEMPLATE = """다음 주식 리포트를 분석하여 JSON 형식으로 요약하십시오.

## 리포트 정보
- 제목: {title}
- 증권사: {brokerage}
- 종목: {stock_name} ({ticker})

## 본문
{body_text}

## 응답 형식 (JSON만 출력)
{{
  "extracted": {{
    "target_price": <목표주가 숫자 또는 null>,
    "previous_target_price": <이전 목표주가 숫자 또는 null>,
    "target_price_change": "<목표주가 변동 방향: 상향/하향/유지 또는 null>",
    "rating": "<투자의견 문자열 또는 null>",
    "earnings": "<실적 정보 문자열 또는 null>",
    "analyst": "<애널리스트 이름(한국어 2-4자) 또는 null>",
    "sector": "<업종/섹터 문자열 또는 null>"
  }},
  "generated": {{
    "key_points": ["<핵심 포인트 1>", "<핵심 포인트 2>", "<핵심 포인트 3>"],
    "one_line": "<한 줄 요약>",
    "opinion_summary": "<투자 의견 요약 또는 null>"
  }}
}}

중요:
- extracted 필드는 본문에서 직접 추출한 값만 사용하십시오. 본문에 없는 정보는 반드시 null로 작성하십시오.
- previous_target_price: 리포트에서 "기존 목표주가", "종전 목표가", "목표주가 NN만원에서 NN만원으로" 등의 표현에서 이전 목표주가를 추출하십시오.
- target_price_change: 목표주가가 이전 대비 올랐으면 "상향", 내렸으면 "하향", 동일하면 "유지"로 표시하십시오. 본문에 "상향", "하향", "유지" 등의 직접적 표현이 있으면 그대로 따르십시오. 판단할 수 없으면 null로 작성하십시오."""

INACCESSIBLE_BODY_PROMPT = """이 리포트는 본문에 접근할 수 없습니다.

## 리포트 정보
- 제목: {title}
- 증권사: {brokerage}
- 종목: {stock_name} ({ticker})

본문을 확인할 수 없으므로 다음과 같이 응답하십시오:
{{
  "extracted": {{
    "target_price": null,
    "previous_target_price": null,
    "target_price_change": null,
    "rating": null,
    "earnings": null
  }},
  "generated": {{
    "key_points": ["본문 접근 불가"],
    "one_line": "본문 접근 불가 - 메타데이터만 확인 가능",
    "opinion_summary": null
  }}
}}"""


def build_summary_prompt(
    title: str,
    brokerage: str,
    stock_name: str | None,
    ticker: str | None,
    body_text: str | None,
) -> str:
    """Build the prompt for a report summary request.

    Handles inaccessible body per FR-023.
    """
    if not body_text or body_text == "본문 접근 불가":
        return INACCESSIBLE_BODY_PROMPT.format(
            title=title,
            brokerage=brokerage,
            stock_name=stock_name or "N/A",
            ticker=ticker or "N/A",
        )

    return SUMMARY_PROMPT_TEMPLATE.format(
        title=title,
        brokerage=brokerage,
        stock_name=stock_name or "N/A",
        ticker=ticker or "N/A",
        body_text=body_text[:15000],  # truncate very long texts
    )
