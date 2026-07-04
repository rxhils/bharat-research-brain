"""Reels studio endpoints: latest run, feedback, improvement versions, honest
publish confirmation. All mutations emit reel.* events on the shared bus."""
from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from .. import database as db
from ..events import bus
from ..services import reel_studio

router = APIRouter(prefix="/api")


@router.get("/reels/capabilities")
def reels_capabilities():
    """What the localhost backend can do on its own — research, real vs
    simulation clip generation, TTS, publishing. The UI reads this to show
    exactly what (if anything) is missing, and never says 'Claude Code'."""
    from maven_reels.pipeline import capabilities  # noqa: PLC0415
    return capabilities.check()


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
    """Run the full pipeline after research: prepare -> generate clips (free
    simulation, or real when Higgsfield keys are set + cost confirmed) -> local
    assemble + audit. Backend-driven; no Claude Code."""
    return reel_studio.continue_after_research(job_id)


@router.post("/reels/{job_id}/generate")
def reel_generate(job_id: str, body: dict = Body(default={})):
    """Confirm + run backend clip generation now (real if keys configured, else
    free simulation), then assemble + audit. Same as approve-generation; named
    for the UI 'Confirm Generation' button."""
    _require_reel_job(job_id)
    return reel_studio.run_generation(job_id, simulate=body.get("simulate"))


@router.get("/reels/{job_id}/clips")
def reel_clips(job_id: str):
    """Higgsfield clips + generation status for a job."""
    import json as _json
    from pathlib import Path as _P
    gen_path = reel_studio.REEL_OUTPUT_ROOT / job_id / "12_higgsfield_generation.json"
    if not gen_path.exists():
        return {"job_id": job_id, "generation_status": "not_planned", "clips": []}
    gen = _json.loads(gen_path.read_text(encoding="utf-8"))
    clips_dir = reel_studio.REEL_OUTPUT_ROOT / job_id / "higgsfield_clips"
    on_disk = {p.stem for p in clips_dir.glob("shot_*.mp4")} if clips_dir.exists() else set()
    return {"job_id": job_id,
            "generation_status": gen.get("generation_status"),
            "approved_from_ui": gen.get("approved_from_ui", False),
            "estimated_cost_credits": gen.get("estimated_cost_credits"),
            "actual_cost_credits": gen.get("actual_cost_credits"),
            "planned": gen.get("planned", []),
            "clips": gen.get("clips", []),
            "clips_on_disk": sorted(on_disk)}


@router.post("/reels/{job_id}/approve-generation")
def reel_approve_generation(job_id: str, body: dict = Body(default={})):
    """Operator's explicit UI trigger for PAID scene generation (all shots)."""
    _require_reel_job(job_id)
    return reel_studio.approve_generation(job_id, source=body.get("source", "ui_run_reel"))


@router.post("/reels/{job_id}/produce")
def reel_produce(job_id: str, body: dict = Body(default={})):
    """Full-stack production (footage + Higgsfield-designed card scenes).
    Real mode requires confirm=true from the localhost UI; otherwise runs the
    free simulation. Never spends credits without explicit confirmation."""
    _require_reel_job(job_id)
    return reel_studio.run_production(
        job_id, simulate=body.get("simulate"),
        approved_from_ui=bool(body.get("confirm", False)))


@router.post("/reels/{job_id}/metrics")
def reel_metrics(job_id: str, body: dict = Body(default={})):
    """Record REAL post-publish metrics (views/likes/saves/shares) for the
    feedback loop. Never fabricated — operator/conductor supplies them."""
    _require_reel_job(job_id)
    return reel_studio.record_reel_metrics(job_id, body)


@router.post("/reels/{job_id}/confirm-generation")
def reel_confirm_generation(job_id: str, body: dict = Body(default={})):
    """Explicit localhost-UI confirmation gate for REAL Higgsfield generation.
    Marks higgsfield_generation_approved=true and runs backend generation — real
    when Higgsfield credentials are configured, else a free simulation. Reports
    the selected models + cost + pricing confidence + any missing credentials.
    Never confirmed via Claude Code; the operator clicks this in the UI."""
    _require_reel_job(job_id)
    from maven_reels.pipeline import capabilities  # noqa: PLC0415
    caps = capabilities.check()
    result = reel_studio.approve_generation(job_id, source="ui_confirm_generation")
    result["higgsfield_generation_approved"] = True
    result["real_generation_available"] = caps.get("higgsfield_available", False)
    result["missing"] = caps.get("missing", [])
    result["note"] = ("Real Higgsfield generation will run (credentials configured)."
                      if caps.get("higgsfield_available")
                      else "No Higgsfield credentials — a free simulation preview will run instead. "
                           "Log in with the Higgsfield CLI (or add a key) for real clips.")
    return result


@router.post("/reels/{job_id}/regenerate-scene/{shot_id}")
def reel_regen_scene(job_id: str, shot_id: str):
    """Approve PAID regeneration of ONE failed/weak scene."""
    _require_reel_job(job_id)
    return reel_studio.approve_generation(job_id, shot_ids=[shot_id],
                                          source="ui_regenerate_scene")


@router.post("/reels/{job_id}/regenerate-all-scenes")
def reel_regen_all(job_id: str):
    """Approve PAID regeneration of ALL scenes."""
    _require_reel_job(job_id)
    return reel_studio.approve_generation(job_id, source="ui_regenerate_all")


@router.post("/reels/{job_id}/improve-animation")
def reel_improve_animation(job_id: str):
    """Rebuild direction/plan/prompts at HIGH intensity (free); regeneration
    itself runs on the backend after the UI Confirm Generation click."""
    _require_reel_job(job_id)
    try:
        return reel_studio.improve_animation(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(409, f"run artifacts incomplete: {exc}")


@router.post("/reels/{job_id}/improve-text")
def reel_improve_text(job_id: str, body: dict = Body(default={})):
    """Text-only reassembly (Improve Text / Resync / Make Text More Viral / Move
    Subtitles Up). Reuses existing clips + voiceover — NO Higgsfield, zero credits."""
    _require_reel_job(job_id)
    try:
        return reel_studio.improve_text(
            job_id, action=body.get("action", "improve_text"),
            move_subtitles_up=bool(body.get("move_subtitles_up", False)))
    except FileNotFoundError as exc:
        raise HTTPException(409, f"cannot reassemble text: {exc}")


@router.post("/reels/{job_id}/reassemble")
def reel_reassemble(job_id: str):
    """Re-run the local assembler + auditor (free). Requires clips on disk."""
    _require_reel_job(job_id)
    try:
        return reel_studio.assemble_and_audit(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(409, f"cannot assemble: {exc}")


@router.post("/reels/{job_id}/approve-publish")
def reel_approve_publish(job_id: str):
    """Approve + run the honest publish preflight in one click. Real publishing
    still returns requires_conductor (Composio lives in the Claude runtime)."""
    _require_reel_job(job_id)
    db.upsert("jobs", {"job_id": job_id, "approval_status": "approved"},
              conflict_keys=["job_id"])
    bus.emit(job_id, "publish_gate", "reel.approval.received",
             "Operator approved via Approve & Publish.", status="approved")
    from .actions import publish as _publish
    return _publish(job_id)


def _require_reel_job(job_id: str) -> dict:
    job = db.query_one("SELECT * FROM jobs WHERE job_id=?", (job_id,))
    if not job:
        raise HTTPException(404, f"job {job_id} not found")
    return job


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
