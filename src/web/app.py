"""FastAPI application for the report dashboard."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

from src.web.data_loader import DATA_OUTPUT_DIR, list_available_dates, load_daily_result


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

    # Serve frontend
    static_dir = Path(__file__).parent / "static"

    @app.get("/", response_class=HTMLResponse)
    def serve_index():
        index_path = static_dir / "index.html"
        if not index_path.exists():
            raise HTTPException(500, "index.html not found")
        return index_path.read_text(encoding="utf-8")

    return app
