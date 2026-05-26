"""Data access for `promoter_signals` (Chunk 4.9 improvement 5).

`bulk_upsert` is idempotent via ON CONFLICT (isin, report_date) DO UPDATE —
re-ingesting the same quarter overwrites with fresh values. `fetch_latest_flags`
feeds the Risk Agent the most recent pledge_risk_flag per stock.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import PromoterSignal, Stock

_BATCH = 500

_UPSERT_COLS = (
    "promoter_holding_pct",
    "promoter_pledged_pct",
    "pledge_risk_flag",
    "source",
)


async def fetch_known_isins(
    session: AsyncSession, isins: Sequence[str]
) -> set[str]:
    """Subset of `isins` that exist in `stocks` (FK guard before upsert)."""
    if not isins:
        return set()
    stmt = select(Stock.isin).where(Stock.isin.in_(list(isins)))
    return set((await session.execute(stmt)).scalars().all())


async def bulk_upsert(session: AsyncSession, rows: Sequence[dict[str, Any]]) -> int:
    """Insert/update promoter rows. Returns affected count. Caller commits."""
    affected = 0
    for i in range(0, len(rows), _BATCH):
        batch = list(rows[i : i + _BATCH])
        stmt = pg_insert(PromoterSignal).values(batch)
        stmt = stmt.on_conflict_do_update(
            index_elements=["isin", "report_date"],
            set_={c: getattr(stmt.excluded, c) for c in _UPSERT_COLS}
            | {"fetched_at": func.now()},
        )
        result = await session.execute(stmt)
        affected += result.rowcount or 0
    return affected


async def fetch_latest_flags(session: AsyncSession) -> dict[str, str]:
    """Latest pledge_risk_flag per isin (most recent report_date)."""
    stmt = (
        select(PromoterSignal.isin, PromoterSignal.pledge_risk_flag)
        .distinct(PromoterSignal.isin)
        .order_by(PromoterSignal.isin, PromoterSignal.report_date.desc())
    )
    return {i: flag for i, flag in (await session.execute(stmt)).all()}


async def fetch_signals(
    session: AsyncSession,
    *,
    isin: str | None = None,
    flag: str | None = None,
    limit: int = 50,
) -> list[tuple[PromoterSignal, str | None]]:
    """Latest-date promoter rows joined to nse_symbol, highest pledge first."""
    latest_date = select(func.max(PromoterSignal.report_date)).scalar_subquery()
    stmt = (
        select(PromoterSignal, Stock.nse_symbol)
        .join(Stock, Stock.isin == PromoterSignal.isin)
        .where(PromoterSignal.report_date == latest_date)
    )
    if isin is not None:
        stmt = stmt.where(PromoterSignal.isin == isin)
    if flag is not None:
        stmt = stmt.where(PromoterSignal.pledge_risk_flag == flag)
    stmt = stmt.order_by(PromoterSignal.promoter_pledged_pct.desc().nullslast())
    stmt = stmt.limit(limit)
    return [(row, sym) for row, sym in (await session.execute(stmt)).all()]
