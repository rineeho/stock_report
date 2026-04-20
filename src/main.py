"""CLI entry point for report-agent per cli-interface.md contract."""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date

from src.utils.timezone import today_kst


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments per cli-interface.md."""
    parser = argparse.ArgumentParser(
        prog="report-agent",
        description="Daily Stock Report Agent - 매일 주식 리포트를 자동 수집/요약하는 파이프라인",
    )
    subparsers = parser.add_subparsers(dest="command")

    # run command
    run_parser = subparsers.add_parser("run", help="파이프라인 실행")
    run_parser.add_argument(
        "--date", "-d",
        type=lambda s: date.fromisoformat(s),
        default=today_kst(),
        help="수집 대상 날짜 (YYYY-MM-DD, 기본: 오늘 KST)",
    )
    run_parser.add_argument(
        "--sites", "-s",
        type=lambda s: s.split(","),
        default=None,
        help="특정 사이트만 실행 (쉼표 구분)",
    )
    run_parser.add_argument(
        "--from-stage",
        default=None,
        choices=["discover", "fetch", "parse", "validate", "normalize",
                 "deduplicate", "summarize", "classify", "aggregate", "output"],
        help="재시작할 단계",
    )
    run_parser.add_argument(
        "--output-dir", "-o",
        default=None,
        help="결과 출력 경로 (기본: data/output/{date}/)",
    )
    run_parser.add_argument(
        "--format", "-f",
        choices=["json", "md", "html", "all"],
        default="all",
        help="출력 형식 (기본: all)",
    )
    run_parser.add_argument("--verbose", "-v", action="store_true", help="상세 로그 출력")
    run_parser.add_argument("--dry-run", action="store_true", help="실제 수집 없이 설정 검증만")

    # sites command
    sites_parser = subparsers.add_parser("sites", help="사이트 관리")
    sites_sub = sites_parser.add_subparsers(dest="sites_command")
    sites_sub.add_parser("list", help="사이트 목록 확인")
    test_parser = sites_sub.add_parser("test", help="특정 사이트 파서 테스트")
    test_parser.add_argument("site_id", help="사이트 ID")
    test_parser.add_argument("--url", default=None, help="테스트 URL")

    # cache command
    cache_parser = subparsers.add_parser("cache", help="캐시 관리")
    cache_sub = cache_parser.add_subparsers(dest="cache_command")
    list_cache = cache_sub.add_parser("list", help="캐시 현황 확인")
    list_cache.add_argument("--date", type=lambda s: date.fromisoformat(s), default=None)
    clear_cache = cache_sub.add_parser("clear", help="캐시 삭제")
    clear_cache.add_argument("--date", type=lambda s: date.fromisoformat(s), required=True)

    # serve command
    serve_parser = subparsers.add_parser("serve", help="대시보드 웹서버 실행")
    serve_parser.add_argument("--host", default="127.0.0.1", help="바인드 호스트 (기본: 127.0.0.1)")
    serve_parser.add_argument("--port", "-p", type=int, default=8000, help="포트 번호 (기본: 8000)")
    serve_parser.add_argument("--reload", action="store_true", help="개발 모드 (자동 리로드)")

    # build-site command
    build_parser = subparsers.add_parser("build-site", help="정적 사이트 빌드 (GitHub Pages용)")
    build_parser.add_argument("--data-dir", default=None, help="데이터 디렉토리 (기본: data/output)")
    build_parser.add_argument("--output-dir", default=None, help="출력 디렉토리 (기본: _site)")

    return parser.parse_args(argv)


async def run_pipeline(args: argparse.Namespace) -> int:
    """Execute the report pipeline."""
    from src.config.settings import load_settings
    from src.parsers.registry import discover_parsers
    from src.pipeline.checkpoint import CheckpointManager
    from src.pipeline.logger import PipelineFileLogger, configure_logging
    from src.pipeline.orchestrator import PipelineOrchestrator

    settings = load_settings()
    configure_logging("DEBUG" if args.verbose else settings.log_level)

    discover_parsers()

    target_date = args.date
    PipelineFileLogger(settings.logs_dir, target_date)  # ensures log dir exists
    checkpoint = CheckpointManager(settings.cache_dir)

    if args.dry_run:
        print(f"[DRY RUN] target_date={target_date}", file=sys.stderr)
        print(f"[DRY RUN] enabled_sites={[s.site_id for s in settings.enabled_sites()]}", file=sys.stderr)
        print("[DRY RUN] Configuration is valid.", file=sys.stderr)
        return 0

    # Filter sites if specified
    sites = settings.enabled_sites()
    if args.sites:
        sites = [s for s in sites if s.site_id in args.sites]

    if not sites:
        print("Error: No enabled sites found.", file=sys.stderr)
        return 2

    # Build agent chain
    from src.agents.fetch import FetchAgent
    from src.agents.normalize import NormalizationAgent
    from src.agents.parse import ParseAgent
    from src.agents.source_discovery import SourceDiscoveryAgent
    from src.agents.validate import ValidationAgent
    from src.utils.http import RateLimitedClient

    http_client = RateLimitedClient()
    for site in sites:
        http_client.set_rate_limit(site.site_id, site.rate_limit_rps)

    agents = [
        SourceDiscoveryAgent(sites=sites, http_client=http_client),
        FetchAgent(http_client=http_client),
        ParseAgent(llm_config=settings.llm),
        ValidationAgent(),
        NormalizationAgent(),
    ]

    # Add optional agents if their modules exist
    try:
        from src.agents.deduplicate import DeduplicationAgent
        agents.append(DeduplicationAgent())
    except ImportError:
        pass

    try:
        from src.agents.summarize import SummarizationAgent
        agents.append(SummarizationAgent(settings.llm))
    except ImportError:
        pass

    try:
        from src.agents.classify import ClassificationAgent
        agents.append(ClassificationAgent())
    except ImportError:
        pass

    try:
        from src.agents.aggregate import AggregationAgent
        agents.append(AggregationAgent())
    except ImportError:
        pass

    try:
        from src.agents.output import OutputAgent
        output_dir = args.output_dir or str(settings.output_dir / target_date.isoformat())
        agents.append(OutputAgent(output_dir=output_dir, output_format=args.format))
    except ImportError:
        pass

    orchestrator = PipelineOrchestrator(
        agents=agents,
        checkpoint_manager=checkpoint,
        from_stage=args.from_stage,
    )

    try:
        envelopes = await orchestrator.run(target_date, sites=sites, http_client=http_client, checkpoint_manager=checkpoint)
    except Exception as exc:
        print(f"Pipeline failed: {exc}", file=sys.stderr)
        return 3
    finally:
        await http_client.close()

    # Print summary to stdout
    for env in envelopes:
        print(f"[{env.stage}] input={env.stats.total_input} output={env.stats.total_output} "
              f"failed={env.stats.total_failed} duration={env.stats.duration_ms}ms")

    # Check for partial failure
    any_failed = any(e.stats.total_failed > 0 for e in envelopes)
    return 1 if any_failed else 0


def main(argv: list[str] | None = None) -> None:
    """Main entry point."""
    args = parse_args(argv)

    if args.command == "run":
        exit_code = asyncio.run(run_pipeline(args))
        sys.exit(exit_code)
    elif args.command == "sites":
        _handle_sites(args)
    elif args.command == "cache":
        _handle_cache(args)
    elif args.command == "serve":
        _handle_serve(args)
    elif args.command == "build-site":
        _handle_build_site(args)
    else:
        parse_args(["--help"])


def _handle_sites(args: argparse.Namespace) -> None:
    """Handle sites subcommands."""
    from src.config.settings import load_settings

    settings = load_settings()

    if args.sites_command == "list":
        for site in settings.sites:
            status = "enabled" if site.enabled else "disabled"
            print(f"  {site.site_id}: {site.name} ({status}) - {site.base_url}")
    elif args.sites_command == "test":
        _test_site_parser(args.site_id, args.url)
    else:
        print("Usage: report-agent sites {list|test}", file=sys.stderr)


def _test_site_parser(site_id: str, test_url: str | None = None) -> None:
    """Test a specific site parser by running discover on its listing page."""
    from src.parsers.registry import discover_parsers, get_parser

    discover_parsers()
    parser = get_parser(site_id)
    if parser is None:
        print(f"Error: No parser found for site_id '{site_id}'", file=sys.stderr)
        sys.exit(1)

    print(f"Parser found: {type(parser).__name__} (site_id={site_id})")

    if test_url:
        print(f"Testing with URL: {test_url}")
        try:
            import httpx
            resp = httpx.get(test_url, timeout=10, follow_redirects=True)
            html = resp.text

            import asyncio
            reports = asyncio.run(parser.discover_reports(html, base_url=test_url))
            print(f"Discovered {len(reports)} report(s)")
            for r in reports[:5]:
                print(f"  - {r.discovered_url}")
        except Exception as exc:
            print(f"Error during test: {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        print("Parser is registered and ready. Use --url to test with a live page.")


def _handle_cache(args: argparse.Namespace) -> None:
    """Handle cache subcommands."""
    from src.config.settings import load_settings
    from src.pipeline.checkpoint import CheckpointManager

    settings = load_settings()
    cm = CheckpointManager(settings.cache_dir)

    if args.cache_command == "list":
        if args.date:
            checkpoints = cm.list_checkpoints(args.date)
            print(f"Checkpoints for {args.date}: {checkpoints}")
        else:
            print("Usage: report-agent cache list --date YYYY-MM-DD")
    elif args.cache_command == "clear":
        count = cm.clear(args.date)
        print(f"Cleared {count} checkpoint(s) for {args.date}")
    else:
        print("Usage: report-agent cache {list|clear}", file=sys.stderr)


def _handle_serve(args: argparse.Namespace) -> None:
    """Launch the dashboard web server."""
    import uvicorn

    from src.web.app import create_app

    app = create_app()
    print(f"Dashboard: http://{args.host}:{args.port}", file=sys.stderr)
    uvicorn.run(app, host=args.host, port=args.port)


def _handle_build_site(args: argparse.Namespace) -> None:
    """Build static site for GitHub Pages."""
    from pathlib import Path

    from src.web.build_static import build_static_site

    data_dir = Path(args.data_dir) if args.data_dir else None
    output_dir = Path(args.output_dir) if args.output_dir else None
    result = build_static_site(data_dir=data_dir, output_dir=output_dir)
    print(f"Static site built: {result}", file=sys.stderr)


if __name__ == "__main__":
    main()
