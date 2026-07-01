"""Reels studio endpoints: latest run, feedback, improvement versions, honest
publish confirmation. All mutations emit reel.* events on the shared bus."""
from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from .. import database as db
from ..events import bus
from ..services import reel_studio

router = APIRouter(prefix="/api")


@router.get("/reels/latest")
def reels_latest():
    job = reel_studio.latest_job()
    if not job:
        raise HTTPException(404, "no reel runs yet")
    job_id = job["job_id"]
    scores = db.query_one("SELECT * FROM scores WHERE job_id=?", (job_id,)) or {}
    stale = reel_studio.staleness(job_id)
    return {
        "job_id": job_id, "status": job.get("status"),
        "created_at": job.get("created_at"), "version": job.get("version", 1),
        "parent_job_id": job.get("parent_job_id"),
        "review_url": f"/reels/review/{job_id}",
        "video_path": f"/api/jobs/{job_id}/artifact/reel.mp4",
        "cover_path": f"/api/jobs/{job_id}/artifact/cover.jpg",
        "scores": scores, "stale": stale,
        "approval_status": job.get("approval_status"),
        "publish_status": job.get("publish_status"),
    }


@router.post("/reels/run")
def reels_run(body: dict = Body(default={})):
    """Create a NEW unique reel run (never overwrites or reuses an old run)."""
    return reel_studio.create_reel_job(source=body.get("source", "manual_run"))


@router.post("/jobs/{job_id}/feedback")
def reel_feedback(job_id: str, body: dict = Body(default={})):
    ftype = body.get("feedback_type", "other")
    if ftype not in reel_studio.FEEDBACK_TYPES:
        raise HTTPException(400, f"unknown feedback_type; use one of {reel_studio.FEEDBACK_TYPES}")
    return reel_studio.record_feedback(job_id, ftype, body.get("custom_feedback", ""))


@router.post("/jobs/{job_id}/improve")
async def reel_improve(job_id: str, body: dict = Body(default={})):
    """Reject-with-feedback → Reel Improvement Director → new version job."""
    ftype = body.get("feedback_type", "other")
    if ftype not in reel_studio.FEEDBACK_TYPES:
        raise HTTPException(400, f"unknown feedback_type; use one of {reel_studio.FEEDBACK_TYPES}")
    return await reel_studio.improve(job_id, ftype, body.get("custom_feedback", ""))


@router.get("/jobs/{job_id}/versions")
def reel_versions(job_id: str):
    root = reel_studio._root_id(job_id)
    versions = db.query_all(
        "SELECT * FROM reel_versions WHERE root_job_id=? ORDER BY version", (root,))
    feedback = db.query_all(
        "SELECT * FROM reel_feedback WHERE job_id LIKE ? ORDER BY created_at",
        (f"{root}%",))
    return {"root_job_id": root, "versions": versions, "feedback": feedback}


@router.post("/jobs/{job_id}/continue-after-research")
def reel_continue(job_id: str):
    """Conductor helper: once fresh 01_research.json is in the run folder, run
    the full deterministic pipeline + local render + audit."""
    return reel_studio.continue_after_research(job_id)


@router.post("/jobs/{job_id}/publish-confirm")
def publish_confirm(job_id: str, body: dict = Body(default={})):
    """Record a REAL Instagram publish result (called by the conductor AFTER
    Composio returns a media id). Refuses to mark published without one."""
    media_id, permalink = body.get("media_id"), body.get("permalink")
    if not media_id and not permalink:
        db.upsert("reel_publish", {"job_id": job_id, "status": "failed",
                                   "error": body.get("error", "no media id returned"),
                                   "media_id": None, "permalink": None,
                                   "published_at": None}, conflict_keys=["job_id"])
        bus.emit(job_id, "reels_courier", "reel.publish.failed",
                 f"Publish failed: {body.get('error', 'no media id returned')}",
                 status="failed")
        raise HTTPException(400, "publish not confirmed: a real Instagram media_id "
                                 "or permalink is required")
    now = reel_studio._now()
    db.upsert("reel_publish", {"job_id": job_id, "status": "published",
                               "media_id": media_id, "permalink": permalink,
                               "error": None, "published_at": now},
              conflict_keys=["job_id"])
    db.upsert("jobs", {"job_id": job_id, "publish_status": "published",
                       "status": "published", "instagram_post_id": media_id,
                       "instagram_post_url": permalink, "updated_at": now},
              conflict_keys=["job_id"])
    bus.emit(job_id, "reels_courier", "reel.publish.completed",
             f"Published to Instagram Reels — {permalink or media_id}",
             status="published")
    return {"status": "published", "media_id": media_id, "permalink": permalink}
