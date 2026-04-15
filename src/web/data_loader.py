"""Data loader: read daily_report.json files from data/output/ directory."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from src.schemas.daily_result import DailyResult

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_OUTPUT_DIR = PROJECT_ROOT / "data" / "output"


def list_available_dates(data_dir: Path = DATA_OUTPUT_DIR) -> list[str]:
    """Return available report dates (YYYY-MM-DD), newest first."""
    dates: list[str] = []
    if not data_dir.exists():
        return dates
    for child in data_dir.iterdir():
        if child.is_dir() and (child / "daily_report.json").exists():
            try:
                date.fromisoformat(child.name)
                dates.append(child.name)
            except ValueError:
                continue
    return sorted(dates, reverse=True)


def load_daily_result(target_date: str, data_dir: Path = DATA_OUTPUT_DIR) -> DailyResult | None:
    """Load a single day's daily_report.json as DailyResult."""
    json_path = data_dir / target_date / "daily_report.json"
    if not json_path.exists():
        return None
    with open(json_path, encoding="utf-8") as f:
        raw = json.load(f)
    return DailyResult(**raw)
