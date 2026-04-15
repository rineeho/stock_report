"""Parser registry: site_id → parser class mapping with auto-discovery."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from src.parsers.base import BaseSiteParser

logger = structlog.get_logger()

_REGISTRY: dict[str, type[BaseSiteParser]] = {}


def register_parser(parser_cls: type[BaseSiteParser]) -> type[BaseSiteParser]:
    """Decorator to register a parser class."""
    # Instantiate to get site_id
    _REGISTRY[parser_cls.site_id.fget(None)] = parser_cls  # type: ignore[arg-type, attr-defined]
    return parser_cls


def register(site_id: str, parser_cls: type[BaseSiteParser]) -> None:
    """Explicitly register a parser for a site_id."""
    _REGISTRY[site_id] = parser_cls


def get_parser(site_id: str) -> BaseSiteParser | None:
    """Get parser instance for a site_id."""
    cls = _REGISTRY.get(site_id)
    if cls is None:
        logger.warning("parser_not_found", site_id=site_id)
        return None
    return cls()


def list_parsers() -> dict[str, type[BaseSiteParser]]:
    """Return all registered parsers."""
    return dict(_REGISTRY)


def discover_parsers() -> None:
    """Import all parser modules to trigger registration."""
    import importlib
    import pkgutil

    import src.parsers.sites as sites_pkg

    for _importer, modname, _ispkg in pkgutil.iter_modules(sites_pkg.__path__):
        importlib.import_module(f"src.parsers.sites.{modname}")
