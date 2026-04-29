"""naver_research site parser.

Discovers reports from: https://finance.naver.com/research/company_list.naver
Parses individual report pages.
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

BASE = "https://finance.naver.com"
LIST_URL = "https://finance.naver.com/research/company_list.naver"


class NaverResearchParser(BaseSiteParser):
    """Parser for 네이버 리서치 company report list."""

    @property
    def site_id(self) -> str:
        return "naver_research"

    def get_page_url(self, base_url: str, page: int, target_date: date | None = None) -> str | None:
        return f"{LIST_URL}?&page={page}"

    async def discover_reports(self, html_content: str, base_url: str) -> list[RawReport]:
        """Parse company_list.naver HTML and return one RawReport per row.

        Each row carries metadata hints (date, ticker, brokerage, title)
        stored in metadata_hint so they survive the fetch stage.
        """
        soup = BeautifulSoup(html_content, "lxml")
        table = soup.find("table", class_="type_1")
        if not table:
            return []

        reports: list[RawReport] = []
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 5:
                continue

            stock_cell = cells[0]
            title_cell = cells[1]
            brokerage_cell = cells[2]
            date_cell = cells[4]

            title_link = title_cell.find("a")
            if not title_link:
                continue

            href = title_link.get("href", "")
            report_url = urljoin(base_url, href) if href else ""
            if not report_url:
                continue
            # Remove &page= parameter from report URL (inherited from list page base_url)
            report_url = re.sub(r"[&?]page=\d+", "", report_url)

            # Embed list-page metadata as a hint
            stock_link = stock_cell.find("a")
            stock_name = stock_link.get_text(strip=True) if stock_link else ""
            ticker = ""
            if stock_link:
                m = re.search(r"code=(\d+)", stock_link.get("href", ""))
                if m:
                    ticker = m.group(1)

            brokerage = brokerage_cell.get_text(strip=True)
            date_hint = date_cell.get_text(strip=True)
            title_text = title_link.get_text(strip=True)

            # Attach PDF link if present
            pdf_cell = cells[3]
            pdf_link = pdf_cell.find("a")
            pdf_url = urljoin(base_url, pdf_link.get("href", "")) if pdf_link else ""

            hint = json.dumps(
                {
                    "title": title_text,
                    "brokerage": brokerage,
                    "stock_name": stock_name,
                    "ticker": ticker,
                    "date_hint": date_hint,
                    "pdf_url": pdf_url,
                },
                ensure_ascii=False,
            )

            reports.append(
                RawReport(
                    site_id=self.site_id,
                    discovered_url=report_url,
                    content_type=ContentType.HTML,
                    metadata_hint=hint,
                    fetch_status=FetchStatus.SKIPPED,
                )
            )

        return reports

    async def parse_report(self, raw: RawReport) -> ParsedReport:
        """Extract metadata from a naver_research report page HTML.

        Uses metadata_hint from discover step, supplemented by HTML parsing.
        When PDF text is available (via fetch stage), extracts analyst and sector.
        """
        errors: list[str] = []

        # --- Load hint (from discover step, preserved through fetch) ---
        hint = self._load_hint(raw.metadata_hint)

        title: str | None = hint.get("title") if hint else None
        brokerage: str | None = hint.get("brokerage") if hint else None
        stock_name: str | None = hint.get("stock_name") if hint else None
        ticker: str | None = hint.get("ticker") if hint else None

        published_date = None
        published_date_source = None
        analyst: str | None = None
        sector: str | None = None
        body_text: str | None = None

        # --- Full HTML parsing (when raw_content is full HTML) ---
        if raw.raw_content and raw.raw_content.strip().startswith("<"):
            soup = BeautifulSoup(raw.raw_content, "lxml")

            # Title: try real page structure, then fallback selectors
            if not title:
                sbj = soup.select_one("th.view_sbj")
                if sbj:
                    for child in sbj.children:
                        if isinstance(child, str) and child.strip():
                            title = child.strip()
                            break
            if not title:
                title_el = soup.select_one(".report_title, h2")
                title = title_el.get_text(strip=True) if title_el else None

            # Brokerage: try p.source in real page, then fallback
            if not brokerage:
                source_el = soup.select_one("th.view_sbj p.source")
                if source_el:
                    source_text = source_el.get_text(separator="|", strip=True)
                    parts = source_text.split("|")
                    if parts:
                        brokerage = parts[0].strip()
            if not brokerage:
                brok_el = soup.select_one(".brokerage")
                brokerage = brok_el.get_text(strip=True) if brok_el else None

            # Analyst
            analyst_el = soup.select_one(".analyst")
            analyst = analyst_el.get_text(strip=True) if analyst_el else None

            # Stock name
            if not stock_name:
                stock_el = soup.select_one("th.view_sbj span em")
                stock_name = stock_el.get_text(strip=True) if stock_el else None
            if not stock_name:
                comp_el = soup.select_one(".company_name")
                stock_name = comp_el.get_text(strip=True) if comp_el else None

            # Ticker
            if not ticker:
                code_el = soup.select_one(".stock_code")
                ticker = code_el.get_text(strip=True) if code_el else None

            # Date: multi-strategy
            published_date, published_date_source = self.extract_date_multi_strategy(
                raw.raw_content
            )

            # Fallback: date from p.source or .date element
            if not published_date:
                source_el = soup.select_one("th.view_sbj p.source")
                if source_el:
                    source_text = source_el.get_text(separator="|", strip=True)
                    parts = source_text.split("|")
                    for part in parts:
                        d = parse_date_kst(part.strip())
                        if d:
                            published_date = d
                            break
            if not published_date:
                date_el = soup.select_one(".date")
                if date_el:
                    published_date = parse_date_kst(date_el.get_text(strip=True))

            # Body text: from HTML page
            body_el = soup.select_one("td.view_cnt, .view_text, .research_body")
            body_text = body_el.get_text(separator="\n", strip=True) if body_el else None

        # --- Date from hint (date_hint field) ---
        if published_date is None and hint and hint.get("date_hint"):
            published_date = parse_date_kst(hint["date_hint"])

        # --- PDF text analysis: analyst, sector, market_type extraction ---
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
            # Always prefer PDF full text over HTML snippet
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

        # PDF URL from hint
        pdf_url: str | None = hint.get("pdf_url") if hint else None

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
            pdf_url=pdf_url if pdf_url else None,
        )

    def _load_hint(self, content: str | None) -> dict | None:
        """Load list-page metadata hint from JSON string."""
        if not content:
            return None
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                return data
        except (ValueError, TypeError):
            pass
        return None


# Register parser
register("naver_research", NaverResearchParser)
