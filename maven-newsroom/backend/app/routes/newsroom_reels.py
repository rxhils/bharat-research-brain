"""Newsroom Reels module routes (/api/newsroom-reels/*).

Isolated from the existing Higgsfield reels routes (routes/reels.py). Does
not import reel_studio, registry_reels, or the shared newsroom.db.
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import FileResponse

from .. import newsroom_reels_db as rdb
from ..newsroom_reels_config import storage_status
from ..services import newsroom_reels_daily as daily
from ..services import newsroom_reels_queue as rq
from ..services.newsroom_reels_storage import ReelsStorageError, validate_storage

router = APIRouter(prefix="/api/newsroom-reels")


@router.get("/status")
def status():
    s = storage_status()
    return {"module": "newsroom-reels", **s}


@router.post("/storage/validate")
def storage_validate():
    """Run the Storage Validation Agent with the render gate enforced.

    The dashboard calls this before a daily run; a 507 here means the run
    is blocked (drive missing or under 50 GB free) — never a silent C-drive
    fallback.
    """
    try:
        return {"module": "newsroom-reels", **validate_storage(for_render=True)}
    except ReelsStorageError as e:
        raise HTTPException(status_code=507, detail=str(e))


@router.get("/db")
def db_status():
    """Isolated reels DB health: file path + reels_ tables present."""
    rdb.init_db()
    return {"db_path": str(rdb.DB_PATH), "tables": rdb.table_names()}


@router.get("/queues")
def queues():
    """Per-queue job counts across the 26-stage pipeline."""
    rdb.init_db()
    return {"queues": rq.stats()}


@router.post("/runs")
def create_run(body: dict = Body(default={})):
    """Create (or return) today's daily run. Blocked runs carry block_reason."""
    rdb.init_db()
    return daily.create_daily_run(body.get("date"))


@router.get("/runs")
def runs():
    rdb.init_db()
    return {"runs": daily.list_runs()}


@router.get("/runs/{run_id}")
def run_detail(run_id: str):
    run = daily.get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    return run


@router.post("/runs/{run_id}/finalize")
def run_finalize(run_id: str):
    if not daily.get_run(run_id):
        raise HTTPException(404, "run not found")
    return daily.finalize_run(run_id)


# the 27 agents of the Newsroom Reels framework — log keys map to
# reels_agent_logs.agent values written by each service
AGENT_REGISTRY = [
    ("storage_guard", "Storage Validation Agent", "Verifies E:\\MavenReels, free space, blocks C-drive paths"),
    ("db_schema", "Database Schema Agent", "Isolated reels_ tables in newsroom_reels.db"),
    ("queue", "Queue Orchestration Agent", "26-queue pipeline with retries and dead-lettering"),
    ("daily_controller", "Daily Production Controller", "Plans 15 reels/day from 3 podcasts, tracks quota"),
    ("source_scout", "Source Scout Agent", "Scans trusted Indian finance channels for episodes"),
    ("source_trust", "Source Trust Agent", "Scores channel authority, relevance, compliance risk"),
    ("episode_ranking", "Episode Ranking Agent", "Ranks episodes by velocity, freshness, LLM topic relevance"),
    ("transcript", "Transcript Agent", "Word-timed captions (official → auto → WhisperX)"),
    ("video_watch", "Claude Video Watch Agents", "Watches source, candidate clips, and final renders"),
    ("segment_discovery", "Segment Discovery Agent", "Finds 20-30 candidate moments, 20-30s, clean boundaries"),
    ("segment_scoring", "Relevance/Virality/Compliance/Context Agents", "Four LLM+regex gates per segment"),
    ("clip_planner", "Clip Planner Agent", "Picks top 5 clips per episode, final score >= 85"),
    ("ffmpeg_builder", "FFmpeg Clip Builder Agent", "Frame-accurate cuts, reproducible commands"),
    ("creative", "Hook / Caption / Storyboard Agents", "Safe hooks, word-synced subtitles, Remotion storyboard"),
    ("remotion_render", "Remotion Render Agent", "1080x1920 premium renders on E:"),
    ("qa", "QA Agent", "Final technical + compliance gate before review"),
    ("review", "Review Dashboard", "Approve / reject / revise on /newsroom/reels"),
    ("memory", "Feedback Memory Agent", "Learns source/topic/hook/template patterns from decisions"),
    ("publishing_queue", "Publishing Queue Agent", "Approved-only, spaced IST slots, Instagram via Composio"),
]


