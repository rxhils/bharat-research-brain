from __future__ import annotations

import os

from backend.logging_setup import configure_logging

configure_logging(os.getenv("LOG_FORMAT", "console"))

import asyncio  # noqa: E402

import structlog  # noqa: E402
from fastapi import FastAPI  # noqa: E402

from backend.db.session import ping_db  # noqa: E402
from backend.services.ollama import ping_ollama  # noqa: E402
from backend.services.redis_client import ping_redis  # noqa: E402

log = structlog.get_logger()
app = FastAPI(title="bharat-research-brain", version="0.0.1")


@app.get("/health")
async def health() -> dict[str, str]:
    pg, rd, oll = await asyncio.gather(
        ping_db(2.0),
        ping_redis(2.0),
        ping_ollama(2.0),
    )
    services = {
        "postgres": "ok" if pg else "down",
        "redis": "ok" if rd else "down",
        "ollama": "ok" if oll else "down",
    }
    down = sum(1 for v in services.values() if v == "down")
    if down == 0:
        overall = "healthy"
    elif down == 3:
        overall = "unhealthy"
    else:
        overall = "degraded"
    log.info("health.check", services=services, overall=overall)
    return {**services, "overall": overall}
