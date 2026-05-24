"""Shared async HTTP fetcher for data source clients.

Provides:
- A single httpx.AsyncClient with the project User-Agent.
- Bounded tenacity retries: 3 attempts, exponential backoff (1s/2s/4s),
  retries only on httpx.ConnectError / ReadTimeout / RemoteProtocolError
  and 5xx HTTPStatusError.
- 1-hour file cache in /tmp/bharat-cache/ keyed on source_url
  (CLAUDE.md §2 rule 5: low-frequency cached access).

CONTRACT:
- 403 / 429 are hard failures — we do NOT retry past tenacity defaults
  and we NEVER spoof browser User-Agents to bypass blocks.
- All errors surface via DataSourceError with `status_code` populated
  when applicable.
"""
from __future__ import annotations

import hashlib
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception,
    retry_if_exception_type,
    stop_after_attempt,
    stop_after_delay,
    wait_exponential,
)

from backend.errors import DataSourceError

log = structlog.get_logger()

USER_AGENT = "bharat-research-brain/0.1 (personal research)"
CACHE_DIR = Path(tempfile.gettempdir()) / "bharat-cache"
DEFAULT_CACHE_TTL = 3600  # 1 hour


@dataclass(frozen=True)
class FetchMetadata:
    """Provenance attached to every fetched artifact."""

    source_url: str
    downloaded_at_utc: datetime
    file_sha256: str
    row_count: int
    http_status: int
    content_length: int
    cache_hit: bool = False
    is_stub: bool = False


_TRANSIENT: tuple[type[BaseException], ...] = (
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.RemoteProtocolError,
)


def _is_5xx(exc: BaseException) -> bool:
    return (
        isinstance(exc, httpx.HTTPStatusError)
        and 500 <= exc.response.status_code < 600
    )


_retry_transient = retry(
    retry=retry_if_exception_type(_TRANSIENT) | retry_if_exception(_is_5xx),
    stop=stop_after_attempt(3) | stop_after_delay(15),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True,
)


def _cache_path(url: str) -> Path:
    h = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{h}.bin"


def _read_cache(url: str, ttl: int) -> bytes | None:
    if ttl <= 0:
        return None
    p = _cache_path(url)
    if not p.exists():
        return None
    age = time.time() - p.stat().st_mtime
    if age > ttl:
        return None
    return p.read_bytes()


def _write_cache(url: str, data: bytes) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _cache_path(url).write_bytes(data)


@_retry_transient
async def _do_get(client: httpx.AsyncClient, url: str) -> httpx.Response:
    """Single HTTP GET wrapped by tenacity. 403/429 hard-fail without retries."""
    resp = await client.get(url)

    # Hard-fail on rate-limit / block signals — do not retry past tenacity
    # defaults. NSE rate-limit signals must be respected (CLAUDE.md §2 rule 5).
    if resp.status_code in (403, 429):
        reason = "rate_limited" if resp.status_code == 429 else "auth_required"
        log.error(
            "http.blocked",
            source_url=url,
            http_status=resp.status_code,
            reason=reason,
            note="provider blocked or rate-limited; do not retry, do not spoof",
        )
        raise DataSourceError(
            f"Source returned {resp.status_code} for {url} — "
            "provider rate-limited or blocked our user agent. Do not retry.",
            status_code=resp.status_code,
            reason_code=reason,
        )

    resp.raise_for_status()
    return resp


async def fetch_bytes(
    url: str,
    *,
    cache_ttl: int = DEFAULT_CACHE_TTL,
    timeout: float = 30.0,
    validate: Callable[[bytes], None] | None = None,
) -> tuple[bytes, FetchMetadata]:
    """Fetch raw bytes with retry, cache, and provenance metadata.

    Returns (body, metadata). Metadata's `row_count` defaults to 0 — callers
    parse the body and emit an updated `FetchMetadata` via dataclasses.replace().

    `validate`, if given, is called with the body BEFORE it is cached (and on
    cache hits). It should raise to reject the body — a rejected body is never
    written to the cache, so transient error pages served as HTTP 200 (e.g.
    soft-404 HTML) cannot poison the cache for the TTL window.
    """
    bound_log = log.bind(source_url=url)

    cached = _read_cache(url, cache_ttl)
    if cached is not None:
        if validate is not None:
            validate(cached)
        bound_log.info("http.cache_hit", bytes=len(cached))
        return cached, FetchMetadata(
            source_url=url,
            downloaded_at_utc=datetime.now(UTC),
            file_sha256=hashlib.sha256(cached).hexdigest(),
            row_count=0,
            http_status=200,
            content_length=len(cached),
            cache_hit=True,
        )

    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    async with httpx.AsyncClient(
        timeout=timeout, headers=headers, follow_redirects=True
    ) as client:
        bound_log.info("http.fetch.start")
        try:
            resp = await _do_get(client, url)
        except DataSourceError:
            raise
        except httpx.HTTPStatusError as exc:
            bound_log.error(
                "http.fetch.http_error",
                http_status=exc.response.status_code,
            )
            raise DataSourceError(
                f"HTTP {exc.response.status_code} for {url}",
                status_code=exc.response.status_code,
            ) from exc
        except Exception as exc:
            bound_log.error("http.fetch.failed", error=str(exc))
            raise DataSourceError(f"fetch failed for {url}: {exc}") from exc

    body = resp.content
    if validate is not None:
        validate(body)
    _write_cache(url, body)
    sha = hashlib.sha256(body).hexdigest()
    bound_log.info(
        "http.fetch.success",
        bytes=len(body),
        sha256_prefix=sha[:16],
        http_status=resp.status_code,
    )
    return body, FetchMetadata(
        source_url=url,
        downloaded_at_utc=datetime.now(UTC),
        file_sha256=sha,
        row_count=0,
        http_status=resp.status_code,
        content_length=len(body),
        cache_hit=False,
    )
