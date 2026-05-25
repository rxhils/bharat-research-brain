"""Data access for `news_articles`.

`bulk_insert` deduplicates via ON CONFLICT (source_url) DO NOTHING — the same
article URL is never stored twice. Reads support the CLI's matched / unmatched
views.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import NewsArticle

_BATCH = 1000


async def bulk_insert(session: AsyncSession, rows: Sequence[dict[str, Any]]) -> int:
    """Insert news rows, skipping duplicate source_urls. Returns inserted count."""
    inserted = 0
    for i in range(0, len(rows), _BATCH):
        batch = list(rows[i : i + _BATCH])
        stmt = pg_insert(NewsArticle).values(batch).on_conflict_do_nothing(
            index_elements=["source_url"]
        )
        result = await session.execute(stmt)
        inserted += result.rowcount or 0
    return inserted


async def fetch(
    session: AsyncSession,
    *,
    isin: str | None = None,
    unmatched: bool = False,
    limit: int = 20,
) -> list[NewsArticle]:
    stmt = select(NewsArticle)
    if unmatched:
        stmt = stmt.where(NewsArticle.isin.is_(None))
    elif isin is not None:
        stmt = stmt.where(NewsArticle.isin == isin)
    stmt = stmt.order_by(NewsArticle.published_at.desc().nullslast()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())
