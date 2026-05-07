from __future__ import annotations

import asyncio

from redis.asyncio import Redis

from backend.config import settings


async def ping_redis(timeout: float = 2.0) -> bool:
    """One-shot health probe — never raises."""
    try:
        async with asyncio.timeout(timeout):
            client = Redis.from_url(settings.redis_url)
            try:
                pong = await client.ping()
                return bool(pong)
            finally:
                await client.aclose()
    except Exception:
        return False
