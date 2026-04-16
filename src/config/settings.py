"""Global settings loader. Timezone=Asia/Seoul, data paths, LLM config."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

TIMEZONE = ZoneInfo("Asia/Seoul")
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class LLMConfig:
    provider: str = "openai"
    api_key: str = ""
    model: str = ""

    def resolve_model(self) -> str:
        if self.model:
            return self.model
        if self.provider == "anthropic":
            return "claude-sonnet-4-5-20250929"
        return "gpt-4o-mini"


@dataclass
class SiteConfig:
    site_id: str
    name: str
    base_url: str
    parser_type: str
    rate_limit_rps: float = 1.0
    auth_type: str = "none"
    auth_config: dict = field(default_factory=dict)
    enabled: bool = True
    max_pages: int = 5


@dataclass
class Settings:
    timezone: ZoneInfo = TIMEZONE
    data_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data")
    log_level: str = "INFO"
    llm: LLMConfig = field(default_factory=LLMConfig)
    sites: list[SiteConfig] = field(default_factory=list)

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"

    @property
    def output_dir(self) -> Path:
        return self.data_dir / "output"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    def enabled_sites(self) -> list[SiteConfig]:
        return [s for s in self.sites if s.enabled]


def load_sites(sites_yaml: Path | None = None) -> list[SiteConfig]:
    """Load site configurations from sites.yaml."""
    if sites_yaml is None:
        sites_yaml = Path(__file__).parent / "sites.yaml"
    if not sites_yaml.exists():
        return []
    with open(sites_yaml, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not data or "sites" not in data:
        return []
    return [SiteConfig(**site) for site in data["sites"]]


def load_settings() -> Settings:
    """Load settings from environment variables and sites.yaml."""
    llm = LLMConfig(
        provider=os.environ.get("LLM_PROVIDER", "openai"),
        api_key=os.environ.get("OPENAI_API_KEY", "") or os.environ.get("ANTHROPIC_API_KEY", ""),
        model=os.environ.get("LLM_MODEL", ""),
    )
    data_dir = Path(os.environ.get("DATA_DIR", str(PROJECT_ROOT / "data")))
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    sites = load_sites()

    return Settings(
        data_dir=data_dir,
        log_level=log_level,
        llm=llm,
        sites=sites,
    )
