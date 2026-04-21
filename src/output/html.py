"""HTML output generator: daily report summary as a self-contained HTML page.

Grouped by 증권사별/종목별 with embedded CSS styling.
"""

from __future__ import annotations

import html
from pathlib import Path

from src.schemas.daily_result import DailyResult
from src.schemas.report import CanonicalReport
from src.schemas.summary import Summary

_CSS = """\
:root {
  --bg: #f8f9fa;
  --card-bg: #fff;
  --border: #dee2e6;
  --accent: #1a73e8;
  --text: #212529;
  --muted: #6c757d;
  --success: #28a745;
  --tag-bg: #e9ecef;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
  padding: 2rem 1rem;
}
.container { max-width: 960px; margin: 0 auto; }
h1 {
  font-size: 1.6rem;
  border-bottom: 2px solid var(--accent);
  padding-bottom: .5rem;
  margin-bottom: 1.5rem;
}
.summary-bar {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 2rem;
}
.stat-chip {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: .5rem 1rem;
  font-size: .9rem;
}
.stat-chip strong { color: var(--accent); }
h2 {
  font-size: 1.3rem;
  margin: 2rem 0 1rem;
  color: var(--accent);
}
h3 {
  font-size: 1.05rem;
  margin: 1.2rem 0 .6rem;
  padding-left: .5rem;
  border-left: 3px solid var(--accent);
}
.report-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1rem 1.2rem;
  margin-bottom: .75rem;
}
.report-card .title {
  font-weight: 700;
  font-size: 1rem;
  margin-bottom: .4rem;
}
.report-card .title a {
  color: var(--text);
  text-decoration: none;
}
.report-card .title a:hover { color: var(--accent); text-decoration: underline; }
.meta { font-size: .85rem; color: var(--muted); margin-bottom: .3rem; }
.meta span { margin-right: .8rem; }
.tag {
  display: inline-block;
  background: var(--tag-bg);
  border-radius: 4px;
  padding: .1rem .45rem;
  font-size: .8rem;
  margin-right: .3rem;
}
.summary-block {
  margin-top: .5rem;
  padding: .6rem .8rem;
  background: #f1f3f5;
  border-radius: 6px;
  font-size: .9rem;
}
.summary-block .one-line { font-weight: 600; margin-bottom: .3rem; }
.summary-block ul { padding-left: 1.2rem; margin: .2rem 0 0; }
.summary-block li { margin-bottom: .15rem; }
.dup-badge {
  display: inline-block;
  background: var(--accent);
  color: #fff;
  border-radius: 4px;
  padding: .1rem .4rem;
  font-size: .75rem;
  margin-left: .4rem;
}
table.stats {
  width: 100%;
  border-collapse: collapse;
  margin-top: 1rem;
  font-size: .9rem;
}
table.stats th, table.stats td {
  border: 1px solid var(--border);
  padding: .45rem .8rem;
  text-align: left;
}
table.stats th { background: var(--tag-bg); font-weight: 600; }
hr { border: none; border-top: 1px solid var(--border); margin: 2rem 0; }
"""

_e = html.escape


