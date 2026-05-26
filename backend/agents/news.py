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
import json
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
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

# Short NSE symbols that are also common English words. A bare token match on
# these leaks false positives ("Cooling Oil" -> OIL India). For a blocklisted
# symbol we require a context confirm: a market context word nearby, or the
# stock's multi-word company name present in the text.
SYMBOL_BLOCKLIST = frozenset(
    {
        "OIL", "MAN", "YES", "PNB", "ITC", "CAN", "HER", "SUN", "BSE", "CUB",
        "GAIL", "IDEA", "BANK", "POWER", "INFO", "TECH", "AGRO", "GOLD", "MID",
        "ALL", "ANY", "ARE", "BEST", "CARE", "CITY", "DAY", "EASE", "FACT",
        "FINE", "GETS", "GO", "GOOD", "HIGH", "JET", "JOY", "JUST", "LAW",
        "MAP", "MORE", "NOW", "ONE", "PIX", "PRO", "RACE", "RAIN", "REC",
        "RISE", "STAR", "TIME", "TOP", "UCO", "WIN",
    }
)
_CONTEXT_WORDS = ("NSE:", "BSE:", "STOCK", "SHARES", "SHARE", "EQUITY", "SCRIP")


@dataclass(frozen=True)
class RawArticle:
    headline: str
    summary: str | None
    source_name: str
    source_url: str
    published_at: datetime | None
    isin: str | None = None  # pre-resolved for deals/announcements; None for RSS


@dataclass(frozen=True)
class KnownStock:
    isin: str
    nse_symbol: str | None
    company_name: str


@dataclass(frozen=True)
class DealItem:
    """One NSE bulk/block-deal row (from a downloaded NSE deal file)."""

    symbol: str
    client_name: str
    buy_sell: str | None
    qty: str | None
    value: str | None
    deal_date: date | None


@dataclass(frozen=True)
class AnnItem:
    """One BSE corporate announcement (from a downloaded BSE announcement file)."""

    scrip_cd: str
    headline: str
    dt_tm: datetime | None
    attachment: str | None


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
        if not st.nse_symbol:
            continue
        sym = st.nse_symbol.upper()
        if sym not in tokens:
            continue
        if sym in SYMBOL_BLOCKLIST:
            sn = _short_name(st.company_name)
            has_ctx = any(cw in text for cw in _CONTEXT_WORDS) or (
                len(sn.split()) >= 2 and sn in text
            )
            if not has_ctx:
                continue
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


# ---------------------------------------------------------------------------
# Deal / announcement file parsing (permitted local-file ingest — NSE/BSE
# website scraping is barred by CLAUDE.md §2 rule 5 / §12).
# ---------------------------------------------------------------------------
def _records(payload: Any, *keys: str) -> list[dict[str, Any]]:
    """Pull the row list from a parsed JSON file (bare array or {key: [...]})."""
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for k in keys:
            val = payload.get(k)
            if isinstance(val, list):
                return [r for r in val if isinstance(r, dict)]
    return []


def _first(rec: dict[str, Any], *keys: str) -> str | None:
    for k in keys:
        v = rec.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return None


