"""hankyung_consensus site parser.

Discovers reports from: https://consensus.hankyung.com
Parses individual report pages for 한경컨센서스.
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


class HankyungConsensusParser(BaseSiteParser):
    """Parser for 한경컨센서스 기업분석 리포트."""

    @property
    def site_id(self) -> str:
        return "hankyung_consensus"

    def get_page_url(self, base_url: str, page: int, target_date: date | None = None) -> str | None:
        date_str = target_date.isoformat() if target_date else ""
        return f"{BASE}/analysis/list?sdate={date_str}&edate={date_str}&now_page={page}"

    async def discover_reports(self, html_content: str, base_url: str) -> list[RawReport]:
        """Parse consensus list page and return one RawReport per row."""
        soup = BeautifulSoup(html_content, "lxml")
        table = soup.find("table", class_="tb_type01")
        if not table:
            return []

        reports: list[RawReport] = []
        for row in table.find_all("tr", class_="row"):
            cells = row.find_all("td")
            if len(cells) < 6:
                continue

            date_cell = cells[0]
            stock_cell = cells[1]
            title_cell = cells[2]
            broker_cell = cells[3]

            title_link = title_cell.find("a")
            if not title_link:
                continue

            href = title_link.get("href", "")
            report_url = urljoin(BASE, href) if href else ""
            if not report_url:
                continue

            stock_link = stock_cell.find("a")
            stock_text = stock_link.get_text(strip=True) if stock_link else ""
            # Extract stock_name and ticker from format like "삼성전자(005930)"
            stock_name = ""
            ticker = ""
            m = re.match(r"(.+?)\((\d+)\)", stock_text)
            if m:
                stock_name = m.group(1)
                ticker = m.group(2)

            brokerage = broker_cell.get_text(strip=True)
            date_hint = date_cell.get_text(strip=True)
            title_text = title_link.get_text(strip=True)

            hint = json.dumps(
                {
                    "title": title_text,
                    "brokerage": brokerage,
                    "stock_name": stock_name,
                    "ticker": ticker,
                    "date_hint": date_hint,
                },
                ensure_ascii=False,
            )

            reports.append(
                RawReport(
                    site_id=self.site_id,
                    discovered_url=report_url,
                    content_type=ContentType.HTML,
                    raw_content=hint,
                    fetch_status=FetchStatus.SKIPPED,
                )
            )

        return reports

    async def parse_report(self, raw: RawReport) -> ParsedReport:
        """Extract metadata from a hankyung_consensus report page."""
        errors: list[str] = []

        hint = self._load_hint(raw.raw_content)

        title: str | None = hint.get("title") if hint else None
        brokerage: str | None = hint.get("brokerage") if hint else None
        stock_name: str | None = hint.get("stock_name") if hint else None
        ticker: str | None = hint.get("ticker") if hint else None

        published_date = None
        published_date_source = None
        analyst: str | None = None
        body_text: str | None = None

        # Full HTML parsing
        if raw.raw_content and raw.raw_content.strip().startswith("<"):
            soup = BeautifulSoup(raw.raw_content, "lxml")

            if not title:
                title_el = soup.select_one(".report_title, h2")
                title = title_el.get_text(strip=True) if title_el else None

            if not brokerage:
                brok_el = soup.select_one(".broker_name")
                brokerage = brok_el.get_text(strip=True) if brok_el else None

            analyst_el = soup.select_one(".analyst_name")
            analyst = analyst_el.get_text(strip=True) if analyst_el else None

            if not stock_name:
                name_el = soup.select_one(".stock_name")
                stock_name = name_el.get_text(strip=True) if name_el else None

            if not ticker:
                code_el = soup.select_one(".stock_code")
                ticker = code_el.get_text(strip=True) if code_el else None

            published_date, published_date_source = self.extract_date_multi_strategy(
                raw.raw_content
            )

            if not published_date:
                date_el = soup.select_one(".date")
                if date_el:
                    published_date = parse_date_kst(date_el.get_text(strip=True))

            body_el = soup.select_one(".report_body")
            body_text = body_el.get_text(separator="\n", strip=True) if body_el else None

        # Date from hint
        if published_date is None and hint and hint.get("date_hint"):
            published_date = parse_date_kst(hint["date_hint"])

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
            body_text=body_text,
            source_url=raw.discovered_url,
            parse_status=status,
            parse_errors=errors,
        )

    def _load_hint(self, raw_content: str | None) -> dict | None:
        if not raw_content:
            return None
        try:
            data = json.loads(raw_content)
            if isinstance(data, dict):
                return data
        except (ValueError, TypeError):
            pass
        return None


register("hankyung_consensus", HankyungConsensusParser)
