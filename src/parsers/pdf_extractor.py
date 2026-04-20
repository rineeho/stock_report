"""PDF text extraction utility using pdfplumber.

Pure function: takes PDF bytes, returns extracted text.
Handles only text-selectable PDFs (no OCR, no VLM).
Also provides regex-based metadata extraction (analyst, sector)
from Korean securities research report text, with LLM fallback.
"""

from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pdfplumber
import structlog

if TYPE_CHECKING:
    from src.summarizer.llm_client import BaseLLMClient

logger = structlog.get_logger()

# Minimum characters per page to consider extraction successful.
# Below this threshold, the PDF likely contains only images/scans.
MIN_CHARS_PER_PAGE = 20


@dataclass(frozen=True)
class PdfExtractionResult:
    """Result of PDF text extraction."""

    text: str
    page_count: int
    char_count: int
    success: bool
    error: str | None = None


def extract_text_from_pdf(pdf_bytes: bytes) -> PdfExtractionResult:
    """Extract text from PDF bytes using pdfplumber.

    Args:
        pdf_bytes: Raw PDF file content.

    Returns:
        PdfExtractionResult with extracted text or error info.
    """
    if not pdf_bytes:
        return PdfExtractionResult(
            text="",
            page_count=0,
            char_count=0,
            success=False,
            error="empty_pdf_bytes",
        )

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages_text: list[str] = []
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                pages_text.append(page_text)

            full_text = "\n\n".join(pages_text).strip()
            page_count = len(pdf.pages)
            char_count = len(full_text)

            # Heuristic: if avg chars per page is very low, the PDF
            # is likely scanned/image-only, not text-selectable.
            if page_count > 0 and (char_count / page_count) < MIN_CHARS_PER_PAGE:
                return PdfExtractionResult(
                    text=full_text,
                    page_count=page_count,
                    char_count=char_count,
                    success=False,
                    error="insufficient_text_content",
                )

            return PdfExtractionResult(
                text=full_text,
                page_count=page_count,
                char_count=char_count,
                success=True,
            )

    except Exception as exc:
        logger.warning("pdf_extraction_failed", error=str(exc))
        return PdfExtractionResult(
            text="",
            page_count=0,
            char_count=0,
            success=False,
            error=f"extraction_error:{type(exc).__name__}:{exc}",
        )


# ---------------------------------------------------------------------------
# Metadata extraction from Korean securities research report text
# ---------------------------------------------------------------------------

# Common Korean surnames (covers ~99% of population)
_KOREAN_SURNAMES = frozenset(
    "김이박최정강조윤장임한오서신권황안송류전홍고문양손배백허유남심노하곽성차주우"
    "구신임나전민유진지엄채원천방공강현함변염양변탁반라마서길"
)

# Words that look like 2-4 char Korean names but are financial/common terms
_ANALYST_BLOCKLIST = frozenset({
    "매출액", "영업이익", "순이익", "자산총계", "부채총계", "자본총계",
    "익잉여금", "이익잉여", "금성자산", "유동자산", "비유동자", "고정자산",
    "특허", "에서", "으로", "까지", "부터", "에는", "에도", "에게",
    "하여", "한다", "이다", "된다", "한편", "또한", "따라", "통해",
    "기준", "전망", "추정", "예상", "의견", "목표", "현재", "기간",
    "분기", "반기", "연간", "전년", "당기", "합계", "소계", "기타",
    "보통주", "우선주", "발행주", "시가총", "외국인", "주주구",
    "투자의", "투자등", "참고서", "사업보", "감사보",
})


def _is_valid_korean_name(name: str) -> bool:
    """Check if a string looks like a valid Korean person name."""
    if not name or len(name) < 2 or len(name) > 4:
        return False
    if name in _ANALYST_BLOCKLIST:
        return False
    # First character should be a known Korean surname
    if name[0] not in _KOREAN_SURNAMES:
        return False
    return True


def extract_analyst_from_pdf_text(text: str | None) -> str | None:
    """Extract analyst name from Korean research report PDF text.

    Tries multiple patterns common in Korean securities research reports.
    Returns the first matched Korean name (2-4 characters) that passes
    surname validation and blocklist filtering.
    """
    if not text:
        return None

    # Only search the first ~2000 chars (analyst info is always near the top)
    header = text[:2000]

    patterns = [
        # "Analyst 홍길동" or "Research Analyst 홍길동"
        r"(?:Research\s+)?Analyst\s*[:：]?\s*([가-힣]{2,4})",
        # "애널리스트 홍길동" or "담당애널리스트: 홍길동"
        r"(?:담당\s*)?애널리스트\s*[:：]?\s*([가-힣]{2,4})",
        # "담당자: 홍길동" or "담당: 홍길동"
        r"담당[자]?\s*[:：]\s*([가-힣]{2,4})",
        # Korean name directly followed by email on same/next line
        r"([가-힣]{2,4})\s+[\w.+-]+@[\w.-]+\.\w{2,}",
        # Korean name directly followed by phone (02-XXXX-XXXX style)
        r"([가-힣]{2,4})\s+\(?\d{2,3}\)?[\s.-]*\d{3,4}[\s.-]*\d{4}",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, header, re.IGNORECASE):
            name = match.group(1).strip()
            if _is_valid_korean_name(name):
                return name

    return None


