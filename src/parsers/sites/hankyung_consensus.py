"""hankyung_consensus site parser.

Discovers reports from: https://consensus.hankyung.com/analysis/list
Parses individual report pages for 한경컨센서스 기업분석.

Listing page columns:
  작성일 | 제목 | 적정가격 | 투자의견 | 작성자 | 제공출처

Each report title links to a PDF download URL (/analysis/downpdf?report_idx=...).
FetchAgent handles the PDF response directly (ContentType.PDF branch).
"""

from __future__ import annotations

import json
import re
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.parsers.base import BaseSiteParser
from src.parsers.registry import register
from src.schemas.report import (
    ContentType,
    FetchStatus,
    ParsedReport,
    ParseStatus,
    RawReport,
)
from src.utils.timezone import parse_date_kst

BASE = "https://consensus.hankyung.com"
LIST_PATH = "/analysis/list"


class HankyungConsensusParser(BaseSiteParser):
    """Parser for 한경컨센서스 기업분석 리포트."""

    @property
    def site_id(self) -> str:
        return "hankyung_consensus"

    def get_page_url(self, base_url: str, page: int, target_date: date | None = None) -> str | None:
        date_str = target_date.isoformat() if target_date else ""
        return (
            f"{BASE}{LIST_PATH}?skinType=business"
            f"&sdate={date_str}&edate={date_str}&now_page={page}"
        )

    async def discover_reports(self, html_content: str, base_url: str) -> list[RawReport]:
        """Parse consensus list page and return one RawReport per row.

        Actual HTML structure:
          <div class="table_style01"><table><tbody><tr>...
        Columns (9): 작성일 | 제목 | 적정가격 | 투자의견 | 작성자 | 제공출처 | 기업정보 | 차트 | 첨부파일
        Title link points to PDF download (/analysis/downpdf?report_idx=...).
        """
        soup = BeautifulSoup(html_content, "lxml")
        wrapper = soup.find("div", class_="table_style01")
        table = wrapper.find("table") if wrapper else soup.find("table", class_="tb_type01")
        if not table:
            return []

        tbody = table.find("tbody")
        reports: list[RawReport] = []
        rows = tbody.find_all("tr") if tbody else table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 6:
                continue

            date_cell = cells[0]
            title_cell = cells[1]
            price_cell = cells[2]
            opinion_cell = cells[3]
            analyst_cell = cells[4]
            broker_cell = cells[5]

            # Title link → PDF download URL
            title_link = title_cell.find("a")
            if not title_link:
                continue

            href = title_link.get("href", "")
            pdf_url = urljoin(BASE, href) if href else ""
            if not pdf_url:
                continue

            title_text = title_link.get_text(strip=True)

            # Stock name and ticker from title: "[종목명(코드)] 제목" or "종목명(코드) 제목"
            stock_name = ""
            ticker = ""
            m = re.match(r"\[?([^(\[]+?)\((\d{6})\)\]?\s*(.*)", title_text)
            if m:
                stock_name = m.group(1).strip()
                ticker = m.group(2)
                title_text = m.group(3).strip() if m.group(3).strip() else title_text

            date_hint = date_cell.get_text(strip=True)
            analyst = analyst_cell.get_text(strip=True) or None
            brokerage = broker_cell.get_text(strip=True)
            target_price = price_cell.get_text(strip=True) or None
            opinion = opinion_cell.get_text(strip=True) or None

            hint = json.dumps(
                {
                    "title": title_text,
                    "brokerage": brokerage,
                    "stock_name": stock_name,
                    "ticker": ticker,
                    "date_hint": date_hint,
                    "analyst": analyst,
                    "target_price": target_price,
                    "opinion": opinion,
                    "pdf_url": pdf_url,
                },
                ensure_ascii=False,
            )

            reports.append(
                RawReport(
                    site_id=self.site_id,
                    discovered_url=pdf_url,
                    content_type=ContentType.PDF,
                    metadata_hint=hint,
                    fetch_status=FetchStatus.SKIPPED,
                )
            )

        return reports

    async def parse_report(self, raw: RawReport) -> ParsedReport:
        """Extract metadata from a hankyung_consensus report.

        Sources (checked in order, earlier wins for each field):
        1. metadata_hint from discover (listing-page metadata)
        2. raw_content HTML (if the fetched page is HTML)
        3. pdf_text from FetchAgent (analyst/sector/body fallback)
        """
        errors: list[str] = []

        hint = self._load_hint(raw.metadata_hint)

        title: str | None = hint.get("title") if hint else None
        brokerage: str | None = hint.get("brokerage") if hint else None
        stock_name: str | None = hint.get("stock_name") if hint else None
        ticker: str | None = hint.get("ticker") if hint else None
        analyst: str | None = hint.get("analyst") if hint else None
        sector: str | None = None
        body_text: str | None = None
        pdf_url: str | None = hint.get("pdf_url") if hint else None

        published_date = None
        published_date_source = None

        # Date from hint
        if hint and hint.get("date_hint"):
            published_date = parse_date_kst(hint["date_hint"])

        # Full HTML parsing (when raw_content is HTML)
        if raw.raw_content and raw.raw_content.strip().startswith("<"):
            soup = BeautifulSoup(raw.raw_content, "lxml")

            if not title:
                title_el = soup.select_one(".report_title, h2")
                title = title_el.get_text(strip=True) if title_el else None

            if not brokerage:
                brok_el = soup.select_one(".broker_name")
                brokerage = brok_el.get_text(strip=True) if brok_el else None

            if not analyst:
                analyst_el = soup.select_one(".analyst_name")
                analyst = analyst_el.get_text(strip=True) if analyst_el else None

            if not stock_name:
                name_el = soup.select_one(".stock_name")
                stock_name = name_el.get_text(strip=True) if name_el else None

            if not ticker:
                code_el = soup.select_one(".stock_code")
                ticker = code_el.get_text(strip=True) if code_el else None

            if not published_date:
                published_date, published_date_source = self.extract_date_multi_strategy(
                    raw.raw_content
                )

            if not published_date:
                date_el = soup.select_one(".date")
                if date_el:
                    published_date = parse_date_kst(date_el.get_text(strip=True))

            body_el = soup.select_one(".report_body")
            if body_el:
                body_text = body_el.get_text(separator="\n", strip=True)

        # PDF text analysis: supplement analyst/sector/market_type, provide body
        market_type: str | None = None
        is_ai_generated = False
        if raw.pdf_text:
            from src.parsers.pdf_extractor import (
                detect_ai_generated,
                extract_analyst_from_pdf_text,
                extract_market_type_from_pdf_text,
                extract_sector_from_pdf_text,
            )

            is_ai_generated = detect_ai_generated(raw.pdf_text)
            if not analyst:
                analyst = extract_analyst_from_pdf_text(raw.pdf_text)
            if not sector:
                sector = extract_sector_from_pdf_text(raw.pdf_text)
            market_type = extract_market_type_from_pdf_text(raw.pdf_text)
            if not body_text or len(body_text) < 100:
                body_text = raw.pdf_text

        # Required fields check
        if not title:
            errors.append("title_missing")
        if not brokerage:
            errors.append("brokerage_missing")
        if published_date is None:
            errors.append("published_date_missing")

        status = ParseStatus.SUCCESS if not errors else (
            ParseStatus.PARTIAL if title else ParseStatus.FAILED
        )

        return ParsedReport(
            raw_id=raw.raw_id,
            title=title,
            published_date=published_date,
            published_date_source=published_date_source,
            brokerage=brokerage,
            analyst=analyst,
            ticker=ticker,
            stock_name=stock_name,
            sector=sector,
            market_type=market_type,
            is_ai_generated=is_ai_generated,
            body_text=body_text,
            source_url=raw.discovered_url,
            parse_status=status,
            parse_errors=errors,
            pdf_url=pdf_url,
        )

    def _load_hint(self, content: str | None) -> dict | None:
        if not content:
            return None
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                return data
        except (ValueError, TypeError):
            pass
        return None


register("hankyung_consensus", HankyungConsensusParser)