def generate_html(daily_result: DailyResult) -> str:
    """Generate a self-contained HTML report from DailyResult."""
    h: list[str] = []

    # Document skeleton
    h.append("<!DOCTYPE html>")
    h.append('<html lang="ko">')
    h.append("<head>")
    h.append('<meta charset="utf-8">')
    h.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
    h.append(f"<title>일일 리포트 — {daily_result.target_date.isoformat()}</title>")
    h.append(f"<style>{_CSS}</style>")
    h.append("</head>")
    h.append("<body>")
    h.append('<div class="container">')

    # Header
    h.append(f"<h1>일일 리포트 요약 — {daily_result.target_date.isoformat()}</h1>")
    h.append('<div class="summary-bar">')
    h.append(f'<div class="stat-chip">수집 <strong>{daily_result.total_discovered}</strong>건</div>')
    h.append(f'<div class="stat-chip">검증 통과 <strong>{daily_result.total_validated}</strong>건</div>')
    h.append(f'<div class="stat-chip">검증 불가 <strong>{daily_result.total_unverified}</strong>건</div>')
    h.append(f'<div class="stat-chip">중복 제거 후 <strong>{daily_result.total_deduplicated}</strong>건</div>')
    h.append("</div>")

    # Lookup maps
    report_map: dict[str, CanonicalReport] = {r.canonical_id: r for r in daily_result.reports}
    summary_map: dict[str, Summary] = {s.canonical_id: s for s in daily_result.summaries}

    # 증권사별
    if daily_result.classifications.by_brokerage:
        h.append("<h2>증권사별</h2>")
        for brokerage, cids in sorted(daily_result.classifications.by_brokerage.items()):
            h.append(f"<h3>{_e(brokerage)} ({len(cids)}건)</h3>")
            for cid in cids:
                report = report_map.get(cid)
                if not report:
                    continue
                summary = summary_map.get(cid)
                h.append(_render_report_card(report, summary))

    # 종목별
    if daily_result.classifications.by_ticker:
        h.append("<h2>종목별</h2>")
        for ticker, cids in sorted(daily_result.classifications.by_ticker.items()):
            first_report = report_map.get(cids[0])
            stock_name = first_report.stock_name if first_report else ticker
            label = f"{_e(stock_name or '')} ({_e(ticker)})" if stock_name else _e(ticker)
            h.append(f"<h3>{label} — {len(cids)}건</h3>")
            for cid in cids:
                report = report_map.get(cid)
                if not report:
                    continue
                summary = summary_map.get(cid)
                h.append(_render_report_card(report, summary))

    # 테마별
    if daily_result.classifications.by_theme:
        h.append("<h2>테마별</h2>")
        sorted_themes = sorted(
            daily_result.classifications.by_theme.items(),
            key=lambda x: -len(x[1]),
        )
        for theme, cids in sorted_themes:
            h.append(f"<h3>{_e(theme)} — {len(cids)}건</h3>")
            for cid in cids:
                report = report_map.get(cid)
                if not report:
                    continue
                summary = summary_map.get(cid)
                h.append(_render_report_card(report, summary))

    # Pipeline stats
    h.append("<hr>")
    h.append("<h2>파이프라인 통계</h2>")
    stats = daily_result.pipeline_stats
    h.append('<table class="stats">')
    h.append("<thead><tr><th>단계</th><th>수량</th></tr></thead>")
    h.append("<tbody>")
    for label, value in [
        ("발견", stats.total_discovered),
        ("다운로드", stats.total_fetched),
        ("파싱", stats.total_parsed),
        ("검증 통과", stats.total_validated),
        ("중복 제거 후", stats.total_deduplicated),
        ("요약 생성", stats.total_summarized),
        ("소요 시간", f"{stats.duration_ms}ms"),
    ]:
        h.append(f"<tr><td>{label}</td><td>{value}</td></tr>")
    h.append("</tbody></table>")

    h.append("</div>")  # .container
    h.append("</body></html>")

    return "\n".join(h)


def _render_report_card(report: CanonicalReport, summary: Summary | None) -> str:
    """Render a single report as an HTML card."""
    parts: list[str] = []
    parts.append('<div class="report-card">')

    # Title with link
    title = _e(report.title)
    url = _e(report.primary_url)
    parts.append(f'<div class="title"><a href="{url}" target="_blank">{title}</a></div>')

    # Meta line
    meta_parts: list[str] = []
    meta_parts.append(f"<span>증권사: {_e(report.brokerage)}</span>")
    meta_parts.append(f"<span>애널리스트: {_e(report.analyst)}</span>")
    if report.ticker:
        stock = f"{_e(report.stock_name or '')} ({_e(report.ticker)})"
        meta_parts.append(f'<span class="tag">{stock}</span>')
    parts.append(f'<div class="meta">{"".join(meta_parts)}</div>')

    # Extracted info
    if summary:
        ext = summary.extracted
        tags: list[str] = []
        if ext.target_price is not None:
            tags.append(f'<span class="tag">목표가 {ext.target_price:,.0f}원</span>')
        if ext.rating:
            tags.append(f'<span class="tag">{_e(ext.rating)}</span>')
        if tags:
            parts.append(f'<div class="meta">{"".join(tags)}</div>')

        # Summary block
        gen = summary.generated
        parts.append('<div class="summary-block">')
        parts.append(f'<div class="one-line">{_e(gen.one_line)}</div>')
        if gen.key_points:
            parts.append("<ul>")
            for kp in gen.key_points:
                parts.append(f"<li>{_e(kp)}</li>")
            parts.append("</ul>")
        parts.append("</div>")

    # Duplicate badge
    if report.duplicate_count > 1:
        parts.append(f'<span class="dup-badge">중복 {report.duplicate_count}건 통합</span>')

    parts.append("</div>")
    return "\n".join(parts)


def write_html(daily_result: DailyResult, output_dir: str | Path) -> Path:
    """Write HTML report to file."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "daily_report.html"

    content = generate_html(daily_result)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)

    return out_path
