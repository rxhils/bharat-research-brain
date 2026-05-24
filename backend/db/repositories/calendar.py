"""Data access for `trading_calendar` (read-only for the Price Agent).

The Price Agent asks which days the exchange was open in a date range so it
only attempts to download bhavcopies for real trading days (skips weekends
and holidays).
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import TradingCalendar


async def get_open_dates(
    session: AsyncSession,
    start: date,
    end: date,
    exchange: str = "NSE",
) -> list[date]:
    """Open trading days in [start, end] for `exchange`, ascending."""
    stmt = (
        select(TradingCalendar.trade_date)
        .where(
            TradingCalendar.trade_date >= start,
            TradingCalendar.trade_date <= end,
            TradingCalendar.exchange == exchange,
            TradingCalendar.is_open.is_(True),
        )
        .order_by(TradingCalendar.trade_date.asc())
    )
    return list((await session.execute(stmt)).scalars().all())
