"""Data access for `corporate_actions` (insert-only event store).

`bulk_insert` is idempotent via ON CONFLICT (isin, action_type, ex_date)
DO NOTHING, so the same event is never double-stored. Rows are duck-typed
(any object exposing the corporate_actions field attributes) to avoid a
circular import with the agent module that defines CorpActionRow.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import CorporateAction, Stock

_BATCH = 1000


async def fetch_active_symbols(session: AsyncSession) -> list[tuple[str, str]]:
    """(isin, nse_symbol) for active stocks that have an NSE symbol."""
    stmt = select(Stock.isin, Stock.nse_symbol).where(
        Stock.delisted_on.is_(None), Stock.nse_symbol.is_not(None)
    )
    return [(isin, sym) for isin, sym in (await session.execute(stmt)).all()]


async def bulk_insert(session: AsyncSession, rows: Sequence[Any]) -> int:
    """Insert corporate-action rows, skipping duplicates. Returns inserted count.

    Caller commits.
    """
    inserted = 0
    payload = [
        {
            "isin": r.isin,
            "action_type": r.action_type,
            "ex_date": r.ex_date,
            "record_date": r.record_date,
            "announcement_date": r.announcement_date,
            "ratio_numerator": r.ratio_numerator,
            "ratio_denominator": r.ratio_denominator,
            "amount_inr": r.amount_inr,
            "description": r.description,
            "source": r.source,
        }
        for r in rows
    ]
    for i in range(0, len(payload), _BATCH):
        batch = payload[i : i + _BATCH]
        stmt = pg_insert(CorporateAction).values(batch).on_conflict_do_nothing(
            index_elements=["isin", "action_type", "ex_date"]
        )
        result = await session.execute(stmt)
        inserted += result.rowcount or 0
    return inserted


async def fetch_actions(
    session: AsyncSession,
    *,
    isin: str | None = None,
    action_type: str | None = None,
    limit: int = 30,
) -> list[CorporateAction]:
    stmt = select(CorporateAction)
    if isin is not None:
        stmt = stmt.where(CorporateAction.isin == isin)
    if action_type is not None:
        stmt = stmt.where(CorporateAction.action_type == action_type)
    stmt = stmt.order_by(CorporateAction.ex_date.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())
