"""Queue Orchestration Agent — the Newsroom Reels job pipeline.

This app has no Redis/BullMQ; the existing architecture is in-process
background runners over SQLite. The Reels queues follow that pattern: a
persistent reels_queue_jobs table gives every stage independent, retry-safe,
monitorable jobs, and workers claim them one at a time.

Each queue name maps 1:1 to a pipeline stage agent. Later phases register a
handler per queue; unregistered queues simply hold jobs until their agent
lands.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from .. import newsroom_reels_db as rdb

QUEUES = [
    "reels.daily.plan",
    "reels.storage.validate",
    "reels.source.scan",
    "reels.source.score",
    "reels.episode.discover",
    "reels.episode.rank",
    "reels.metadata.fetch",
    "reels.transcript.create",
    "reels.video.watch_source",
    "reels.segments.create",
    "reels.segment.score_finance",
    "reels.segment.score_viral",
    "reels.segment.score_compliance",
    "reels.segment.score_context",
    "reels.clip.plan",
    "reels.clip.build",
    "reels.video.watch_candidate",
    "reels.hook.write",
    "reels.caption.create",
    "reels.storyboard.create",
    "reels.render.create",
    "reels.video.watch_final",
    "reels.qa.check",
    "reels.review.create",
    "reels.memory.update",
    "reels.publish.approved",
]

Handler = Callable[[dict], Awaitable[dict | None]]
_HANDLERS: dict[str, Handler] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def register(queue: str, handler: Handler) -> None:
    if queue not in QUEUES:
        raise ValueError(f"unknown reels queue: {queue}")
    _HANDLERS[queue] = handler


def enqueue(queue: str, *, run_id: str | None = None, subject_id: str | None = None,
            payload: dict | None = None, max_attempts: int = 3) -> int:
    if queue not in QUEUES:
        raise ValueError(f"unknown reels queue: {queue}")
    with rdb.connect() as c:
        cur = c.execute(
            "INSERT INTO reels_queue_jobs (queue, run_id, subject_id, payload_json, "
            "status, max_attempts, created_at) VALUES (?,?,?,?, 'queued', ?, ?)",
            (queue, run_id, subject_id, rdb.dumps(payload or {}), max_attempts, _now()))
        return int(cur.lastrowid)


def claim(queue: str) -> dict | None:
    """Atomically claim the oldest queued job on *queue* (or a retryable failure)."""
    with rdb.connect() as c:
        row = c.execute(
            "SELECT * FROM reels_queue_jobs WHERE queue=? AND "
            "(status='queued' OR (status='failed' AND attempts < max_attempts)) "
            "ORDER BY job_id LIMIT 1", (queue,)).fetchone()
        if row is None:
            return None
        job = dict(row)
        updated = c.execute(
            "UPDATE reels_queue_jobs SET status='running', attempts=attempts+1, "
            "started_at=? WHERE job_id=? AND status IN ('queued','failed')",
            (_now(), job["job_id"]))
        if updated.rowcount == 0:  # lost the race to another worker
            return None
        job["attempts"] += 1
        return job


def complete(job_id: int) -> None:
    with rdb.connect() as c:
        c.execute("UPDATE reels_queue_jobs SET status='done', finished_at=?, error=NULL "
                  "WHERE job_id=?", (_now(), job_id))


def fail(job_id: int, error: str) -> None:
    """Mark failed; becomes 'dead' once attempts are exhausted (never retries forever)."""
    with rdb.connect() as c:
        c.execute(
            "UPDATE reels_queue_jobs SET "
            "status=CASE WHEN attempts >= max_attempts THEN 'dead' ELSE 'failed' END, "
            "finished_at=?, error=? WHERE job_id=?", (_now(), error[:2000], job_id))


async def process_one(queue: str) -> dict | None:
    """Claim and run one job through its registered handler. Returns the job row."""
    handler = _HANDLERS.get(queue)
    if handler is None:
        return None
    job = claim(queue)
    if job is None:
        return None
    try:
        import json
        payload = json.loads(job.get("payload_json") or "{}")
        await handler({**job, "payload": payload})
        complete(job["job_id"])
        job["status"] = "done"
    except Exception as e:  # noqa: BLE001 — recorded, never swallowed silently
        fail(job["job_id"], f"{type(e).__name__}: {e}")
        job["status"] = "failed"
        log(job.get("run_id"), "queue", queue, f"job {job['job_id']} failed: {e}", level="error")
    return job


def stats() -> list[dict]:
    """Per-queue counts for the dashboard."""
    rows = rdb.query_all(
        "SELECT queue, status, COUNT(*) AS n FROM reels_queue_jobs GROUP BY queue, status")
    by_queue: dict[str, dict] = {q: {"queue": q, "queued": 0, "running": 0,
                                     "done": 0, "failed": 0, "dead": 0} for q in QUEUES}
    for r in rows:
        if r["queue"] in by_queue:
            by_queue[r["queue"]][r["status"]] = r["n"]
    return list(by_queue.values())


def log(run_id: str | None, agent: str, queue: str | None, message: str,
        *, level: str = "info", payload: dict | None = None) -> None:
    with rdb.connect() as c:
        c.execute(
            "INSERT INTO reels_agent_logs (run_id, agent, queue, level, message, "
            "payload_json, created_at) VALUES (?,?,?,?,?,?,?)",
            (run_id, agent, queue, level, message, rdb.dumps(payload or {}), _now()))
