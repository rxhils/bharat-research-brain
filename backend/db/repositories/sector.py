"""Data access for the Sector Agent (Chunk 3.5).

All reads aggregate existing tables — no external source. Momentum uses a
ROW_NUMBER window over prices_eod_adjusted (rn=1 latest, rn=8 = 7 trading days
ago, rn=31 = 30 trading days ago). `bulk_upsert` is idempotent via
ON CONFLICT (sector, computed_date) DO UPDATE.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import (
    NewsArticle,
    PriceEodAdjusted,
    SectorSignal,
    Stock,
    TechnicalSignal,
)

_UPSERT_COLS = (
    "stock_count",
    "avg_rsi_14",
    "pct_above_ema200",
    "momentum_7d",
    "momentum_30d",
    "avg_sentiment_score",
    "bull_article_pct",
    "signal",
    "source",
)


async def fetch_sectors(session: AsyncSession) -> list[str]:
    """Canonical non-null sector list from active stocks, alphabetical."""
    stmt = (
        select(Stock.sector)
        .where(Stock.delisted_on.is_(None), Stock.sector.is_not(None))
        .distinct()
        .order_by(Stock.sector)
    )
    return [s for (s,) in (await session.execute(stmt)).all()]


async def fetch_sector_momentum(
    session: AsyncSession, *, sector: str, as_of: date
) -> list[tuple[str, Decimal | None, Decimal | None, Decimal | None]]:
    """(isin, latest_close, close_7d_ago, close_30d_ago) per constituent."""
    ranked = (
        select(
            PriceEodAdjusted.isin.label("isin"),
            PriceEodAdjusted.adj_close.label("adj_close"),
            func.row_number()
            .over(
                partition_by=PriceEodAdjusted.isin,
                order_by=PriceEodAdjusted.trade_date.desc(),
            )
            .label("rn"),
        )
        .join(Stock, Stock.isin == PriceEodAdjusted.isin)
        .where(
            Stock.sector == sector,
            Stock.delisted_on.is_(None),
            PriceEodAdjusted.trade_date <= as_of,
        )
        .subquery()
    )
    stmt = (
        select(
            ranked.c.isin,
            func.max(case((ranked.c.rn == 1, ranked.c.adj_close))).label("latest"),
            func.max(case((ranked.c.rn == 8, ranked.c.adj_close))).label("c7"),
            func.max(case((ranked.c.rn == 31, ranked.c.adj_close))).label("c30"),
        )
        .where(ranked.c.rn.in_([1, 8, 31]))
        .group_by(ranked.c.isin)
    )
    return [
        (isin, latest, c7, c30)
        for isin, latest, c7, c30 in (await session.execute(stmt)).all()
    ]


async def fetch_sector_technicals(
    session: AsyncSession, *, sector: str, as_of: date
) -> list[tuple[str, Decimal | None, str | None]]:
    """(isin, rsi_14, price_vs_ema200) from the latest technical row per stock."""
    ranked = (
        select(
            TechnicalSignal.isin.label("isin"),
            TechnicalSignal.rsi_14.label("rsi_14"),
            TechnicalSignal.price_vs_ema200.label("pve"),
            func.row_number()
            .over(
                partition_by=TechnicalSignal.isin,
                order_by=TechnicalSignal.computed_date.desc(),
            )
            .label("rn"),
        )
        .join(Stock, Stock.isin == TechnicalSignal.isin)
        .where(
            Stock.sector == sector,
            Stock.delisted_on.is_(None),
            TechnicalSignal.computed_date <= as_of,
        )
        .subquery()
    )
    stmt = select(ranked.c.isin, ranked.c.rsi_14, ranked.c.pve).where(ranked.c.rn == 1)
    return [(isin, rsi, pve) for isin, rsi, pve in (await session.execute(stmt)).all()]


async def fetch_sector_sentiment(
    session: AsyncSession, *, sector: str, since: date
) -> list[tuple[Decimal | None, str | None]]:
    """(sentiment_score, sentiment_label) for the sector's articles since `since`."""
    stmt = (
        select(NewsArticle.sentiment_score, NewsArticle.sentiment_label)
        .join(Stock, Stock.isin == NewsArticle.isin)
        .where(
            Stock.sector == sector,
            Stock.delisted_on.is_(None),
            NewsArticle.sentiment_score.is_not(None),
            NewsArticle.published_at >= since,
        )
    )
    return [(score, label) for score, label in (await session.execute(stmt)).all()]


async def bulk_upsert(session: AsyncSession, rows: Sequence[dict[str, Any]]) -> int:
    """Insert/update sector_signals. Returns affected count. Caller commits."""
    if not rows:
        return 0
    stmt = pg_insert(SectorSignal).values(list(rows))
    stmt = stmt.on_conflict_do_update(
        index_elements=["sector", "computed_date"],
        set_={c: getattr(stmt.excluded, c) for c in _UPSERT_COLS}
        | {"computed_at": func.now()},
    )
    result = await session.execute(stmt)
    return result.rowcount or 0


async def fetch_signals(
    session: AsyncSession, *, limit: int = 20
) -> list[SectorSignal]:
    """Latest sector signals, most momentum first."""
    latest_date = select(func.max(SectorSignal.computed_date)).scalar_subquery()
    stmt = (
        select(SectorSignal)
        .where(SectorSignal.computed_date == latest_date)
        .order_by(SectorSignal.momentum_7d.desc().nullslast())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())
