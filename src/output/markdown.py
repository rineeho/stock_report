"""Markdown output generator: daily report summary in Markdown format.

Grouped by 증권사별/종목별 with report summaries, statistics, and source URLs.
"""

from __future__ import annotations

from pathlib import Path

from src.schemas.daily_result import DailyResult
from src.schemas.report import CanonicalReport
from src.schemas.summary import Summary


def generate_markdown(daily_result: DailyResult) -> str:
    """Generate Markdown report from DailyResult.

    Sections:
    - Header with date and stats
    - 증권사별 그룹
    - 종목별 그룹
    - 통계 요약
    """
    lines: list[str] = []

    # Header
    lines.append(f"# 일일 리포트 요약 — {daily_result.target_date.isoformat()}")
    lines.append("")
    lines.append(f"- 수집: {daily_result.total_discovered}건")
    lines.append(f"- 검증 통과: {daily_result.total_validated}건")
    lines.append(f"- 검증 불가: {daily_result.total_unverified}건")
    lines.append(f"- 중복 제거 후: {daily_result.total_deduplicated}건")
    lines.append("")

    # Build lookup maps
    report_map: dict[str, CanonicalReport] = {
        r.canonical_id: r for r in daily_result.reports
    }
    summary_map: dict[str, Summary] = {
        s.canonical_id: s for s in daily_result.summaries
    }

    # 증권사별 그룹
    if daily_result.classifications.by_brokerage:
        lines.append("## 증권사별")
        lines.append("")
        for brokerage, cids in sorted(daily_result.classifications.by_brokerage.items()):
            lines.append(f"### {brokerage} ({len(cids)}건)")
            lines.append("")
            for cid in cids:
                report = report_map.get(cid)
                if not report:
                    continue
                summary = summary_map.get(cid)
                lines.extend(_format_report_entry(report, summary))
            lines.append("")

    # 종목별 그룹
    if daily_result.classifications.by_ticker:
        lines.append("## 종목별")
        lines.append("")
        for ticker, cids in sorted(daily_result.classifications.by_ticker.items()):
            # Get stock name from first report
            first_report = report_map.get(cids[0])
            stock_name = first_report.stock_name if first_report else ticker
            lines.append(f"### {stock_name} ({ticker}) — {len(cids)}건")
            lines.append("")
            for cid in cids:
                report = report_map.get(cid)
                if not report:
                    continue
                summary = summary_map.get(cid)
                lines.extend(_format_report_entry(report, summary))
            lines.append("")

    # 통계
    lines.append("---")
    lines.append("")
    lines.append("## 파이프라인 통계")
    lines.append("")
    stats = daily_result.pipeline_stats
    lines.append("| 단계 | 수량 |")
    lines.append("|------|------|")
    lines.append(f"| 발견 | {stats.total_discovered} |")
    lines.append(f"| 다운로드 | {stats.total_fetched} |")
    lines.append(f"| 파싱 | {stats.total_parsed} |")
    lines.append(f"| 검증 통과 | {stats.total_validated} |")
    lines.append(f"| 중복 제거 후 | {stats.total_deduplicated} |")
    lines.append(f"| 요약 생성 | {stats.total_summarized} |")
    lines.append(f"| 소요 시간 | {stats.duration_ms}ms |")
    lines.append("")

    return "\n".join(lines)


def _format_report_entry(report: CanonicalReport, summary: Summary | None) -> list[str]:
    """Format a single report entry in Markdown."""
    lines: list[str] = []
    lines.append(f"- **{report.title}**")
    lines.append(f"  - 증권사: {report.brokerage} / 애널리스트: {report.analyst}")

    if report.ticker:
        lines.append(f"  - 종목: {report.stock_name or ''} ({report.ticker})")

    if summary:
        ext = summary.extracted
        if ext.target_price is not None:
            lines.append(f"  - 목표주가: {ext.target_price:,.0f}원")
        if ext.rating:
            lines.append(f"  - 투자의견: {ext.rating}")

        gen = summary.generated
        lines.append(f"  - **요약**: {gen.one_line}")
        if gen.key_points:
            for kp in gen.key_points:
                lines.append(f"    - {kp}")

    lines.append(f"  - 출처: {report.primary_url}")
    if report.duplicate_count > 1:
        lines.append(f"  - (중복 {report.duplicate_count}건 통합)")

    return lines


def write_markdown(daily_result: DailyResult, output_dir: str | Path) -> Path:
    """Write Markdown report to file."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "daily_report.md"

    content = generate_markdown(daily_result)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)

    return out_path
