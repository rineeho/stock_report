"""Rate-limited async HTTP client with per-site token bucket and retry."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()

DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 3
BACKOFF_BASE = 1.0


class TokenBucket:
    """Simple token bucket rate limiter."""

    def __init__(self, rate: float) -> None:
        self.rate = rate  # tokens per second
        self.tokens = rate
        self.max_tokens = rate
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a token is available."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.max_tokens, self.tokens + elapsed * self.rate)
            self.last_refill = now

            if self.tokens < 1:
                wait_time = (1 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1


class RateLimitedClient:
    """Async HTTP client with per-site rate limiting and retry."""

    def __init__(self) -> None:
        self._buckets: dict[str, TokenBucket] = {}
        self._client: httpx.AsyncClient | None = None

    def set_rate_limit(self, site_id: str, rps: float) -> None:
        """Configure rate limit for a specific site."""
        self._buckets[site_id] = TokenBucket(rps)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=DEFAULT_TIMEOUT,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                },
            )
        return self._client

    async def get(self, url: str, site_id: str, **kwargs: Any) -> httpx.Response:
        """Fetch URL with rate limiting and retry.

        Args:
            url: The URL to fetch.
            site_id: Site identifier for rate limiting.
            **kwargs: Additional httpx request kwargs.

        Returns:
            httpx.Response on success.

        Raises:
            httpx.HTTPError: After all retries are exhausted.
        """
        bucket = self._buckets.get(site_id)

        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            if bucket:
                await bucket.acquire()

            try:
                client = await self._get_client()
                response = await client.get(url, **kwargs)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                # Don't retry 4xx client errors (404, 403, etc.)
                if 400 <= exc.response.status_code < 500:
                    logger.warning(
                        "http_client_error",
                        url=url,
                        status_code=exc.response.status_code,
                        error=str(exc),
                    )
                    raise
                last_exc = exc
                wait = BACKOFF_BASE * (2**attempt)
                logger.warning(
                    "http_retry",
                    url=url,
                    attempt=attempt + 1,
                    error=str(exc),
                    wait_seconds=wait,
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(wait)
            except httpx.RequestError as exc:
                last_exc = exc
                wait = BACKOFF_BASE * (2**attempt)
                logger.warning(
                    "http_retry",
                    url=url,
                    attempt=attempt + 1,
                    error=str(exc),
                    wait_seconds=wait,
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(wait)

        raise last_exc  # type: ignore[misc]

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
