"""Data access for the `stocks` table (mutable universe master, keyed by ISIN).

No business logic here — the Universe Agent owns the diff/SCD decisions and
mutates the returned ORM objects directly (the table is the mutable parent;
`updated_at` is maintained by SQLAlchemy `onupdate`). This module only
fetches and inserts.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Stock


async def fetch_all_by_isin(session: AsyncSession) -> dict[str, Stock]:
    """Return every stock row keyed by ISIN (delisted rows included).

    Delisted rows are kept so the agent can detect a re-listing and avoid a
    spurious insert that would violate the ISIN primary key.
    """
    rows = (await session.execute(select(Stock))).scalars().all()
    return {row.isin: row for row in rows}


async def insert(
    session: AsyncSession,
    *,
    isin: str,
    company_name: str,
    nse_symbol: str | None = None,
    industry: str | None = None,
    sector: str | None = None,
    listed_on: date | None = None,
    lot_size_fno: int | None = None,
    is_fno: bool = False,
) -> Stock:
    """Insert a new stock row and flush so its PK is usable immediately.

    Caller commits the session.
    """
    stock = Stock(
        isin=isin,
        company_name=company_name,
        nse_symbol=nse_symbol,
        industry=industry,
        sector=sector,
        listed_on=listed_on,
        lot_size_fno=lot_size_fno,
        is_fno=is_fno,
    )
    session.add(stock)
    await session.flush()
    return stock
