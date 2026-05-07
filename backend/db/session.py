from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from backend.config import settings

engine: AsyncEngine = create_async_engine(settings.postgres_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def ping_db(timeout: float = 2.0) -> bool:
    """One-shot health probe — never raises."""
    try:
        async with asyncio.timeout(timeout):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
