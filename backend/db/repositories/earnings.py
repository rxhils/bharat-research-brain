"""Data access for `earnings_calendar` (Build E).

`bulk_upsert` is idempotent via ON CONFLICT (isin, result_date) DO UPDATE.
`fetch_upcoming` returns the nearest upcoming result date per stock within a
calendar-day horizon, used by the Risk Agent to derive `days_to_results`.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import EarningsCalendar, Stock
from backend.db.repositories._helpers import today_ist

_BATCH = 500

_UPSERT_COLS = ("quarter", "status", "source")


async def bulk_upsert(session: AsyncSession, rows: Sequence[dict[str, Any]]) -> int:
    """Insert/update earnings rows. Returns affected count. Caller commits."""
    affected = 0
    for i in range(0, len(rows), _BATCH):
        batch = list(rows[i : i + _BATCH])
        stmt = pg_insert(EarningsCalendar).values(batch)
        stmt = stmt.on_conflict_do_update(
            index_elements=["isin", "result_date"],
            set_={c: getattr(stmt.excluded, c) for c in _UPSERT_COLS}
            | {"fetched_at": func.now()},
        )
        result = await session.execute(stmt)
        affected += result.rowcount or 0
    return affected


async def fetch_upcoming(
    session: AsyncSession, *, days_ahead: int = 30
) -> dict[str, date]:
    """{isin: nearest upcoming result_date} within `days_ahead` calendar days.

    Uses IST 'today' (CLAUDE.md §4) — not pg CURRENT_DATE (UTC) — to avoid the
    date-boundary trap noted in lesson 4.9.
    """
    today = today_ist()
    horizon = today + timedelta(days=days_ahead)
    stmt = (
        select(EarningsCalendar.isin, func.min(EarningsCalendar.result_date))
        .where(
            EarningsCalendar.result_date >= today,
            EarningsCalendar.result_date <= horizon,
        )
        .group_by(EarningsCalendar.isin)
    )
    return {
        isin: result_date
        for isin, result_date in (await session.execute(stmt)).all()
    }


async def fetch_recent(
    session: AsyncSession, *, days: int = 14, limit: int = 20
) -> list[tuple[str | None, date, str | None, str]]:
    """(nse_symbol, result_date, quarter, status) for upcoming results, soonest first."""
    today = today_ist()
    horizon = today + timedelta(days=days)
    stmt = (
        select(
            Stock.nse_symbol,
            EarningsCalendar.result_date,
            EarningsCalendar.quarter,
            EarningsCalendar.status,
        )
        .join(Stock, Stock.isin == EarningsCalendar.isin)
        .where(
            EarningsCalendar.result_date >= today,
            EarningsCalendar.result_date <= horizon,
        )
        .order_by(EarningsCalendar.result_date)
        .limit(limit)
    )
    return [tuple(r) for r in (await session.execute(stmt)).all()]
