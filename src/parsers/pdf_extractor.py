"""PDF text extraction utility using pdfplumber.

Pure function: takes PDF bytes, returns extracted text.
Handles only text-selectable PDFs (no OCR, no VLM).
Also provides regex-based metadata extraction (analyst, sector)
from Korean securities research report text.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass

import pdfplumber
import structlog

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


def extract_analyst_from_pdf_text(text: str | None) -> str | None:
    """Extract analyst name from Korean research report PDF text.

    Tries multiple patterns common in Korean securities research reports.
    Returns the first matched Korean name (2-4 characters).
    """
    if not text:
        return None

    patterns = [
        # "Analyst 홍길동" or "Research Analyst 홍길동"
        r"(?:Research\s+)?Analyst\s*[:：]?\s*([가-힣]{2,4})",
        # "애널리스트 홍길동" or "담당애널리스트: 홍길동"
        r"(?:담당\s*)?애널리스트\s*[:：]?\s*([가-힣]{2,4})",
        # "담당자: 홍길동" or "담당: 홍길동"
        r"담당[자]?\s*[:：]\s*([가-힣]{2,4})",
        # Korean name followed by email (name\nemail or name email)
        r"([가-힣]{2,4})\s*\n?\s*[\w.+-]+@[\w.-]+\.\w{2,}",
        # Korean name followed by phone (02-XXXX-XXXX style)
        r"([가-힣]{2,4})\s*\n?\s*\(?\d{2,3}\)?[\s.-]*\d{3,4}[\s.-]*\d{4}",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            if 2 <= len(name) <= 4:
                return name

    return None


def extract_sector_from_pdf_text(text: str | None) -> str | None:
    """Extract sector/industry classification from PDF text.

    Looks for common Korean securities report sector labels.
    """
    if not text:
        return None

    patterns = [
        # "업종: 반도체" or "업종 : IT"
        r"업종\s*[:：]\s*([가-힣A-Za-z0-9/&·]+(?:[ \t]+[가-힣A-Za-z0-9/&·]+)*)",
        # "섹터: 자동차" or "Sector: Automotive"
        r"(?:섹터|Sector)\s*[:：]\s*([가-힣A-Za-z0-9/&·]+(?:[ \t]+[가-힣A-Za-z0-9/&·]+)*)",
        # "Industry: 반도체"
        r"Industry\s*[:：]\s*([가-힣A-Za-z0-9/&·]+(?:[ \t]+[가-힣A-Za-z0-9/&·]+)*)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            sector = match.group(1).strip()
            if sector:
                return sector

    return None
