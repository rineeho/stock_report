"""네이버 금융 테마별 시세 크롤러 → 테마-종목 매핑 JSON 생성."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import structlog
from bs4 import BeautifulSoup

from src.utils.http import RateLimitedClient
from src.utils.timezone import today_kst

logger = structlog.get_logger()

SITE_ID = "naver_theme"
THEME_LIST_URL = "https://finance.naver.com/sise/theme.naver"
THEME_RPS = 2.0


async def scrape_theme_list(client: RateLimitedClient) -> list[dict[str, str]]:
    """테마 목록 페이지 전체 크롤링 (페이지네이션 포함).

    Returns:
        [{"name": "2차전지(생산)", "url": "/sise/sise_group_detail.naver?type=theme&no=..."}, ...]
    """
    themes: list[dict[str, str]] = []
    page = 1

    while True:
        url = f"{THEME_LIST_URL}?page={page}"
        logger.info("scrape_theme_list_page", page=page, url=url)

        try:
            response = await client.get(url, site_id=SITE_ID)
        except Exception as exc:
            logger.warning("scrape_theme_list_error", page=page, error=str(exc))
            break

        soup = BeautifulSoup(response.text, "lxml")
        table = soup.select_one("table.type_1")
        if not table:
            break

        rows = table.select("tr")
        found_on_page = 0
        for row in rows:
            name_cell = row.select_one('td a[href*="type=theme"]')
            if not name_cell:
                continue
            theme_name = name_cell.get_text(strip=True)
            theme_href = name_cell.get("href", "")
            if theme_name and theme_href:
                themes.append({"name": theme_name, "url": theme_href})
                found_on_page += 1

        if found_on_page == 0:
            break

        # 다음 페이지 존재 여부 확인
        paging = soup.select_one("table.Nnavi")
        if not paging:
            break
        next_link = paging.select_one(f'a[href*="page={page + 1}"]')
        if not next_link:
            break

        page += 1

    logger.info("scrape_theme_list_done", total_themes=len(themes))
    return themes


async def scrape_theme_detail(
    client: RateLimitedClient, theme_url: str
) -> list[dict[str, str]]:
    """테마 상세 페이지에서 종목 리스트 추출.

    Args:
        client: HTTP client.
        theme_url: 상대 또는 절대 URL.

    Returns:
        [{"name": "삼성SDI", "ticker": "006400"}, ...]
    """
    if theme_url.startswith("/"):
        full_url = f"https://finance.naver.com{theme_url}"
    else:
        full_url = theme_url

    stocks: list[dict[str, str]] = []

    try:
        response = await client.get(full_url, site_id=SITE_ID)
    except Exception as exc:
        logger.warning("scrape_theme_detail_error", url=full_url, error=str(exc))
        return stocks

    soup = BeautifulSoup(response.text, "lxml")
    table = soup.select_one("table.type_5")
    if not table:
        # 일부 테마 상세 페이지는 type_1 테이블 사용
        table = soup.select_one("table.type_1")
    if not table:
        return stocks

    for row in table.select("tr"):
        name_link = row.select_one("td.name a[href*='main.naver?code=']")
        if not name_link:
            continue

        stock_name = name_link.get_text(strip=True)
        href = name_link.get("href", "")

        # code=XXXXXX 파라미터에서 티커 추출
        ticker = _extract_ticker(href)
        if stock_name and ticker:
            stocks.append({"name": stock_name, "ticker": ticker})

    return stocks


def _extract_ticker(href: str) -> str:
    """URL에서 code= 파라미터로 티커코드 추출."""
    # 정규식 방식
    match = re.search(r"code=(\d{6})", href)
    if match:
        return match.group(1)
    # urlparse 방식 fallback
    parsed = urlparse(href)
    qs = parse_qs(parsed.query)
    codes = qs.get("code", [])
    if codes and re.match(r"^\d{6}$", codes[0]):
        return codes[0]
    return ""


async def build_theme_mapping(client: RateLimitedClient) -> dict[str, Any]:
    """전체 실행: 테마 목록 → 상세 순회 → 매핑 dict 생성.

    Returns:
        완성된 매핑 dict (JSON으로 저장 가능).
    """
    themes_list = await scrape_theme_list(client)

    themes: dict[str, list[str]] = {}  # theme_name → [ticker, ...]
    stock_to_themes: dict[str, list[str]] = {}  # stock_name → [theme, ...]
    ticker_to_themes: dict[str, list[str]] = {}  # ticker → [theme, ...]
    ticker_to_name: dict[str, str] = {}  # ticker → stock_name

    for i, theme_info in enumerate(themes_list):
        theme_name = theme_info["name"]
        theme_url = theme_info["url"]

        logger.info(
            "scrape_theme_detail_progress",
            current=i + 1,
            total=len(themes_list),
            theme=theme_name,
        )

        stocks = await scrape_theme_detail(client, theme_url)
        tickers_in_theme: list[str] = []

        for stock in stocks:
            ticker = stock["ticker"]
            name = stock["name"]
            tickers_in_theme.append(ticker)

            # stock_to_themes
            if name not in stock_to_themes:
                stock_to_themes[name] = []
            if theme_name not in stock_to_themes[name]:
                stock_to_themes[name].append(theme_name)

            # ticker_to_themes
            if ticker not in ticker_to_themes:
                ticker_to_themes[ticker] = []
            if theme_name not in ticker_to_themes[ticker]:
                ticker_to_themes[ticker].append(theme_name)

            # ticker_to_name (latest wins)
            ticker_to_name[ticker] = name

        themes[theme_name] = tickers_in_theme

    mapping = {
        "meta": {
            "updated": today_kst().isoformat(),
            "theme_count": len(themes),
            "stock_count": len(ticker_to_name),
        },
        "themes": themes,
        "stock_to_themes": stock_to_themes,
        "ticker_to_themes": ticker_to_themes,
        "ticker_to_name": ticker_to_name,
    }

    logger.info(
        "build_theme_mapping_done",
        theme_count=len(themes),
        stock_count=len(ticker_to_name),
    )
    return mapping


def save_mapping(mapping: dict[str, Any], path: Path) -> None:
    """매핑 dict를 JSON 파일로 저장."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    logger.info("save_mapping_done", path=str(path))


def load_mapping(path: Path) -> dict[str, Any] | None:
    """저장된 매핑 JSON 로드. 파일 없으면 None."""
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)
