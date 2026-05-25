"""News Agent — fetch + dedup + ISIN-match daily market news (Chunk 3.2).

RSS is the primary, key-free path (built first). NewsAPI / Marketaux are
optional and skipped cleanly when their API keys are absent. Stock matching is
pure + in-memory: exact NSE-symbol token match (which also catches the common
short name, since the symbol usually *is* it), then a suffix-stripped
company-name match; otherwise the article is stored market-wide (isin NULL).
No LLMs; sentiment columns are left NULL for Chunk 3.3.
"""
from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog

from backend.config import settings
from backend.data_sources._http import fetch_bytes
from backend.errors import DataSourceError

log = structlog.get_logger()

RSS_FEEDS: dict[str, str] = {
    "Economic Times Markets": "https://economictimes.indiatimes.com/markets/rss.cms",
    "Moneycontrol": "https://www.moneycontrol.com/rss/MCtopnews.xml",
    "Business Standard Markets": "https://www.business-standard.com/rss/markets-106.rss",
    "NDTV Profit": "https://feeds.feedburner.com/ndtvprofit-latest",
    "LiveMint Markets": "https://www.livemint.com/rss/markets",
    "Zeebiz Markets": "https://zeebiz.com/markets/rss",
}

_NAME_SUFFIXES = (" LIMITED", " LTD.", " LTD", " LIMITED.")


@dataclass(frozen=True)
class RawArticle:
    headline: str
    summary: str | None
    source_name: str
    source_url: str
    published_at: datetime | None


@dataclass(frozen=True)
class KnownStock:
    isin: str
    nse_symbol: str | None
    company_name: str


@dataclass
class NewsResult:
    fetched: int = 0
    deduped: int = 0
    matched: int = 0
    unmatched: int = 0
    inserted: int = 0
    sample: list[tuple[str, str | None]] | None = None


def _short_name(company_name: str) -> str:
    n = company_name.upper().strip()
    for suffix in _NAME_SUFFIXES:
        if n.endswith(suffix):
            n = n[: -len(suffix)].strip()
            break
    return n


def match_to_isin(
    headline: str, summary: str | None, known_stocks: list[KnownStock]
) -> str | None:
    """Match an article to an ISIN: exact symbol token, then company name."""
    text = f"{headline} {summary or ''}".upper()
    tokens = set(re.findall(r"[A-Z0-9&]+", text))
    for st in known_stocks:
        if st.nse_symbol and st.nse_symbol.upper() in tokens:
            return st.isin
    for st in known_stocks:
        sn = _short_name(st.company_name)
        if len(sn) >= 4 and sn in text:
            return st.isin
    return None


def dedup_by_url(articles: list[RawArticle]) -> list[RawArticle]:
    seen: set[str] = set()
    out: list[RawArticle] = []
    for a in articles:
        if a.source_url in seen:
            continue
        seen.add(a.source_url)
        out.append(a)
    return out


