"""Data access for `delivery_signals` (Build D).

`bulk_upsert` is idempotent via ON CONFLICT (isin, trade_date) DO UPDATE —
re-ingesting the same snapshot overwrites in place, row count unchanged.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import DeliverySignal, Stock

_BATCH = 500

_UPSERT_COLS = (
    "delivery_pct",
    "avg_5d_delivery_pct",
    "traded_volume",
    "delivery_volume",
    "source",
)


async def bulk_upsert(session: AsyncSession, rows: Sequence[dict[str, Any]]) -> int:
    """Insert/update delivery rows. Returns affected count. Caller commits."""
    affected = 0
    for i in range(0, len(rows), _BATCH):
        batch = list(rows[i : i + _BATCH])
        stmt = pg_insert(DeliverySignal).values(batch)
        stmt = stmt.on_conflict_do_update(
            index_elements=["isin", "trade_date"],
            set_={c: getattr(stmt.excluded, c) for c in _UPSERT_COLS}
            | {"fetched_at": func.now()},
        )
        result = await session.execute(stmt)
        affected += result.rowcount or 0
    return affected


async def fetch_recent(
    session: AsyncSession, *, isin: str | None = None, limit: int = 30
) -> list[tuple[str | None, date, Any, Any, int | None]]:
    """(nse_symbol, trade_date, delivery_pct, avg_5d_delivery_pct, traded_volume).

    Ordered by delivery_pct DESC (high delivery first) unless filtered to one
    stock, where the time series (trade_date DESC) is more useful.
    """
    stmt = select(
        Stock.nse_symbol,
        DeliverySignal.trade_date,
        DeliverySignal.delivery_pct,
        DeliverySignal.avg_5d_delivery_pct,
        DeliverySignal.traded_volume,
    ).join(Stock, Stock.isin == DeliverySignal.isin)
    if isin is not None:
        stmt = stmt.where(DeliverySignal.isin == isin).order_by(
            DeliverySignal.trade_date.desc()
        )
    else:
        stmt = stmt.order_by(DeliverySignal.delivery_pct.desc())
    stmt = stmt.limit(limit)
    return [tuple(r) for r in (await session.execute(stmt)).all()]
