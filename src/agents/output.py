"""OutputAgent: write final Markdown + JSON outputs to data/output/{target_date}/."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import structlog

from src.agents.base import BaseAgent
from src.output.html import write_html
from src.output.json_output import write_daily_result
from src.output.markdown import write_markdown
from src.schemas.daily_result import DailyResult

logger = structlog.get_logger()


class OutputAgent(BaseAgent):
    """Writes final results as Markdown and/or JSON files."""

    def __init__(self, output_dir: str, output_format: str = "all") -> None:
        self.output_dir = output_dir
        self.output_format = output_format

    @property
    def stage_name(self) -> str:
        return "output"

    async def process(
        self, items: list[DailyResult], target_date: date, **kwargs: Any
    ) -> list[dict]:
        """Write output files.

        Args:
            items: List with one DailyResult from aggregate stage.
        """
        if not items:
            logger.warning("no_daily_result_to_output")
            return []

        item = items[0]
        if isinstance(item, dict):
            item = DailyResult(**item)

        out_dir = Path(self.output_dir)
        outputs: list[str] = []

        if self.output_format in ("json", "all"):
            json_path = write_daily_result(item, out_dir)
            outputs.append(str(json_path))
            logger.info("json_output_written", path=str(json_path))

        if self.output_format in ("md", "all"):
            md_path = write_markdown(item, out_dir)
            outputs.append(str(md_path))
            logger.info("markdown_output_written", path=str(md_path))

        if self.output_format in ("html", "all"):
            html_path = write_html(item, out_dir)
            outputs.append(str(html_path))
            logger.info("html_output_written", path=str(html_path))

        return [{"output_files": outputs, "target_date": target_date.isoformat()}]
