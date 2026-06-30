"""Server-Sent Events live stream for a job.

On connect it replays recent events (so a late subscriber catches up), then
tails live events pushed by the event bus. Heartbeats keep the connection warm.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from .. import database as db
from ..events import bus

router = APIRouter(prefix="/api")


def _sse(data: str, event: str | None = None) -> str:
    prefix = f"event: {event}\n" if event else ""
    return f"{prefix}data: {data}\n\n"


@router.get("/jobs/{job_id}/stream")
async def stream(job_id: str, request: Request, replay: int = 200):
    queue = bus.subscribe(job_id)

    async def gen():
        try:
            # 1) replay recent history
            history = db.query_all(
                "SELECT * FROM events WHERE job_id=? ORDER BY seq DESC LIMIT ?",
                (job_id, replay))
            for ev in reversed(history):
                yield _sse(db.dumps(ev), event="event")
            yield _sse(db.dumps({"type": "replay_done"}), event="meta")
            # 2) tail live
            while True:
                if await request.is_disconnected():
                    break
                try:
                    ev = await asyncio.wait_for(queue.get(), timeout=15)
                    yield _sse(db.dumps(ev), event="event")
                except asyncio.TimeoutError:
                    yield _sse(db.dumps({"type": "heartbeat"}), event="ping")
        finally:
            bus.unsubscribe(job_id, queue)

    return StreamingResponse(gen(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    })
