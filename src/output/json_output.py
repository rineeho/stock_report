"""JSON output generator for NormalizedReport list and DailyResult."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any


def write_normalized_reports(reports: list[Any], output_dir: str | Path, target_date: date) -> Path:
    """Write normalized report list to data/output/{date}/validated_reports.json.

    Args:
        reports: List of NormalizedReport pydantic objects.
        output_dir: Output directory (will be created if needed).
        target_date: Target date for folder naming.

    Returns:
        Path to written file.
    """
    out_dir = Path(output_dir) / target_date.isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "validated_reports.json"

    data = [
        r.model_dump(mode="json") if hasattr(r, "model_dump") else r
        for r in reports
    ]

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {"target_date": target_date.isoformat(), "count": len(data), "reports": data},
            f,
            ensure_ascii=False,
            indent=2,
        )

    return out_path


def write_daily_result(daily_result: Any, output_dir: str | Path) -> Path:
    """Write DailyResult to data/output/{date}/daily_report.json.

    Args:
        daily_result: DailyResult pydantic object.
        output_dir: Output directory (will be created if needed).

    Returns:
        Path to written file.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "daily_report.json"

    data = (
        daily_result.model_dump(mode="json")
        if hasattr(daily_result, "model_dump")
        else daily_result
    )

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return out_path
