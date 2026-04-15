"""CLI utility tests for T064 and T065.

Tests: sites list, sites test, cache list/clear, --dry-run, parse_args.
"""

from __future__ import annotations

from datetime import date

import pytest

from src.main import parse_args


class TestParseArgs:
    """Test CLI argument parsing."""

    def test_run_default(self):
        args = parse_args(["run"])
        assert args.command == "run"
        assert isinstance(args.date, date)
        assert args.format == "all"
        assert args.verbose is False
        assert args.dry_run is False

    def test_run_with_date(self):
        args = parse_args(["run", "--date", "2026-04-10"])
        assert args.date == date(2026, 4, 10)

    def test_run_with_sites_filter(self):
        args = parse_args(["run", "--sites", "naver_research,hankyung_consensus"])
        assert args.sites == ["naver_research", "hankyung_consensus"]

    def test_run_with_format_json(self):
        args = parse_args(["run", "--format", "json"])
        assert args.format == "json"

    def test_run_with_format_md(self):
        args = parse_args(["run", "--format", "md"])
        assert args.format == "md"

    def test_run_with_from_stage(self):
        args = parse_args(["run", "--from-stage", "summarize"])
        assert args.from_stage == "summarize"

    def test_run_with_output_dir(self):
        args = parse_args(["run", "--output-dir", "/tmp/out"])
        assert args.output_dir == "/tmp/out"

    def test_run_verbose(self):
        args = parse_args(["run", "-v"])
        assert args.verbose is True

    def test_run_dry_run(self):
        args = parse_args(["run", "--dry-run"])
        assert args.dry_run is True

    def test_sites_list(self):
        args = parse_args(["sites", "list"])
        assert args.command == "sites"
        assert args.sites_command == "list"

    def test_sites_test(self):
        args = parse_args(["sites", "test", "naver_research"])
        assert args.command == "sites"
        assert args.sites_command == "test"
        assert args.site_id == "naver_research"

    def test_sites_test_with_url(self):
        args = parse_args(["sites", "test", "naver_research", "--url", "https://example.com"])
        assert args.url == "https://example.com"

    def test_cache_list(self):
        args = parse_args(["cache", "list", "--date", "2026-04-10"])
        assert args.command == "cache"
        assert args.cache_command == "list"
        assert args.date == date(2026, 4, 10)

    def test_cache_clear(self):
        args = parse_args(["cache", "clear", "--date", "2026-04-10"])
        assert args.cache_command == "clear"


class TestDryRun:
    """Test --dry-run mode outputs config validation."""

    @pytest.mark.asyncio
    async def test_dry_run_returns_zero(self):
        """--dry-run should validate config and return 0."""
        from src.main import run_pipeline

        args = parse_args(["run", "--dry-run"])
        exit_code = await run_pipeline(args)
        assert exit_code == 0


class TestSitesTest:
    """Test sites test command."""

    def test_test_parser_found(self, capsys):
        """sites test should find a registered parser."""
        from src.main import _test_site_parser

        _test_site_parser("naver_research", test_url=None)
        captured = capsys.readouterr()
        assert "NaverResearchParser" in captured.out
        assert "registered and ready" in captured.out

    def test_test_parser_not_found(self):
        """sites test with unknown site_id should fail."""
        from src.main import _test_site_parser

        with pytest.raises(SystemExit):
            _test_site_parser("nonexistent_site", test_url=None)
