"""Data access for the Risk Agent (Chunk 4.2).

All reads aggregate existing tables — no external source. `bulk_upsert` is
idempotent via ON CONFLICT (isin, computed_date) DO UPDATE.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import (
    MacroSignal,
    NewsArticle,
    PriceEodAdjusted,
    RiskSignal,
    Stock,
    TechnicalSignal,
)

_UPSERT_COLS = (
    "atr_pct",
    "volatility_flag",
    "news_spike",
    "days_to_results",
    "risk_score",
    "source",
)


async def fetch_active_isins(
    session: AsyncSession, *, isin: str | None = None
) -> list[str]:
    stmt = select(Stock.isin).where(Stock.delisted_on.is_(None))
    if isin is not None:
        stmt = stmt.where(Stock.isin == isin)
    return [i for (i,) in (await session.execute(stmt)).all()]


async def fetch_atr_pct(
    session: AsyncSession, *, isin: str | None = None
) -> dict[str, Decimal | None]:
    """ATR as % of latest price per isin: atr_14 / latest adj_close * 100."""
    atr_stmt = (
        select(TechnicalSignal.isin, TechnicalSignal.atr_14)
        .distinct(TechnicalSignal.isin)
        .order_by(TechnicalSignal.isin, TechnicalSignal.computed_date.desc())
    )
    price_stmt = (
        select(PriceEodAdjusted.isin, PriceEodAdjusted.adj_close)
        .distinct(PriceEodAdjusted.isin)
        .order_by(PriceEodAdjusted.isin, PriceEodAdjusted.trade_date.desc())
    )
    if isin is not None:
        atr_stmt = atr_stmt.where(TechnicalSignal.isin == isin)
        price_stmt = price_stmt.where(PriceEodAdjusted.isin == isin)

    atr_by = {i: a for i, a in (await session.execute(atr_stmt)).all()}
    price_by = {i: p for i, p in (await session.execute(price_stmt)).all()}

    out: dict[str, Decimal | None] = {}
    for i, atr in atr_by.items():
        price = price_by.get(i)
        out[i] = (atr / price * 100) if (atr is not None and price) else None
    return out


async def fetch_news_counts(
    session: AsyncSession, *, isin: str | None = None
) -> dict[str, tuple[int, Decimal]]:
    """Per isin: (count in last 24h, 7-day daily average)."""
    now = datetime.now(UTC)
    cut_24h = now - timedelta(hours=24)
    cut_7d = now - timedelta(days=7)
    stmt = (
        select(
            NewsArticle.isin,
            func.count().filter(NewsArticle.published_at >= cut_24h),
            func.count().filter(NewsArticle.published_at >= cut_7d),
        )
        .where(NewsArticle.isin.is_not(None))
        .group_by(NewsArticle.isin)
    )
    if isin is not None:
        stmt = stmt.where(NewsArticle.isin == isin)
    out: dict[str, tuple[int, Decimal]] = {}
    for i, c24, c7 in (await session.execute(stmt)).all():
        out[i] = (int(c24), Decimal(int(c7)) / 7)
    return out


async def fetch_macro_regime(session: AsyncSession) -> str:
    """Latest market regime from macro_signals (default neutral)."""
    stmt = (
        select(MacroSignal.signal)
        .where(MacroSignal.indicator == "regime")
        .order_by(MacroSignal.computed_date.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none() or "neutral"


async def bulk_upsert(session: AsyncSession, rows: Sequence[dict[str, Any]]) -> int:
    """Insert/update risk rows. Returns affected count. Caller commits."""
    if not rows:
        return 0
    stmt = pg_insert(RiskSignal).values(list(rows))
    stmt = stmt.on_conflict_do_update(
        index_elements=["isin", "computed_date"],
        set_={c: getattr(stmt.excluded, c) for c in _UPSERT_COLS}
        | {"computed_at": func.now()},
    )
    result = await session.execute(stmt)
    return result.rowcount or 0


async def fetch_signals(
    session: AsyncSession, *, limit: int = 20, flag: str | None = None
) -> list[tuple[RiskSignal, str | None]]:
    """Latest-date risk rows joined to nse_symbol, highest risk first."""
    latest_date = select(func.max(RiskSignal.computed_date)).scalar_subquery()
    stmt = (
        select(RiskSignal, Stock.nse_symbol)
        .join(Stock, Stock.isin == RiskSignal.isin)
        .where(RiskSignal.computed_date == latest_date)
    )
    if flag is not None:
        stmt = stmt.where(RiskSignal.volatility_flag == flag)
    stmt = stmt.order_by(RiskSignal.risk_score.desc()).limit(limit)
    return [(row, sym) for row, sym in (await session.execute(stmt)).all()]