def _parse_ddmonyyyy(value: str | None) -> date | None:
    if not value:
        return None
    for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    s = value.strip()
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        pass
    for fmt in ("%d %b %Y %H:%M:%S", "%d-%b-%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def parse_deals_json(text: str) -> list[DealItem]:
    """Parse an NSE bulk/block-deal file (bare array or {"data": [...]})."""
    records = _records(json.loads(text), "data")
    out: list[DealItem] = []
    for rec in records:
        symbol = _first(rec, "symbol", "BD_SYMBOL")
        if not symbol:
            continue
        out.append(
            DealItem(
                symbol=symbol.upper(),
                client_name=_first(rec, "name", "BD_CLIENT_NAME") or "",
                buy_sell=_first(rec, "buySell", "BD_BUY_SELL"),
                qty=_first(rec, "qty", "BD_QTY_TRD"),
                value=_first(rec, "value", "BD_TP_WATP"),
                deal_date=_parse_ddmonyyyy(_first(rec, "BD_DT_DATE", "date")),
            )
        )
    return out


def parse_bse_announcements_json(text: str) -> list[AnnItem]:
    """Parse a BSE announcement file (bare array or {"Table": [...]})."""
    records = _records(json.loads(text), "Table", "data")
    out: list[AnnItem] = []
    for rec in records:
        scrip = _first(rec, "SCRIP_CD", "scrip_cd")
        headline = _first(rec, "HEADLINE", "headline", "NEWSSUB")
        if not scrip or not headline:
            continue
        out.append(
            AnnItem(
                scrip_cd=scrip,
                headline=headline,
                dt_tm=_parse_dt(_first(rec, "DT_TM", "dt_tm", "NEWS_DT")),
                attachment=_first(rec, "ATTACHMENTNAME", "attachment"),
            )
        )
    return out


def deal_to_article(
    item: DealItem,
    source_name: str,
    deal_type: str,
    isin_by_symbol: dict[str, str],
) -> RawArticle:
    """Build a news article from a deal row; ISIN via nse_symbol lookup."""
    qty = item.qty or "?"
    headline = f"{item.client_name} {deal_type} deal in {item.symbol} — {qty} shares"
    parts = [
        source_name,
        item.deal_date.isoformat() if item.deal_date else "",
        item.symbol,
        item.buy_sell or "",
        item.client_name,
        qty,
    ]
    published = (
        datetime(item.deal_date.year, item.deal_date.month, item.deal_date.day, tzinfo=UTC)
        if item.deal_date
        else None
    )
    summary = (
        f"{item.buy_sell or ''} {qty} @ {item.value or '?'}".strip()
        if (item.buy_sell or item.value)
        else None
    )
    return RawArticle(
        headline=headline,
        summary=summary,
        source_name=source_name,
        source_url=":".join(parts),
        published_at=published,
        isin=isin_by_symbol.get(item.symbol.upper()),
    )


def announcement_to_article(
    item: AnnItem, isin_by_bse_code: dict[str, str]
) -> RawArticle:
    """Build a news article from a BSE announcement; ISIN via BSE-code lookup."""
    dt_part = item.dt_tm.isoformat() if item.dt_tm else ""
    return RawArticle(
        headline=item.headline,
        summary=(f"attachment: {item.attachment}" if item.attachment else None),
        source_name="bse_announcement",
        source_url=f"bse_announcement:{item.scrip_cd}:{dt_part}:{item.headline[:80]}",
        published_at=item.dt_tm,
        isin=isin_by_bse_code.get(str(item.scrip_cd)),
    )


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
        self,
        *,
        sources: tuple[str, ...] = ("rss",),
        dry_run: bool = False,
        nse_bulk_path: str | None = None,
        nse_block_path: str | None = None,
        bse_path: str | None = None,
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
        if {"nse-deals", "all"} & want:
            symbol_map = await self._load_symbol_isin_map()
            for path, src, dtype in (
                (nse_bulk_path, "nse_bulk_deal", "bulk"),
                (nse_block_path, "nse_block_deal", "block"),
            ):
                for deal in await self.fetch_deals_file(path):
                    raw.append(deal_to_article(deal, src, dtype, symbol_map))
        if {"bse-announcements", "all"} & want:
            bse_map = await self._load_bse_isin_map()
            for ann in await self.fetch_bse_file(bse_path):
                raw.append(announcement_to_article(ann, bse_map))

        deduped = dedup_by_url(raw)
        known = await self._load_known_stocks()

        rows: list[dict[str, Any]] = []
        sample: list[tuple[str, str | None]] = []
        now = datetime.now(UTC)
        matched = 0
        for a in deduped:
            isin = a.isin if a.isin is not None else match_to_isin(
                a.headline, a.summary, known
            )
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

    async def fetch_deals_file(self, path: str | None) -> list[DealItem]:
        """Parse a downloaded NSE bulk/block-deal file. Resilient: [] on issue."""
        text = await self._read_text(path, "deals")
        if text is None:
            return []
        try:
            return parse_deals_json(text)
        except (ValueError, KeyError) as exc:
            log.warning("news.deals.parse_failed", path=path, error=str(exc))
            return []

    async def fetch_bse_file(self, path: str | None) -> list[AnnItem]:
        """Parse a downloaded BSE announcement file. Resilient: [] on issue."""
        text = await self._read_text(path, "bse")
        if text is None:
            return []
        try:
            return parse_bse_announcements_json(text)
        except (ValueError, KeyError) as exc:
            log.warning("news.bse.parse_failed", path=path, error=str(exc))
            return []

    @staticmethod
    async def _read_text(path: str | None, label: str) -> str | None:
        import asyncio

        if not path:
            log.warning("news.file.no_path", source=label)
            return None
        return await asyncio.to_thread(_read_file_sync, path, label)

    async def _load_symbol_isin_map(self) -> dict[str, str]:
        from sqlalchemy import select

        from backend.db.models import Stock
        from backend.db.session import SessionLocal

        async with SessionLocal() as session:
            rows = (
                await session.execute(
                    select(Stock.nse_symbol, Stock.isin).where(
                        Stock.delisted_on.is_(None), Stock.nse_symbol.is_not(None)
                    )
                )
            ).all()
        return {sym.upper(): isin for sym, isin in rows}

    async def _load_bse_isin_map(self) -> dict[str, str]:
        """BSE scrip code/symbol -> ISIN from current stock_identifiers rows."""
        from sqlalchemy import select

        from backend.db.models import StockIdentifier
        from backend.db.session import SessionLocal

        async with SessionLocal() as session:
            rows = (
                await session.execute(
                    select(StockIdentifier.value, StockIdentifier.isin).where(
                        StockIdentifier.identifier_type == "bse_symbol",
                        StockIdentifier.effective_to.is_(None),
                    )
                )
            ).all()
        return {str(value): isin for value, isin in rows}


def _read_file_sync(path: str, label: str) -> str | None:
    from pathlib import Path

    p = Path(path)
    if not p.exists():
        log.warning("news.file.missing", source=label, path=path)
        return None
    try:
        return p.read_text(encoding="utf-8")
    except OSError as exc:
        log.warning("news.file.read_failed", source=label, path=path, error=str(exc))
        return None


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
