"""Data access for `prices_eod` (end-of-day OHLCV).

`bulk_insert` is idempotent via INSERT ... ON CONFLICT (trade_date, isin)
DO NOTHING, batched 1000 rows per statement, and returns the count actually
inserted. The Price Agent owns the diff/quality decisions; this layer only
reads presence and writes.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import distinct, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.data_sources.nse_bhavcopy import BhavRow
from backend.db.models import PriceEod

_BATCH = 1000
# Column stores turnover in rupees; bhavcopy gives crores → ×1e7.
_RUPEES_PER_CRORE = Decimal(10_000_000)


async def get_latest_date(session: AsyncSession, isin: str) -> date | None:
    """Most recent trade_date we hold for `isin`, or None."""
    stmt = (
        select(PriceEod.trade_date)
        .where(PriceEod.isin == isin)
        .order_by(PriceEod.trade_date.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_dates_present(
    session: AsyncSession, start: date, end: date
) -> set[date]:
    """Distinct trade_dates with ANY row in [start, end]. One query."""
    stmt = select(distinct(PriceEod.trade_date)).where(
        PriceEod.trade_date >= start,
        PriceEod.trade_date <= end,
    )
    return set((await session.execute(stmt)).scalars().all())


async def bulk_insert(
    session: AsyncSession,
    rows: Sequence[BhavRow],
    *,
    ingestion_run_id: int,
    source: str = "nse_bhavcopy",
) -> int:
    """Insert rows with ON CONFLICT DO NOTHING. Returns rows actually inserted.

    Caller commits. Rows missing a trade_date are skipped defensively.
    """
    inserted = 0
    payload = [
        {
            "trade_date": r.trade_date,
            "isin": r.isin,
            "open": r.open,
            "high": r.high,
            "low": r.low,
            "close": r.close,
            "volume": r.volume,
            "turnover_inr": (
                r.value_inr_cr * _RUPEES_PER_CRORE
                if r.value_inr_cr is not None
                else None
            ),
            "delivery_qty": r.delivery_qty,
            "delivery_pct": r.delivery_pct,
            "trade_count": r.trades_count,
            "source": source,
            "ingestion_run_id": ingestion_run_id,
        }
        for r in rows
        if r.trade_date is not None
    ]
    for i in range(0, len(payload), _BATCH):
        batch = payload[i : i + _BATCH]
        stmt = pg_insert(PriceEod).values(batch).on_conflict_do_nothing(
            index_elements=["trade_date", "isin"]
        )
        result = await session.execute(stmt)
        inserted += result.rowcount or 0
    return inserted