@router.get("/agents")
def agents():
    """Every framework agent with its latest activity from reels_agent_logs."""
    rdb.init_db()
    rows = rdb.query_all(
        "SELECT agent, MAX(created_at) AS last_at FROM reels_agent_logs GROUP BY agent")
    last_by_agent = {r["agent"]: r["last_at"] for r in rows}
    out = []
    for key, name, role in AGENT_REGISTRY:
        last_at = last_by_agent.get(key)
        latest = rdb.query_one(
            "SELECT message, level, created_at FROM reels_agent_logs "
            "WHERE agent=? ORDER BY log_id DESC LIMIT 1", (key,))
        errors_24h = rdb.query_one(
            "SELECT COUNT(*) AS n FROM reels_agent_logs WHERE agent=? "
            "AND level='error' AND created_at >= datetime('now', '-1 day')",
            (key,)) or {"n": 0}
        out.append({
            "key": key, "name": name, "role": role,
            "last_activity_at": last_at,
            "last_message": latest["message"] if latest else None,
            "last_level": latest["level"] if latest else None,
            "errors_24h": errors_24h["n"],
        })
    return {"agents": out}


@router.get("/reels")
def list_reels():
    """Reel cards for review, latest render first."""
    rows = rdb.query_all(
        "SELECT r.render_id, r.render_path, r.status AS render_status, r.created_at, "
        "r.duration_sec, p.hook_text, p.ig_caption, p.hashtags, p.attribution, "
        "p.disclaimer, q.passed AS qa_passed, q.final_render_watch_score, "
        "s.indian_relevance_score, s.virality_score, s.compliance_risk_score, "
        "s.context_safety_score, s.final_clip_score, g.text AS transcript_excerpt, "
        "e.title AS episode_title, e.url AS episode_url, src.name AS source_name, "
        "d.decision, d.reason AS decision_reason "
        "FROM reels_renders r "
        "LEFT JOIN reels_clip_candidates c ON c.clip_id = r.clip_id "
        "LEFT JOIN reels_edit_plans p ON p.clip_id = r.clip_id "
        "LEFT JOIN reels_qa_reports q ON q.render_id = r.render_id "
        "LEFT JOIN reels_segments g ON g.segment_id = c.segment_id "
        "LEFT JOIN reels_segment_scores s ON s.segment_id = c.segment_id "
        "LEFT JOIN reels_episodes e ON e.episode_id = c.episode_id "
        "LEFT JOIN reels_sources src ON src.source_id = e.source_id "
        "LEFT JOIN reels_review_decisions d ON d.render_id = r.render_id "
        "ORDER BY r.created_at DESC LIMIT 100")
    return {"reels": rows}


@router.get("/reels/{render_id}/video")
def reel_video(render_id: str):
    r = rdb.query_one("SELECT render_path FROM reels_renders WHERE render_id=?",
                      (render_id,))
    if not r or not r["render_path"] or not Path(r["render_path"]).exists():
        raise HTTPException(404, "render not found")
    return FileResponse(r["render_path"], media_type="video/mp4")


@router.post("/reels/{render_id}/decision")
def reel_decision(render_id: str, body: dict = Body(...)):
    """approve | reject | revise — approval-only publishing starts here."""
    decision = body.get("decision")
    if decision not in ("approve", "reject", "revise"):
        raise HTTPException(422, "decision must be approve|reject|revise")
    r = rdb.query_one("SELECT * FROM reels_renders WHERE render_id=?", (render_id,))
    if not r:
        raise HTTPException(404, "render not found")
    if decision == "approve":
        qa = rdb.query_one("SELECT passed FROM reels_qa_reports WHERE render_id=? "
                           "ORDER BY created_at DESC", (render_id,))
        if not qa or not qa["passed"]:
            raise HTTPException(409, "cannot approve a reel that has not passed QA")
    decision_id = f"dec-{uuid4().hex[:8]}"
    rdb.upsert("reels_review_decisions", {
        "decision_id": decision_id, "render_id": render_id, "run_id": r["run_id"],
        "decision": decision, "reason": body.get("reason"),
        "revise_instruction": body.get("revise_instruction"),
        "decided_at": datetime.now(UTC).isoformat(),
    }, ["decision_id"])
    rq.enqueue("reels.memory.update", run_id=r["run_id"], subject_id=render_id,
               payload={"decision": decision, "reason": body.get("reason")})
    if decision == "approve":
        rq.enqueue("reels.publish.approved", run_id=r["run_id"],
                   subject_id=render_id, payload={"decision_id": decision_id})
    return {"decision_id": decision_id, "decision": decision}
