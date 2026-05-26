"""Data access for `fundamental_signals` (Chunk 3.4).

`bulk_upsert` is idempotent via ON CONFLICT (isin, fetched_date) DO UPDATE — a
re-run on the same day overwrites with fresh values. `set_mcap_categories`
writes the derived bucket back to `stocks.mcap_category` through the ORM so the
`updated_at` trigger fires.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import FundamentalSignal, Stock

_BATCH = 500

_UPSERT_COLS = (
    "pe_ratio",
    "pb_ratio",
    "roe",
    "roce",
    "debt_to_equity",
    "revenue_growth",
    "earnings_growth",
    "profit_margin",
    "market_cap",
    "dividend_yield",
    "promoter_holding",
    "fifty_two_week_high",
    "fifty_two_week_low",
    "avg_volume_30d",
    "source",
)


async def fetch_active_symbols(
    session: AsyncSession, *, isin: str | None = None
) -> list[tuple[str, str]]:
    """(isin, nse_symbol) for active stocks with an NSE symbol; optional filter."""
    stmt = select(Stock.isin, Stock.nse_symbol).where(
        Stock.delisted_on.is_(None), Stock.nse_symbol.is_not(None)
    )
    if isin is not None:
        stmt = stmt.where(Stock.isin == isin)
    return [(i, sym) for i, sym in (await session.execute(stmt)).all()]


async def bulk_upsert(session: AsyncSession, rows: Sequence[dict[str, Any]]) -> int:
    """Insert/update fundamental_signals rows. Returns affected count. Caller commits."""
    affected = 0
    for i in range(0, len(rows), _BATCH):
        batch = list(rows[i : i + _BATCH])
        stmt = pg_insert(FundamentalSignal).values(batch)
        stmt = stmt.on_conflict_do_update(
            index_elements=["isin", "fetched_date"],
            set_={c: getattr(stmt.excluded, c) for c in _UPSERT_COLS}
            | {"fetched_at": func.now()},
        )
        result = await session.execute(stmt)
        affected += result.rowcount or 0
    return affected


async def latest_market_caps(session: AsyncSession) -> list[tuple[str, int | None]]:
    """(isin, market_cap) for the most recent fundamental_signals row per stock."""
    stmt = (
        select(FundamentalSignal.isin, FundamentalSignal.market_cap)
        .distinct(FundamentalSignal.isin)
        .order_by(FundamentalSignal.isin, FundamentalSignal.fetched_date.desc())
    )
    return [(i, mc) for i, mc in (await session.execute(stmt)).all()]


async def set_mcap_categories(
    session: AsyncSession, pairs: Sequence[tuple[str, str]]
) -> int:
    """UPDATE stocks.mcap_category per isin. Returns rows updated. Caller commits."""
    updated = 0
    for isin, category in pairs:
        result = await session.execute(
            update(Stock).where(Stock.isin == isin).values(mcap_category=category)
        )
        updated += result.rowcount or 0
    return updated


async def fetch_latest(
    session: AsyncSession, *, isin: str
) -> FundamentalSignal | None:
    stmt = (
        select(FundamentalSignal)
        .where(FundamentalSignal.isin == isin)
        .order_by(FundamentalSignal.fetched_date.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalars().first()
