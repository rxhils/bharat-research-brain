"""Data access for the Technical Agent.

Loads the adjusted OHLC series (for indicators) and the raw delivery series
(for the 30-day delivery average), and upserts computed signals into
`technical_signals` (ON CONFLICT (isin, computed_date) DO UPDATE).
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import PriceEod, PriceEodAdjusted, TechnicalSignal

_BATCH = 1000


async def load_adj_series(
    session: AsyncSession, isin: str
) -> list[tuple[date, Decimal | None, Decimal | None, Decimal | None, Decimal | None]]:
    """(trade_date, adj_open, adj_high, adj_low, adj_close) ascending."""
    stmt = (
        select(
            PriceEodAdjusted.trade_date,
            PriceEodAdjusted.adj_open,
            PriceEodAdjusted.adj_high,
            PriceEodAdjusted.adj_low,
            PriceEodAdjusted.adj_close,
        )
        .where(PriceEodAdjusted.isin == isin)
        .order_by(PriceEodAdjusted.trade_date.asc())
    )
    return [tuple(r) for r in (await session.execute(stmt)).all()]


async def load_delivery_series(
    session: AsyncSession, isin: str
) -> list[tuple[date, Decimal | None]]:
    """(trade_date, delivery_pct) ascending. delivery_pct may be NULL (UDiFF)."""
    stmt = (
        select(PriceEod.trade_date, PriceEod.delivery_pct)
        .where(PriceEod.isin == isin)
        .order_by(PriceEod.trade_date.asc())
    )
    return [(d, dp) for d, dp in (await session.execute(stmt)).all()]


async def bulk_upsert(session: AsyncSession, rows: Sequence[dict[str, Any]]) -> int:
    """Insert/update technical_signals rows. Returns affected count. Caller commits."""
    affected = 0
    cols = (
        "rsi_14",
        "ema_20",
        "ema_200",
        "macd_line",
        "macd_signal",
        "macd_hist",
        "atr_14",
        "avg_delivery_pct_30d",
        "price_vs_ema200",
        "ema_cross",
        "source",
    )
    for i in range(0, len(rows), _BATCH):
        batch = list(rows[i : i + _BATCH])
        stmt = pg_insert(TechnicalSignal).values(batch)
        stmt = stmt.on_conflict_do_update(
            index_elements=["isin", "computed_date"],
            set_={c: getattr(stmt.excluded, c) for c in cols}
            | {"computed_at": func.now()},
        )
        result = await session.execute(stmt)
        affected += result.rowcount or 0
    return affected


async def fetch_signals(
    session: AsyncSession, *, isin: str, limit: int = 3
) -> list[TechnicalSignal]:
    stmt = (
        select(TechnicalSignal)
        .where(TechnicalSignal.isin == isin)
        .order_by(TechnicalSignal.computed_date.desc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())
