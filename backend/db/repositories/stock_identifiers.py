"""Data access for `stock_identifiers` (SCD-2 identity/classification history).

When the Universe Agent detects a tracked field change on a stock
(nse_symbol, company_name, industry, sector, ...), it end-dates the current
open identifier row for that (isin, identifier_type) and inserts a new one.
Append-only; rows are never updated except to set `effective_to`.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import StockIdentifier


async def fetch_current(
    session: AsyncSession,
) -> dict[tuple[str, str], StockIdentifier]:
    """Return open identifier rows keyed by (isin, identifier_type).

    Open = `effective_to IS NULL`. The DB guarantees at most one open row per
    (isin, identifier_type) via the partial index `idx_stock_identifiers_current`.
    """
    stmt = select(StockIdentifier).where(StockIdentifier.effective_to.is_(None))
    rows = (await session.execute(stmt)).scalars().all()
    return {(row.isin, row.identifier_type): row for row in rows}


async def open_identifier(
    session: AsyncSession,
    *,
    isin: str,
    identifier_type: str,
    value: str,
    effective_from: date,
    source: str,
) -> StockIdentifier:
    """Insert a new open identifier row and flush. Caller commits."""
    row = StockIdentifier(
        isin=isin,
        identifier_type=identifier_type,
        value=value,
        effective_from=effective_from,
        source=source,
    )
    session.add(row)
    await session.flush()
    return row


def close_identifier(row: StockIdentifier, *, effective_to: date) -> None:
    """End-date an open identifier row in place (SCD-2 close-out). Caller commits."""
    row.effective_to = effective_to
