"""Data access for `index_constituents` (SCD-2 membership, append-only).

The Universe Agent diffs the live constituent set against what each index
CSV reports. New members get an open row (`effective_to IS NULL`); dropped
members get their open row end-dated. Rows are never deleted — that is what
keeps backtests survivorship-bias-free (CLAUDE.md §4).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import IndexConstituent


async def fetch_active(session: AsyncSession) -> list[IndexConstituent]:
    """Return every currently-open membership row (`effective_to IS NULL`)."""
    stmt = select(IndexConstituent).where(IndexConstituent.effective_to.is_(None))
    return list((await session.execute(stmt)).scalars().all())


async def open_membership(
    session: AsyncSession,
    *,
    index_code: str,
    isin: str,
    effective_from: date,
    source: str,
    weight_pct: Decimal | None = None,
) -> IndexConstituent:
    """Insert a new open membership row and flush. Caller commits."""
    row = IndexConstituent(
        index_code=index_code,
        isin=isin,
        weight_pct=weight_pct,
        effective_from=effective_from,
        source=source,
    )
    session.add(row)
    await session.flush()
    return row


def close_membership(row: IndexConstituent, *, effective_to: date) -> None:
    """End-date an open membership row in place (SCD-2 close-out).

    `row` must be a session-attached instance from `fetch_active`. Caller
    commits. The DB enforces `effective_to > effective_from`, so a same-day
    close-and-reopen is rejected loud rather than silently corrupting history.
    """
    row.effective_to = effective_to
