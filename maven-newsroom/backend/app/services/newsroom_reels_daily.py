"""Daily Production Controller Agent.

Creates one daily run targeting 15 approval-ready Reels from at least 3
current Indian finance podcasts (5 clips each). Freshness policy: prefer the
last 24 hours, then 48 hours, then trusted backfill from the last 7 days.
Quality gates are never lowered to hit quota — a short day is marked
'incomplete', not padded with bad clips.
"""
from __future__ import annotations

import uuid
from datetime import date as date_t
from datetime import datetime, timezone

from .. import newsroom_reels_db as rdb
from . import newsroom_reels_queue as rq
from .newsroom_reels_storage import ReelsStorageError, validate_storage

TARGET_REELS = 15
TARGET_PODCASTS = 3
CLIPS_PER_PODCAST = 5
# Freshness windows, in hours, tried in order. Backfill never exceeds 7 days.
FRESHNESS_WINDOWS_H = (24, 48, 168)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_daily_run(run_date: date_t | str | None = None) -> dict:
    """Create (or return) the daily run for *run_date*. Storage-gated."""
    d = (run_date or date_t.today())
    d = d.isoformat() if isinstance(d, date_t) else str(d)

    existing = rdb.query_one("SELECT * FROM reels_daily_runs WHERE run_date=?", (d,))
    if existing:
        return get_run(existing["run_id"])

    run_id = f"nreels-{d}-{uuid.uuid4().hex[:6]}"
    try:
        storage = validate_storage(for_render=True)
        status, block_reason = "planned", None
    except ReelsStorageError as e:
        storage = {"storage_root": None}
        status, block_reason = "blocked", str(e)

    rdb.upsert("reels_daily_runs", {
        "run_id": run_id, "run_date": d,
        "target_reels": TARGET_REELS, "target_podcasts": TARGET_PODCASTS,
        "clips_per_podcast": CLIPS_PER_PODCAST,
        "storage_root": storage.get("storage_root"),
        "status": status, "reels_ready": 0, "block_reason": block_reason,
        "created_at": _now(), "updated_at": _now(),
    }, ["run_id"])

    if status == "planned":
        rq.enqueue("reels.storage.validate", run_id=run_id)
        rq.enqueue("reels.source.scan", run_id=run_id,
                   payload={"freshness_windows_h": list(FRESHNESS_WINDOWS_H)})
        rq.log(run_id, "daily_controller", "reels.daily.plan",
               f"planned run {run_id}: {TARGET_PODCASTS} podcasts x "
               f"{CLIPS_PER_PODCAST} clips -> {TARGET_REELS} reels")
    else:
        rq.log(run_id, "daily_controller", "reels.daily.plan",
               f"run {run_id} blocked: {block_reason}", level="error")
    return get_run(run_id)


def quota_progress(run_id: str) -> dict:
    """Live quota numbers for the dashboard. Counts only QA-passed renders."""
    ready = rdb.query_one(
        "SELECT COUNT(*) AS n FROM reels_renders r "
        "JOIN reels_qa_reports q ON q.render_id = r.render_id AND q.passed = 1 "
        "WHERE r.run_id=? AND r.status='done'", (run_id,))["n"]
    podcasts = rdb.query_one(
        "SELECT COUNT(DISTINCT episode_id) AS n FROM reels_clip_candidates "
        "WHERE run_id=? AND status != 'rejected'", (run_id,))["n"]
    clips_built = rdb.query_one(
        "SELECT COUNT(*) AS n FROM reels_clip_candidates WHERE run_id=? "
        "AND status IN ('built','watched','approved_for_render')", (run_id,))["n"]
    return {"reels_ready": ready, "podcasts_selected": podcasts,
            "clips_built": clips_built, "target_reels": TARGET_REELS,
            "target_podcasts": TARGET_PODCASTS,
            "clips_per_podcast": CLIPS_PER_PODCAST}


def finalize_run(run_id: str) -> dict:
    """End-of-day close-out: complete if quota met, else incomplete.

    Never lowers gates — an incomplete run stays incomplete.
    """
    p = quota_progress(run_id)
    status = "complete" if p["reels_ready"] >= TARGET_REELS else "incomplete"
    with rdb.connect() as c:
        c.execute("UPDATE reels_daily_runs SET status=?, reels_ready=?, updated_at=? "
                  "WHERE run_id=?", (status, p["reels_ready"], _now(), run_id))
    rq.log(run_id, "daily_controller", None,
           f"finalized {run_id}: {p['reels_ready']}/{TARGET_REELS} -> {status}")
    return get_run(run_id)


def get_run(run_id: str) -> dict:
    run = rdb.query_one("SELECT * FROM reels_daily_runs WHERE run_id=?", (run_id,))
    if run:
        run["progress"] = quota_progress(run_id)
    return run


def list_runs(limit: int = 30) -> list[dict]:
    return rdb.query_all(
        "SELECT * FROM reels_daily_runs ORDER BY run_date DESC LIMIT ?", (limit,))


async def _handle_daily_plan(job: dict) -> None:
    create_daily_run(job.get("payload", {}).get("date"))


rq.register("reels.daily.plan", _handle_daily_plan)