class NewsAgent:
    async def fetch_rss(self, feed_url: str, source_name: str) -> list[RawArticle]:
        import feedparser  # lazy: keeps module importable without the dep

        body, _meta = await fetch_bytes(feed_url, cache_ttl=0)
        parsed = feedparser.parse(body)
        out: list[RawArticle] = []
        for entry in parsed.entries:
            link = entry.get("link")
            title = entry.get("title")
            if not link or not title:
                continue
            pp = entry.get("published_parsed") or entry.get("updated_parsed")
            published = (
                datetime.fromtimestamp(calendar.timegm(pp), tz=UTC) if pp else None
            )
            out.append(
                RawArticle(
                    headline=title.strip(),
                    summary=(entry.get("summary") or entry.get("description") or None),
                    source_name=source_name,
                    source_url=link.strip(),
                    published_at=published,
                )
            )
        log.info("news.rss.fetched", source=source_name, count=len(out))
        return out

    async def fetch_newsapi(
        self, query: str, from_date: str | None = None
    ) -> list[RawArticle]:
        if not settings.newsapi_key:
            log.info("news.newsapi.skipped", reason="no NEWSAPI_KEY in .env")
            return []
        params = {"q": query, "language": "en", "apiKey": settings.newsapi_key}
        if from_date:
            params["from"] = from_date
        body, _meta = await fetch_bytes(
            _with_params("https://newsapi.org/v2/everything", params), cache_ttl=0
        )
        import json

        data = json.loads(body)
        out = [
            RawArticle(
                headline=a.get("title", "").strip(),
                summary=a.get("description"),
                source_name=(a.get("source") or {}).get("name", "NewsAPI"),
                source_url=a.get("url", ""),
                published_at=_iso_or_none(a.get("publishedAt")),
            )
            for a in data.get("articles", [])
            if a.get("url") and a.get("title")
        ]
        log.info("news.newsapi.fetched", count=len(out))
        return out

    async def fetch_marketaux(self, query: str) -> list[RawArticle]:
        if not settings.marketaux_key:
            log.info("news.marketaux.skipped", reason="no MARKETAUX_KEY in .env")
            return []
        params = {
            "search": query,
            "language": "en",
            "api_token": settings.marketaux_key,
        }
        body, _meta = await fetch_bytes(
            _with_params("https://api.marketaux.com/v1/news/all", params), cache_ttl=0
        )
        import json

        data = json.loads(body)
        out = [
            RawArticle(
                headline=a.get("title", "").strip(),
                summary=a.get("description") or a.get("snippet"),
                source_name=a.get("source", "Marketaux"),
                source_url=a.get("url", ""),
                published_at=_iso_or_none(a.get("published_at")),
            )
            for a in data.get("data", [])
            if a.get("url") and a.get("title")
        ]
        log.info("news.marketaux.fetched", count=len(out))
        return out

    async def run(
        self, *, sources: tuple[str, ...] = ("rss",), dry_run: bool = False
    ) -> NewsResult:
        want = set(sources)
        raw: list[RawArticle] = []
        if {"rss", "all"} & want:
            for name, url in RSS_FEEDS.items():
                try:
                    raw.extend(await self.fetch_rss(url, name))
                except DataSourceError as exc:
                    log.warning("news.rss.failed", source=name, error=str(exc))
        if {"newsapi", "all"} & want:
            raw.extend(await self.fetch_newsapi("NSE OR Sensex OR Nifty"))
        if {"marketaux", "all"} & want:
            raw.extend(await self.fetch_marketaux("NSE"))

        deduped = dedup_by_url(raw)
        known = await self._load_known_stocks()

        rows: list[dict[str, Any]] = []
        sample: list[tuple[str, str | None]] = []
        now = datetime.now(UTC)
        matched = 0
        for a in deduped:
            isin = match_to_isin(a.headline, a.summary, known)
            if isin:
                matched += 1
            rows.append(
                {
                    "isin": isin,
                    "headline": a.headline,
                    "summary": a.summary,
                    "source_name": a.source_name,
                    "source_url": a.source_url,
                    "published_at": a.published_at,
                    "fetched_at": now,
                }
            )
            if len(sample) < 10:
                sample.append((a.headline, isin))

        inserted = 0
        if not dry_run and rows:
            from backend.db.repositories import news as news_repo
            from backend.db.session import SessionLocal

            async with SessionLocal() as session:
                inserted = await news_repo.bulk_insert(session, rows)
                await session.commit()

        log.info(
            "news.run.done",
            fetched=len(raw),
            deduped=len(deduped),
            matched=matched,
            inserted=inserted,
            dry_run=dry_run,
        )
        return NewsResult(
            fetched=len(raw),
            deduped=len(deduped),
            matched=matched,
            unmatched=len(deduped) - matched,
            inserted=inserted,
            sample=sample,
        )

    async def _load_known_stocks(self) -> list[KnownStock]:
        from sqlalchemy import select

        from backend.db.models import Stock
        from backend.db.session import SessionLocal

        async with SessionLocal() as session:
            rows = (
                await session.execute(
                    select(Stock.isin, Stock.nse_symbol, Stock.company_name).where(
                        Stock.delisted_on.is_(None)
                    )
                )
            ).all()
        return [KnownStock(isin, sym, name) for isin, sym, name in rows]


def _with_params(url: str, params: dict[str, str]) -> str:
    from urllib.parse import urlencode

    return f"{url}?{urlencode(params)}"


def _iso_or_none(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
