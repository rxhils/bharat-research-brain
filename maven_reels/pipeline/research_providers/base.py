"""Provider abstraction: every provider returns normalized story dicts.

Story fields (all REAL content from the source — nothing invented):
  headline, summary, source_name, source_url, published_at (ISO or ""),
  provider. Downstream steps derive category/sectors/numbers from this text
  only, always keeping the source URL attached to every claim.
"""
from __future__ import annotations

import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) MavenNewsroom/1.0 "
      "(research; personal educational use)")
TIMEOUT = 10


def http_get(url: str, timeout: int = TIMEOUT) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


class Story(dict):
    """dict with guaranteed keys."""

    @classmethod
    def make(cls, *, headline: str, summary: str, source_name: str,
             source_url: str, published_at: str = "", provider: str = "") -> "Story":
        return cls(headline=" ".join(str(headline).split())[:220],
                   summary=" ".join(str(summary).split())[:500],
                   source_name=source_name, source_url=source_url,
                   published_at=published_at, provider=provider)


def available_providers() -> list:
    """Providers in priority order; key-gated ones only when configured."""
    from . import news_provider, rss_provider, tavily_provider
    out = []
    if tavily_provider.configured():
        out.append(tavily_provider)
    if news_provider.configured():
        out.append(news_provider)
    out.append(rss_provider)   # always available, zero-key
    return out


def fetch_all(max_per_provider: int = 25) -> tuple[list[Story], list[str], list[str]]:
    """(stories, sources_used, errors) across all configured providers."""
    stories: list[Story] = []
    used: list[str] = []
    errors: list[str] = []
    for p in available_providers():
        try:
            got = p.fetch(max_items=max_per_provider)
            if got:
                stories.extend(got)
                used.append(p.NAME)
        except Exception as exc:  # provider-level failure is non-fatal
            errors.append(f"{getattr(p, 'NAME', p.__name__)}: {exc}")
    return stories, used, errors
