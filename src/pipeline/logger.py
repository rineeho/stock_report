"""Structured pipeline logger using structlog. JSONL output to data/logs/{target_date}/pipeline.jsonl."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import structlog


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog for the pipeline."""
    import logging

    level_num = logging.getLevelName(log_level.upper())
    if not isinstance(level_num, int):
        level_num = logging.INFO

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if log_level == "DEBUG" else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level_num),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


class PipelineFileLogger:
    """Writes structured log entries to a JSONL file."""

    def __init__(self, logs_dir: Path, target_date: date) -> None:
        self.log_dir = logs_dir / target_date.isoformat()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "pipeline.jsonl"

    def log(self, stage: str, status: str, **kwargs: Any) -> None:
        """Append a structured log entry."""
        entry = {
            "timestamp": datetime.now().astimezone().isoformat(),
            "stage": stage,
            "status": status,
            **kwargs,
        }
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
