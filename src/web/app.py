"""FastAPI application for the report dashboard."""

from __future__ import annotations

from collections import Counter
from datetime import date as date_type
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

from src.web.data_loader import (
    DATA_OUTPUT_DIR,
    extract_ticker_consensus,
    list_available_dates,
    load_daily_result,
)


def create_app(data_dir: Path = DATA_OUTPUT_DIR) -> FastAPI:
    """Create the FastAPI dashboard application."""
    app = FastAPI(title="Report Dashboard", version="0.1.0")

    @app.get("/api/dates")
    def get_dates():
        return {"dates": list_available_dates(data_dir)}

    @app.get("/api/reports/{target_date}/summary")
    def get_summary(target_date: str):
        result = load_daily_result(target_date, data_dir)
        if result is None:
            raise HTTPException(404, f"No report for {target_date}")
        return {
            "target_date": result.target_date.isoformat(),
            "total_discovered": result.total_discovered,
            "total_fetched": result.total_fetched,
            "total_validated": result.total_validated,
            "total_unverified": result.total_unverified,
            "total_deduplicated": result.total_deduplicated,
            "report_count": len(result.reports),
            "summary_count": len(result.summaries),
            "pipeline_stats": result.pipeline_stats.model_dump(mode="json"),
            "brokerage_counts": {k: len(v) for k, v in result.classifications.by_brokerage.items()},
            "ticker_counts": {k: len(v) for k, v in result.classifications.by_ticker.items()},
            "theme_counts": {k: len(v) for k, v in result.classifications.by_theme.items()},
            "stock_names": {
                r.ticker: r.stock_name
                for r in result.reports
                if r.ticker and r.stock_name
            },
        }

    @app.get("/api/reports/{target_date}/list")
    def get_report_list(
        target_date: str,
        brokerage: str | None = Query(None),
        ticker: str | None = Query(None),
        theme: str | None = Query(None),
    ):
        result = load_daily_result(target_date, data_dir)
        if result is None:
            raise HTTPException(404, f"No report for {target_date}")

        summary_map = {s.canonical_id: s for s in result.summaries}

        if brokerage and brokerage in result.classifications.by_brokerage:
            allowed_ids = set(result.classifications.by_brokerage[brokerage])
        elif ticker and ticker in result.classifications.by_ticker:
            allowed_ids = set(result.classifications.by_ticker[ticker])
        elif theme and theme in result.classifications.by_theme:
            allowed_ids = set(result.classifications.by_theme[theme])
        else:
            allowed_ids = None

        items = []
        for report in result.reports:
            if allowed_ids is not None and report.canonical_id not in allowed_ids:
                continue
            entry = report.model_dump(mode="json")
            sm = summary_map.get(report.canonical_id)
            entry["summary"] = sm.model_dump(mode="json") if sm else None
            items.append(entry)

        return {"target_date": target_date, "count": len(items), "reports": items}

    @app.get("/api/reports/{target_date}/detail/{canonical_id}")
    def get_report_detail(target_date: str, canonical_id: str):
        result = load_daily_result(target_date, data_dir)
        if result is None:
            raise HTTPException(404, f"No report for {target_date}")

        report = next((r for r in result.reports if r.canonical_id == canonical_id), None)
        if report is None:
            raise HTTPException(404, f"Report {canonical_id} not found")

        summary = next((s for s in result.summaries if s.canonical_id == canonical_id), None)
        data = report.model_dump(mode="json")
        data["summary"] = summary.model_dump(mode="json") if summary else None
        return data

    # --- Consensus Changes (Home page top) ---
    @app.get("/api/reports/{target_date}/consensus-changes")
    def get_consensus_changes(target_date: str):
        result = load_daily_result(target_date, data_dir)
        if result is None:
            raise HTTPException(404, f"No report for {target_date}")

        dates = list_available_dates(data_dir)
        prev_date = next((d for d in dates if d < target_date), None)

        today_data = extract_ticker_consensus(result)
        prev_data: dict[str, dict] = {}
        if prev_date:
            prev_result = load_daily_result(prev_date, data_dir)
            if prev_result:
                prev_data = extract_ticker_consensus(prev_result)

        changes: list[dict] = []
        for ticker, td in today_data.items():
            if not td["prices"] and not td["ratings"]:
                continue

            pd = prev_data.get(ticker)
            curr_avg = sum(td["prices"]) / len(td["prices"]) if td["prices"] else None
            prev_avg = sum(pd["prices"]) / len(pd["prices"]) if pd and pd["prices"] else None

            direction = "neutral"
            description = ""
            sort_key = 0.0

            if pd is None:
                has_buy = any("매수" in r or "buy" in r.lower() for r in td["ratings"])
                direction = "up"
                description = "신규 매수" if has_buy else "신규 커버리지"
                sort_key = 50.0
            elif curr_avg is not None and prev_avg is not None and prev_avg > 0:
                pct = (curr_avg - prev_avg) / prev_avg * 100
                if abs(pct) >= 1:
                    direction = "up" if pct > 0 else "down"
                    sign = "+" if pct > 0 else ""
                    description = f"목표주가 {sign}{pct:.0f}%"
                    sort_key = abs(pct)
                else:
                    today_dom = Counter(td["ratings"]).most_common(1)[0][0] if td["ratings"] else None
                    prev_dom = Counter(pd["ratings"]).most_common(1)[0][0] if pd and pd["ratings"] else None
                    if today_dom and today_dom != prev_dom:
                        direction = "up" if "매수" in today_dom else "down"
                        description = f"의견 변경 → {today_dom}"
                        sort_key = 10.0
                    else:
                        continue
            else:
                today_dom = Counter(td["ratings"]).most_common(1)[0][0] if td["ratings"] else None
                prev_dom = Counter(pd["ratings"]).most_common(1)[0][0] if pd and pd["ratings"] else None
                if today_dom and today_dom != prev_dom:
                    direction = "up" if "매수" in today_dom else "down"
                    description = f"의견 변경 → {today_dom}"
                    sort_key = 10.0
                else:
                    continue

            changes.append({
                "ticker": ticker,
                "stock_name": td["stock_name"],
                "direction": direction,
                "description": description,
                "curr_target_price": curr_avg,
                "prev_target_price": prev_avg,
                "_sort": sort_key,
            })

        changes.sort(key=lambda c: c["_sort"], reverse=True)
        for c in changes:
            del c["_sort"]

        return {
            "target_date": target_date,
            "prev_date": prev_date,
            "changes": changes[:5],
        }

    # --- Ticker History (Detail page top) ---
    @app.get("/api/reports/{target_date}/ticker-history/{ticker}")
    def get_ticker_history(target_date: str, ticker: str):
        dates = list_available_dates(data_dir)
        relevant_dates = [d for d in dates if d <= target_date][:30]

        try:
            target_dt = date_type.fromisoformat(target_date)
        except ValueError:
            raise HTTPException(400, "Invalid date format")

        history: list[dict] = []
        total_7d = 0
        total_30d = 0
        stock_name = ticker

        for d in relevant_dates:
            d_result = load_daily_result(d, data_dir)
            if d_result is None:
                continue
            td = extract_ticker_consensus(d_result).get(ticker)
            if td is None:
                continue

            stock_name = td["stock_name"]
            d_dt = date_type.fromisoformat(d)
            diff = (target_dt - d_dt).days

            if diff < 7:
                total_7d += td["count"]
            if diff < 30:
                total_30d += td["count"]

            avg_price = sum(td["prices"]) / len(td["prices"]) if td["prices"] else None
            rating_counts = dict(Counter(td["ratings"]))

            history.append({
                "date": d,
                "avg_target_price": avg_price,
                "rating_counts": rating_counts,
                "report_count": td["count"],
            })

        return {
            "ticker": ticker,
            "stock_name": stock_name,
            "history": history,
            "report_counts": {"last_7_days": total_7d, "last_30_days": total_30d},
        }

    # --- Theme Summary (Dashboard theme section) ---
    @app.get("/api/reports/{target_date}/theme-summary")
    def get_theme_summary(target_date: str):
        result = load_daily_result(target_date, data_dir)
        if result is None:
            raise HTTPException(404, f"No report for {target_date}")

        dates = list_available_dates(data_dir)
        prev_date = next((d for d in dates if d < target_date), None)

        today_consensus = extract_ticker_consensus(result)
        prev_consensus: dict[str, dict] = {}
        prev_theme_counts: dict[str, int] = {}
        if prev_date:
            prev_result = load_daily_result(prev_date, data_dir)
            if prev_result:
                prev_consensus = extract_ticker_consensus(prev_result)
                prev_theme_counts = {
                    k: len(v) for k, v in prev_result.classifications.by_theme.items()
                }

        cid_to_ticker = {r.canonical_id: r.ticker for r in result.reports if r.ticker}

        themes: list[dict] = []
        for theme_name, cids in result.classifications.by_theme.items():
            report_count = len(cids)
            theme_tickers = {cid_to_ticker[c] for c in cids if c in cid_to_ticker}

            target_up = 0
            target_down = 0
            new_buy = 0

            for tk in theme_tickers:
                td = today_consensus.get(tk)
                pd = prev_consensus.get(tk)
                if td is None:
                    continue

                curr_avg = sum(td["prices"]) / len(td["prices"]) if td["prices"] else None
                prev_avg = sum(pd["prices"]) / len(pd["prices"]) if pd and pd["prices"] else None

                if pd is None:
                    if any("매수" in r or "buy" in r.lower() for r in td["ratings"]):
                        new_buy += 1
                elif curr_avg and prev_avg and prev_avg > 0:
                    pct = (curr_avg - prev_avg) / prev_avg * 100
                    if pct >= 1:
                        target_up += 1
                    elif pct <= -1:
                        target_down += 1

                if pd is not None:
                    prev_buy = any("매수" in r or "buy" in r.lower() for r in (pd.get("ratings") or []))
                    curr_buy = any("매수" in r or "buy" in r.lower() for r in td["ratings"])
                    if curr_buy and not prev_buy:
                        new_buy += 1

            prev_count = prev_theme_counts.get(theme_name, 0)
            count_diff = report_count - prev_count

            change_items: list[str] = []
            if target_up:
                change_items.append(f"목표주가 상향 {target_up}건")
            if target_down:
                change_items.append(f"목표주가 하향 {target_down}건")
            if new_buy:
                change_items.append(f"신규 매수 {new_buy}건")
            if count_diff > 0:
                change_items.append(f"리포트 증가 +{count_diff}")
            elif count_diff < 0:
                change_items.append(f"리포트 감소 {count_diff}")
            if not change_items:
                change_items.append("변화 없음")

            is_hot = target_up > 0 or new_buy > 0 or count_diff > 2

            themes.append({
                "theme": theme_name,
                "report_count": report_count,
                "is_hot": is_hot,
                "changes": change_items,
            })

        themes.sort(key=lambda t: (t["is_hot"], t["report_count"]), reverse=True)

        return {
            "target_date": target_date,
            "prev_date": prev_date,
            "themes": themes,
        }

    # Serve frontend
    static_dir = Path(__file__).parent / "static"

    @app.get("/", response_class=HTMLResponse)
    def serve_index():
        index_path = static_dir / "index.html"
        if not index_path.exists():
            raise HTTPException(500, "index.html not found")
        return index_path.read_text(encoding="utf-8")

    return app
