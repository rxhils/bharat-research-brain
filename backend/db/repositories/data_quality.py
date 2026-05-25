"""Data access for the Data Quality Agent.

Read helpers feed the agent's pure checks; write helpers persist findings to
`data_quality_log`. All numeric/date values returned for JSONB context are
stringified here so findings stay JSON-serializable.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import DataQualityLog, PriceEod, Stock

_ZERO_VOL_LIMIT = 100_000


async def fetch_active_isins(session: AsyncSession) -> list[str]:
    stmt = select(Stock.isin).where(Stock.delisted_on.is_(None))
    return list((await session.execute(stmt)).scalars().all())


async def fetch_price_span(session: AsyncSession) -> tuple[date | None, date | None]:
    row = (
        await session.execute(
            select(func.min(PriceEod.trade_date), func.max(PriceEod.trade_date))
        )
    ).first()
    return (row[0], row[1]) if row else (None, None)


async def fetch_presence(session: AsyncSession) -> dict[str, set[date]]:
    """All (isin, trade_date) pairs grouped into per-ISIN date sets."""
    result = await session.execute(select(PriceEod.isin, PriceEod.trade_date))
    presence: dict[str, set[date]] = {}
    for isin, d in result.all():
        presence.setdefault(isin, set()).add(d)
    return presence


async def fetch_last_price_dates(session: AsyncSession) -> dict[str, date]:
    stmt = select(PriceEod.isin, func.max(PriceEod.trade_date)).group_by(PriceEod.isin)
    return {isin: d for isin, d in (await session.execute(stmt)).all()}


def _row_dict(isin: str, d: date, o: Any, h: Any, low: Any, c: Any) -> dict[str, Any]:
    return {
        "isin": isin,
        "trade_date": d.isoformat(),
        "open": None if o is None else str(o),
        "high": None if h is None else str(h),
        "low": None if low is None else str(low),
        "close": None if c is None else str(c),
    }


async def fetch_ohlc_violations(session: AsyncSession) -> list[dict[str, Any]]:
    stmt = select(
        PriceEod.isin,
        PriceEod.trade_date,
        PriceEod.open,
        PriceEod.high,
        PriceEod.low,
        PriceEod.close,
    ).where(
        PriceEod.high.is_not(None),
        PriceEod.low.is_not(None),
        or_(
            PriceEod.low > PriceEod.high,
            PriceEod.close > PriceEod.high,
            PriceEod.close < PriceEod.low,
        ),
    )
    return [_row_dict(*r) for r in (await session.execute(stmt)).all()]


async def fetch_nonpositive(session: AsyncSession) -> list[dict[str, Any]]:
    stmt = select(
        PriceEod.isin,
        PriceEod.trade_date,
        PriceEod.open,
        PriceEod.high,
        PriceEod.low,
        PriceEod.close,
    ).where(
        or_(
            PriceEod.open <= 0,
            PriceEod.high <= 0,
            PriceEod.low <= 0,
            PriceEod.close <= 0,
        )
    )
    return [_row_dict(*r) for r in (await session.execute(stmt)).all()]


async def fetch_zero_volume(session: AsyncSession) -> list[tuple[str, date]]:
    stmt = (
        select(PriceEod.isin, PriceEod.trade_date)
        .where(PriceEod.volume == 0)
        .limit(_ZERO_VOL_LIMIT)
    )
    return [(isin, d) for isin, d in (await session.execute(stmt)).all()]


async def insert_findings(
    session: AsyncSession, findings: list[Any], ingestion_run_id: int | None
) -> int:
    for f in findings:
        session.add(
            DataQualityLog(
                ingestion_run_id=ingestion_run_id,
                isin=f.isin,
                severity=f.severity,
                code=f.code,
                message=f.message,
                context=f.context,
            )
        )
    return len(findings)


async def fetch_findings(
    session: AsyncSession, *, severity: str | None, limit: int
) -> list[DataQualityLog]:
    stmt = select(DataQualityLog)
    if severity is not None:
        stmt = stmt.where(DataQualityLog.severity == severity)
    stmt = stmt.order_by(DataQualityLog.detected_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())
