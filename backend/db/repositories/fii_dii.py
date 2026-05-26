"""Data access for `fii_dii_flows` (Chunk 3.6).

`bulk_upsert` is idempotent via ON CONFLICT (flow_date) DO UPDATE — re-ingesting
the same file overwrites with identical values, leaving the row count unchanged.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import FiiDiiFlow

_BATCH = 500

_UPSERT_COLS = (
    "fii_net_cr",
    "dii_net_cr",
    "fii_5d_sum",
    "dii_5d_sum",
    "fii_signal",
    "source",
)


async def bulk_upsert(session: AsyncSession, rows: Sequence[dict[str, Any]]) -> int:
    """Insert/update flow rows. Returns affected count. Caller commits."""
    affected = 0
    for i in range(0, len(rows), _BATCH):
        batch = list(rows[i : i + _BATCH])
        stmt = pg_insert(FiiDiiFlow).values(batch)
        stmt = stmt.on_conflict_do_update(
            index_elements=["flow_date"],
            set_={c: getattr(stmt.excluded, c) for c in _UPSERT_COLS}
            | {"fetched_at": func.now()},
        )
        result = await session.execute(stmt)
        affected += result.rowcount or 0
    return affected


async def fetch_recent(session: AsyncSession, *, limit: int = 30) -> list[FiiDiiFlow]:
    """Most-recent flow rows, newest first."""
    stmt = select(FiiDiiFlow).order_by(FiiDiiFlow.flow_date.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())
