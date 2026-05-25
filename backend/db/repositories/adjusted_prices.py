"""Data access for `prices_eod_adjusted` + raw-bar loading for adjustment.

`bulk_upsert` is idempotent via ON CONFLICT (trade_date, isin) DO UPDATE so
re-running `prices adjust` overwrites in place. `fetch_raw_bars` loads a
stock's full raw OHLCV series (ascending) to feed the pure adjust engine.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.adjusted_prices import RawBar
from backend.db.models import PriceEod, PriceEodAdjusted

_BATCH = 1000


async def fetch_raw_bars(session: AsyncSession, isin: str) -> list[RawBar]:
    stmt = (
        select(
            PriceEod.trade_date,
            PriceEod.open,
            PriceEod.high,
            PriceEod.low,
            PriceEod.close,
            PriceEod.volume,
        )
        .where(PriceEod.isin == isin)
        .order_by(PriceEod.trade_date.asc())
    )
    return [
        RawBar(trade_date=d, open=o, high=h, low=low_, close=c, volume=v)
        for d, o, h, low_, c, v in (await session.execute(stmt)).all()
    ]


async def bulk_upsert(session: AsyncSession, rows: Sequence[dict[str, Any]]) -> int:
    """Insert or update adjusted rows. Returns affected row count. Caller commits."""
    affected = 0
    for i in range(0, len(rows), _BATCH):
        batch = list(rows[i : i + _BATCH])
        stmt = pg_insert(PriceEodAdjusted).values(batch)
        stmt = stmt.on_conflict_do_update(
            index_elements=["trade_date", "isin"],
            set_={
                "adj_open": stmt.excluded.adj_open,
                "adj_high": stmt.excluded.adj_high,
                "adj_low": stmt.excluded.adj_low,
                "adj_close": stmt.excluded.adj_close,
                "adj_volume": stmt.excluded.adj_volume,
                "adj_factor": stmt.excluded.adj_factor,
                "source": stmt.excluded.source,
                "computed_at": func.now(),
            },
        )
        result = await session.execute(stmt)
        affected += result.rowcount or 0
    return affected


async def get_adjusted(
    session: AsyncSession, isin: str, start: date, end: date
) -> list[PriceEodAdjusted]:
    stmt = (
        select(PriceEodAdjusted)
        .where(
            PriceEodAdjusted.isin == isin,
            PriceEodAdjusted.trade_date >= start,
            PriceEodAdjusted.trade_date <= end,
        )
        .order_by(PriceEodAdjusted.trade_date.asc())
    )
    return list((await session.execute(stmt)).scalars().all())
