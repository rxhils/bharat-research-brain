"""Data access for the Nightly Scheduler (Chunk 4.6).

`upsert_run` records one row per run_date (ON CONFLICT (run_date) DO UPDATE).
`is_trading_day` gates the pipeline on the NSE trading calendar.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import PipelineRun, TradingCalendar

_UPSERT_COLS = (
    "started_at",
    "finished_at",
    "status",
    "agents_run",
    "total_duration_seconds",
    "error_message",
)


async def is_trading_day(
    session: AsyncSession, day: date, *, exchange: str = "NSE"
) -> bool:
    """True if the calendar marks the day open (or has no row — fail open)."""
    stmt = select(TradingCalendar.is_open).where(
        TradingCalendar.trade_date == day, TradingCalendar.exchange == exchange
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    return True if row is None else bool(row)


async def upsert_run(session: AsyncSession, row: dict[str, Any]) -> int:
    """Insert/update the pipeline run for its run_date. Caller commits."""
    stmt = pg_insert(PipelineRun).values([row])
    stmt = stmt.on_conflict_do_update(
        index_elements=["run_date"],
        set_={c: getattr(stmt.excluded, c) for c in _UPSERT_COLS},
    )
    result = await session.execute(stmt)
    return result.rowcount or 0


async def fetch_runs(
    session: AsyncSession, *, limit: int = 10
) -> Sequence[PipelineRun]:
    stmt = select(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())