def extract_sector_from_pdf_text(text: str | None) -> str | None:
    """Extract sector/industry classification from PDF text.

    Looks for common Korean securities report sector labels.
    """
    if not text:
        return None

    header = text[:2000]

    patterns = [
        # "KOSPI | 반도체" or "KOSDAQ | IT서비스" (AI report format)
        r"KOS(?:PI|DAQ)\s*\|\s*([가-힣A-Za-z0-9/&·]+(?:[/\s]+[가-힣A-Za-z0-9/&·]+)*)",
        # "업종: 반도체" or "업종 : IT"
        r"업종\s*[:：]\s*([가-힣A-Za-z0-9/&·]+(?:[ \t]+[가-힣A-Za-z0-9/&·]+)*)",
        # "섹터: 자동차" or "Sector: Automotive"
        r"(?:섹터|Sector)\s*[:：]\s*([가-힣A-Za-z0-9/&·]+(?:[ \t]+[가-힣A-Za-z0-9/&·]+)*)",
        # "Industry: 반도체"
        r"Industry\s*[:：]\s*([가-힣A-Za-z0-9/&·]+(?:[ \t]+[가-힣A-Za-z0-9/&·]+)*)",
        # Analyst line with sector: "홍길동 반도체/IT" (name followed by Korean sector)
        r"Analyst\s*[:：]?\s*[가-힣]{2,4}\s+([가-힣][가-힣A-Za-z0-9/&·]+(?:[/·]\s*[가-힣A-Za-z0-9]+)*)",
    ]

    for pattern in patterns:
        match = re.search(pattern, header, re.IGNORECASE)
        if match:
            sector = match.group(1).strip()
            if sector and len(sector) >= 2:
                return sector

    return None


def extract_market_type_from_pdf_text(text: str | None) -> str | None:
    """Extract market type (KOSPI/KOSDAQ) from PDF text."""
    if not text:
        return None

    header = text[:1500]

    # Direct mention: "KOSPI" or "KOSDAQ" near the top
    match = re.search(r"\b(KOSPI|KOSDAQ)\b", header, re.IGNORECASE)
    if match:
        return match.group(1).upper()

    # Korean: "코스피" or "코스닥"
    match = re.search(r"(코스피|코스닥)", header)
    if match:
        return "KOSPI" if match.group(1) == "코스피" else "KOSDAQ"

    return None


# ---------------------------------------------------------------------------
# LLM-based metadata extraction fallback
# ---------------------------------------------------------------------------

_METADATA_EXTRACTION_SYSTEM = """당신은 한국 증권 리포트 메타데이터 추출 전문가입니다.
주어진 텍스트에서 애널리스트 이름, 업종/섹터, 시장구분을 추출하십시오.
반드시 JSON 형식으로만 응답하십시오."""

_METADATA_EXTRACTION_PROMPT = """다음은 한국 증권사 리포트 PDF의 앞부분 텍스트입니다.
이 텍스트에서 다음 정보를 추출하십시오:

1. analyst: 리포트를 작성한 애널리스트의 한국어 실명 (2-4자, 성+이름). 회사명이나 금융용어가 아닌 사람 이름만. 없으면 null.
2. sector: 해당 종목의 업종/섹터 분류. 없으면 null.
3. market_type: "KOSPI" 또는 "KOSDAQ". 없으면 null.

## 텍스트
{text}

## 응답 형식 (JSON만 출력)
{{"analyst": "<이름 또는 null>", "sector": "<업종 또는 null>", "market_type": "<KOSPI 또는 KOSDAQ 또는 null>"}}"""


async def extract_metadata_via_llm(
    text: str, llm_client: BaseLLMClient
) -> dict[str, str | None]:
    """Extract analyst/sector/market_type from PDF text using LLM as fallback.

    Args:
        text: PDF text (will be truncated to first 1500 chars).
        llm_client: LLM client instance.

    Returns:
        Dict with 'analyst', 'sector', 'market_type' keys (values may be None).
    """
    truncated = text[:1500]
    prompt = _METADATA_EXTRACTION_PROMPT.format(text=truncated)

    try:
        raw_response = await llm_client.generate(prompt, system=_METADATA_EXTRACTION_SYSTEM)
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            cleaned = "\n".join(lines)
        result = json.loads(cleaned)
        analyst = result.get("analyst")
        if analyst and not _is_valid_korean_name(analyst):
            analyst = None
        market_type = result.get("market_type")
        if market_type and market_type.upper() in ("KOSPI", "KOSDAQ"):
            market_type = market_type.upper()
        else:
            market_type = None
        return {
            "analyst": analyst,
            "sector": result.get("sector"),
            "market_type": market_type,
        }
    except Exception as exc:
        logger.warning("llm_metadata_extraction_failed", error=str(exc))
        return {"analyst": None, "sector": None, "market_type": None}
