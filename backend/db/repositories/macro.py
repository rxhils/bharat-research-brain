"""Data access for `macro_signals` (Chunk 4.1).

`bulk_upsert` is idempotent via ON CONFLICT (indicator, computed_date) DO UPDATE
— re-running the agent on the same day overwrites with fresh values.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import MacroSignal

_UPSERT_COLS = ("value", "signal", "regime_weight", "source")


async def bulk_upsert(session: AsyncSession, rows: Sequence[dict[str, Any]]) -> int:
    """Insert/update macro rows. Returns affected count. Caller commits."""
    if not rows:
        return 0
    stmt = pg_insert(MacroSignal).values(list(rows))
    stmt = stmt.on_conflict_do_update(
        index_elements=["indicator", "computed_date"],
        set_={c: getattr(stmt.excluded, c) for c in _UPSERT_COLS}
        | {"fetched_at": func.now()},
    )
    result = await session.execute(stmt)
    return result.rowcount or 0


async def fetch_latest(session: AsyncSession) -> list[MacroSignal]:
    """All indicators for the most recent computed_date, indicator-ordered."""
    latest_date = select(func.max(MacroSignal.computed_date)).scalar_subquery()
    stmt = (
        select(MacroSignal)
        .where(MacroSignal.computed_date == latest_date)
        .order_by(MacroSignal.indicator)
    )
    return list((await session.execute(stmt)).scalars().all())
