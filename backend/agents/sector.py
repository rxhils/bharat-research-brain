"""Sector Agent (Chunk 3.5) — sector-level momentum signals.

Pure SQL aggregation over data already in the database (prices_eod_adjusted,
technical_signals, news_articles) — NO external API calls. For each canonical
sector it computes average RSI, the % of constituents above their 200-day EMA,
average 7- and 30-trading-day price momentum, and a 30-day news-sentiment
summary, then classifies the sector as leading / neutral / lagging.

The aggregation math is pure (testable with synthetic data); only
`compute_sector` / `run_all` touch the database.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_EVEN, Decimal

import structlog

from backend.db.repositories._helpers import today_ist

log = structlog.get_logger()

SOURCE = "sector_agent"
_SENTIMENT_WINDOW_DAYS = 30
_Q4 = Decimal("0.0001")

# Signal thresholds (CLAUDE.md / chunk spec).
_RSI_LEAD = Decimal("55")
_PCT_LEAD = Decimal("60")
_RSI_LAG = Decimal("45")
_PCT_LAG = Decimal("40")
_MOM_LAG = Decimal("-1.0")


@dataclass(frozen=True)
class StockData:
    """One constituent's inputs to the sector aggregate."""

    rsi_14: Decimal | None
    above_ema200: bool | None
    ret_7d: Decimal | None
    ret_30d: Decimal | None


@dataclass(frozen=True)
class SectorRow:
    sector: str
    computed_date: date
    stock_count: int
    avg_rsi_14: Decimal | None
    pct_above_ema200: Decimal | None
    momentum_7d: Decimal | None
    momentum_30d: Decimal | None
    avg_sentiment_score: Decimal | None
    bull_article_pct: Decimal | None
    signal: str
    source: str = SOURCE


# ---------------------------------------------------------------------------
# Pure aggregation helpers
# ---------------------------------------------------------------------------
def pct_return(latest: Decimal | None, past: Decimal | None) -> Decimal | None:
    """Percentage return from `past` to `latest`. None if either is missing/zero."""
    if latest is None or past is None or past == 0:
        return None
    return (latest - past) / past * 100


def mean_or_none(values: Sequence[Decimal | None]) -> Decimal | None:
    nums = [v for v in values if v is not None]
    if not nums:
        return None
    return sum(nums, Decimal(0)) / len(nums)


def pct_true(flags: Sequence[bool | None]) -> Decimal:
    """Percentage of True among non-None flags. 0 when none are present."""
    vals = [f for f in flags if f is not None]
    if not vals:
        return Decimal(0)
    return Decimal(sum(1 for f in vals if f)) / len(vals) * 100


def bull_pct(labels: Sequence[str]) -> Decimal | None:
    if not labels:
        return None
    return Decimal(sum(1 for label in labels if label == "bull")) / len(labels) * 100


def classify_signal(
    avg_rsi: Decimal | None,
    pct_above_ema200: Decimal | None,
    momentum_7d: Decimal | None,
) -> str:
    """leading / lagging / neutral per the chunk's threshold rules."""
    if (
        avg_rsi is not None
        and pct_above_ema200 is not None
        and momentum_7d is not None
        and avg_rsi > _RSI_LEAD
        and pct_above_ema200 > _PCT_LEAD
        and momentum_7d > 0
    ):
        return "leading"
    if (
        (avg_rsi is not None and avg_rsi < _RSI_LAG)
        or (pct_above_ema200 is not None and pct_above_ema200 < _PCT_LAG)
        or (momentum_7d is not None and momentum_7d < _MOM_LAG)
    ):
        return "lagging"
    return "neutral"


def _q4(value: Decimal | None) -> Decimal | None:
    return None if value is None else value.quantize(_Q4, rounding=ROUND_HALF_EVEN)


