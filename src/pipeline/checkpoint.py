"""Checkpoint manager: save/load JSON per stage to data/cache/{target_date}/."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import structlog

from src.schemas.pipeline import StageEnvelope

logger = structlog.get_logger()

# Stage name to file number mapping
STAGE_FILE_MAP = {
    "discover": "01_discovered",
    "fetch": "02_fetched",
    "parse": "03_parsed",
    "validate": "04_validated",
    "normalize": "05_normalized",
    "deduplicate": "06_deduplicated",
    "summarize": "07_summarized",
    "classify": "08_classified",
    "aggregate": "09_aggregated",
}


class CheckpointManager:
    """Manages pipeline stage checkpoints as JSON files."""

    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir

    def _stage_path(self, target_date: date, stage: str) -> Path:
        date_str = target_date.isoformat()
        filename = STAGE_FILE_MAP.get(stage, stage)
        return self.cache_dir / date_str / f"{filename}.json"

    def save(self, target_date: date, stage: str, envelope: StageEnvelope) -> Path:
        """Save stage envelope as JSON checkpoint."""
        path = self._stage_path(target_date, stage)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = envelope.model_dump(mode="json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info("checkpoint_saved", stage=stage, path=str(path), items=len(envelope.items))
        return path

    def load(self, target_date: date, stage: str) -> list[Any] | None:
        """Load items from a stage checkpoint. Returns None if not found."""
        path = self._stage_path(target_date, stage)
        if not path.exists():
            return None

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        items = data.get("items", [])
        logger.info("checkpoint_loaded", stage=stage, path=str(path), items=len(items))
        return items

    def exists(self, target_date: date, stage: str) -> bool:
        """Check if a checkpoint exists for the given stage."""
        return self._stage_path(target_date, stage).exists()

    def list_checkpoints(self, target_date: date) -> list[str]:
        """List all checkpoint stages for a given date."""
        date_dir = self.cache_dir / target_date.isoformat()
        if not date_dir.exists():
            return []
        return sorted(p.stem for p in date_dir.glob("*.json"))

    def clear(self, target_date: date) -> int:
        """Clear all checkpoints for a given date. Returns count of deleted files."""
        date_dir = self.cache_dir / target_date.isoformat()
        if not date_dir.exists():
            return 0
        count = 0
        for p in date_dir.glob("*.json"):
            p.unlink()
            count += 1
        if not any(date_dir.iterdir()):
            date_dir.rmdir()
        return count
