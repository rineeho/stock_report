"""Static site builder: generates a GitHub Pages compatible site from pipeline output."""

from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

import structlog

logger = structlog.get_logger()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def build_static_site(
    data_dir: Path | None = None,
    output_dir: Path | None = None,
) -> Path:
    """Build a static site from daily_report.json files.

    Args:
        data_dir: Directory containing date folders with daily_report.json files.
                  Can be data/output/ (local) or a gh-pages data dir.
        output_dir: Output directory for the static site (default: _site/).

    Returns:
        Path to the output directory.
    """
    if data_dir is None:
        data_dir = PROJECT_ROOT / "data" / "output"
    if output_dir is None:
        output_dir = PROJECT_ROOT / "_site"

    output_dir.mkdir(parents=True, exist_ok=True)
    site_data_dir = output_dir / "data"
    site_data_dir.mkdir(parents=True, exist_ok=True)

    # Find all dates with daily_report.json
    dates: list[str] = []

    if data_dir.exists():
        for child in sorted(data_dir.iterdir(), reverse=True):
            if not child.is_dir():
                continue

            # Check if this looks like a date directory
            try:
                date.fromisoformat(child.name)
            except ValueError:
                continue

            # Look for daily_report.json (local output) or treat as pre-copied .json
            json_file = child / "daily_report.json"
            if json_file.exists():
                shutil.copy2(json_file, site_data_dir / f"{child.name}.json")
                dates.append(child.name)
                logger.info("copied_daily_json", date=child.name)

    # Also check for already-copied .json files in data_dir (gh-pages data format)
    for json_file in sorted(data_dir.glob("*.json"), reverse=True):
        date_str = json_file.stem
        try:
            date.fromisoformat(date_str)
        except ValueError:
            continue
        if date_str not in dates:
            shutil.copy2(json_file, site_data_dir / f"{date_str}.json")
            dates.append(date_str)
            logger.info("copied_daily_json", date=date_str, source="flat")

    dates.sort(reverse=True)

    # Write dates.json
    dates_json = output_dir / "dates.json"
    with open(dates_json, "w", encoding="utf-8") as f:
        json.dump({"dates": dates}, f, ensure_ascii=False)
    logger.info("wrote_dates_json", count=len(dates))

    # Copy static frontend
    static_html = Path(__file__).parent / "static" / "index-static.html"
    shutil.copy2(static_html, output_dir / "index.html")
    logger.info("copied_index_html")

    logger.info("static_site_built", output_dir=str(output_dir), dates=len(dates))
    return output_dir