def build_sector_row(
    sector: str,
    computed_date: date,
    stocks: Sequence[StockData],
    sentiment_scores: Sequence[Decimal],
    sentiment_labels: Sequence[str],
) -> SectorRow:
    """Aggregate constituent data into one classified SectorRow."""
    avg_rsi = mean_or_none([s.rsi_14 for s in stocks])
    pct_above = pct_true([s.above_ema200 for s in stocks])
    mom_7d = mean_or_none([s.ret_7d for s in stocks])
    mom_30d = mean_or_none([s.ret_30d for s in stocks])
    avg_sent = mean_or_none(list(sentiment_scores))
    bull = bull_pct(sentiment_labels)
    # An empty sector (no constituents) has no signal — never "lagging".
    signal = "neutral" if not stocks else classify_signal(avg_rsi, pct_above, mom_7d)
    return SectorRow(
        sector=sector,
        computed_date=computed_date,
        stock_count=len(stocks),
        avg_rsi_14=_q4(avg_rsi),
        pct_above_ema200=_q4(pct_above),
        momentum_7d=_q4(mom_7d),
        momentum_30d=_q4(mom_30d),
        avg_sentiment_score=_q4(avg_sent),
        bull_article_pct=_q4(bull),
        signal=signal,
        source=SOURCE,
    )


# ---------------------------------------------------------------------------
# DB-backed agent
# ---------------------------------------------------------------------------
@dataclass
class SectorResult:
    computed_date: date
    rows: list[SectorRow]
    rows_upserted: int = 0


class SectorAgent:
    name = "sector"

    async def compute_sector(self, sector: str, as_of_date: date) -> SectorRow:
        from backend.db.repositories import sector as sector_repo
        from backend.db.session import SessionLocal

        async with SessionLocal() as session:
            momentum = await sector_repo.fetch_sector_momentum(
                session, sector=sector, as_of=as_of_date
            )
            technicals = await sector_repo.fetch_sector_technicals(
                session, sector=sector, as_of=as_of_date
            )
            cutoff = as_of_date - timedelta(days=_SENTIMENT_WINDOW_DAYS)
            sentiment = await sector_repo.fetch_sector_sentiment(
                session, sector=sector, since=cutoff
            )

        tech_by_isin = {isin: (rsi, pve) for isin, rsi, pve in technicals}
        stocks: list[StockData] = []
        for isin, latest, c7, c30 in momentum:
            rsi, pve = tech_by_isin.get(isin, (None, None))
            above = None if pve is None else (pve == "above")
            stocks.append(
                StockData(
                    rsi_14=rsi,
                    above_ema200=above,
                    ret_7d=pct_return(latest, c7),
                    ret_30d=pct_return(latest, c30),
                )
            )

        scores = [s for s, _ in sentiment if s is not None]
        labels = [label for _, label in sentiment if label is not None]
        return build_sector_row(sector, as_of_date, stocks, scores, labels)

    async def run_all(
        self, *, as_of_date: date | None = None, dry_run: bool = False
    ) -> SectorResult:
        from backend.db.repositories import sector as sector_repo
        from backend.db.session import SessionLocal

        as_of = as_of_date or today_ist()
        async with SessionLocal() as session:
            sectors = await sector_repo.fetch_sectors(session)

        rows = [await self.compute_sector(s, as_of) for s in sectors]
        result = SectorResult(computed_date=as_of, rows=rows)

        if not dry_run and rows:
            payload = [_row_to_dict(r) for r in rows]
            async with SessionLocal() as session:
                result.rows_upserted = await sector_repo.bulk_upsert(session, payload)
                await session.commit()

        log.info(
            "sector.run.done",
            computed_date=as_of.isoformat(),
            sectors=len(rows),
            upserted=result.rows_upserted,
            dry_run=dry_run,
        )
        return result


def _row_to_dict(row: SectorRow) -> dict[str, object]:
    return {
        "sector": row.sector,
        "computed_date": row.computed_date,
        "stock_count": row.stock_count,
        "avg_rsi_14": row.avg_rsi_14,
        "pct_above_ema200": row.pct_above_ema200,
        "momentum_7d": row.momentum_7d,
        "momentum_30d": row.momentum_30d,
        "avg_sentiment_score": row.avg_sentiment_score,
        "bull_article_pct": row.bull_article_pct,
        "signal": row.signal,
        "source": row.source,
    }
