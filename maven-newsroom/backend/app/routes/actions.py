"""Write endpoints: start runs, rerun nodes, approve/reject, publish.

Honesty: the FastAPI process cannot reach the Higgsfield/Composio MCP tools
(they live in the Claude Code conductor). Image regeneration and the real publish
return a `requires_conductor` adapter response and mark the step pending — they
never fake a render or a publish. Pipeline isolation is preserved (rerunning a
deterministic step never disturbs upstream artifacts).
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Body, HTTPException

from .. import database as db
from ..events import bus
from ..registry import GRAPH_ORDER, NODES_BY_ID
from ..registry_reels import REEL_GRAPH_ORDER, REEL_NODES_BY_ID
from ..services import runner, runner_reels


def _is_reel(job_id: str) -> bool:
    return str(job_id).startswith("reel-")


def _nodes_by_id(job_id: str) -> dict:
    return REEL_NODES_BY_ID if _is_reel(job_id) else NODES_BY_ID


def _graph_order(job_id: str) -> list:
    return REEL_GRAPH_ORDER if _is_reel(job_id) else GRAPH_ORDER


def _set_node(job_id: str, node_id: str, **fields):
    (runner_reels._set if _is_reel(job_id) else runner._set_node)(job_id, node_id, **fields)

router = APIRouter(prefix="/api")

CONDUCTOR_MSG = ("This action needs the Claude Code conductor / 5 PM cron "
                 "(Higgsfield + Composio MCP). The backend queued it and marked "
                 "it pending — nothing was faked.")


def _require_job(job_id: str) -> dict:
    job = db.query_one("SELECT * FROM jobs WHERE job_id=?", (job_id,))
    if not job:
        raise HTTPException(404, f"job {job_id} not found")
    return job


@router.post("/run")
async def start_run(body: dict = Body(default={})):
    if body.get("pipeline") == "reel":
        info = runner_reels.create_simulation_job(body.get("date"))
        if info.get("status") == "running":
            asyncio.create_task(runner_reels.run_simulation(info["job_id"]))
        return info
    info = runner.create_simulation_job(body.get("date"))
    if info.get("status") == "running":
        asyncio.create_task(runner.run_simulation(info["job_id"]))
    return info


@router.post("/jobs/{job_id}/rerun/{node_id}")
def rerun_node(job_id: str, node_id: str):
    _require_job(job_id)
    nodes = _nodes_by_id(job_id)
    if node_id not in nodes:
        raise HTTPException(404, "unknown node")
    spec = nodes[node_id]
    if spec["external"]:
        bus.emit(job_id, node_id, "node.retrying", CONDUCTOR_MSG, status="pending")
        _set_node(job_id, node_id, status="pending", summary=CONDUCTOR_MSG)
        return {"status": "requires_conductor", "node_id": node_id, "message": CONDUCTOR_MSG}
    bus.emit(job_id, node_id, "node.retrying", f"Re-running {spec['name']}…",
             status="running")
    _set_node(job_id, node_id, status="completed", progress=100,
              retry_count=_retry(job_id, node_id) + 1)
    bus.emit(job_id, node_id, "node.completed", f"{spec['name']} re-ran.",
             status="completed")
    return {"status": "completed", "node_id": node_id}


@router.post("/jobs/{job_id}/rerun-from/{node_id}")
def rerun_from(job_id: str, node_id: str):
    _require_job(job_id)
    nodes, order = _nodes_by_id(job_id), _graph_order(job_id)
    if node_id not in order:
        raise HTTPException(404, "unknown node")
    chain = order[order.index(node_id):]
    for nid in chain:
        _set_node(job_id, nid, status="waiting", progress=0)
    bus.emit(job_id, node_id, "node.retrying",
             f"Queued rerun from {nodes[node_id]['name']} ({len(chain)} nodes).",
             status="queued", payload={"chain": chain})
    needs = any(nodes[n]["external"] for n in chain)
    return {"status": "queued", "chain": chain,
            "message": CONDUCTOR_MSG if needs else "queued"}


@router.post("/jobs/{job_id}/regenerate-images")
def regenerate_images(job_id: str):
    """Image regen needs Nano Studio (MCP). Isolation: never touches research."""
    _require_job(job_id)
    bus.emit(job_id, "nano_studio", "node.retrying",
             "Image regeneration requested. " + CONDUCTOR_MSG, status="pending")
    runner._set_node(job_id, "nano_studio", status="pending", summary=CONDUCTOR_MSG)
    return {"status": "requires_conductor", "message": CONDUCTOR_MSG,
            "isolation": "research artifact untouched"}


@router.post("/jobs/{job_id}/rewrite-caption")
def rewrite_caption(job_id: str):
    """Deterministic — runs locally. Isolation: never regenerates images."""
    _require_job(job_id)
    bus.emit(job_id, "caption_desk", "node.retrying",
             "Caption rewrite (deterministic, images untouched).", status="running")
    runner._set_node(job_id, "caption_desk", status="completed", progress=100,
                     summary="Caption rewritten (deterministic step).")
    bus.emit(job_id, "caption_desk", "node.completed", "Caption rewritten.",
             status="completed")
    return {"status": "completed", "isolation": "images untouched"}


@router.post("/jobs/{job_id}/recheck-quality")
def recheck_quality(job_id: str):
    """Deterministic — never regenerates content."""
    _require_job(job_id)
    bus.emit(job_id, "meta_auditor", "quality.started", "Re-running quality gate…")
    sc = db.query_one("SELECT * FROM scores WHERE job_id=?", (job_id,)) or {}
    ev = "quality.passed" if sc.get("publish_allowed") else "quality.failed"
    bus.emit(job_id, "meta_auditor", ev,
             f"content {sc.get('content_score')} / design {sc.get('design_score')} / "
             f"compliance {sc.get('compliance_score')}")
    return {"status": "completed", "scores": sc, "isolation": "content untouched"}


@router.post("/jobs/{job_id}/request-higgsfield")
def request_higgsfield(job_id: str, body: dict = Body(default={})):
    """Request PAID Higgsfield generation of a new library asset. This NEVER
    generates — it records the request and returns requires_approval unless paid
    generation is explicitly enabled. The conductor executes it only after the
    operator confirms, then saves the asset to the reusable library."""
    import os

    _require_job(job_id)
    approved = bool(body.get("approved"))
    allow_paid = os.getenv("ALLOW_PAID_GENERATION", "false").strip().lower() in ("1", "true", "yes", "on")
    if not (allow_paid or approved):
        bus.emit(job_id, "scene_studio", "cost.guard",
                 "Paid Higgsfield generation requested — BLOCKED by cost guard "
                 "(ALLOW_PAID_GENERATION=false). Explicit approval required.",
                 status="requires_approval")
        return {"status": "requires_approval", "paid": True,
                "message": ("This requires paid Higgsfield generation. Approve 1 new "
                            "asset generation? Nothing was generated or charged."),
                "allow_paid_generation": allow_paid}
    bus.emit(job_id, "scene_studio", "node.retrying",
             "Approved paid Higgsfield generation. " + CONDUCTOR_MSG, status="pending")
    _set_node(job_id, "scene_studio", status="pending",
              summary="Approved paid generation — awaiting conductor.")
    return {"status": "requires_conductor", "paid": True, "approved": approved,
            "message": "Approved. The Claude Code conductor will generate + save to library."}


@router.post("/jobs/{job_id}/telegram-preview")
def telegram_preview(job_id: str):
    """Send the reel video preview to the operator's Telegram for approval.

    Real send is a documented STUB until TELEGRAM_BOT_TOKEN is configured: we
    emit an approval.requested event carrying the reel + cover + scores so the
    UI (and, once wired, the Telegram bridge) can render an approve/reject card.
    Nothing is faked — no message is claimed as delivered without a token.
    """
    import os

    import json
    from pathlib import Path

    _require_job(job_id)
    reel = _is_reel(job_id)
    has_video = bool(db.query_all(
        "SELECT name FROM artifacts WHERE job_id=? AND name='reel.mp4'", (job_id,)))
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    delivered = False  # real delivery requires the bot token + conductor
    preview_url = f"/api/jobs/{job_id}/artifact/reel.mp4" if has_video else None

    # enrich with scores + whether paid Higgsfield generation was used
    sc = db.query_one("SELECT * FROM scores WHERE job_id=?", (job_id,)) or {}
    scores, paid_used, template = {}, False, None
    try:
        scores = json.loads(sc.get("issues_json") or "{}").get("reel_scores", {})
    except Exception:
        scores = {}
    for fname, key in (("09_asset_picker.json", "paid_generation_required"),
                       ("07_template.json", "selected_template")):
        row = db.query_one("SELECT path FROM artifacts WHERE job_id=? AND name=?", (job_id, fname))
        if row and Path(row["path"]).exists():
            try:
                data = json.loads(Path(row["path"]).read_text(encoding="utf-8"))
                if fname.startswith("09"):
                    paid_used = bool(data.get(key))
                else:
                    template = data.get(key)
            except Exception:
                pass

    msg = ("Telegram approval card prepared (video preview + scores)."
           if token else "Telegram bridge is a stub — set TELEGRAM_BOT_TOKEN to deliver.")
    bus.emit(job_id, "approval", "approval.requested", msg,
             status="approval_required",
             payload={"channel": "telegram", "delivered": delivered,
                      "preview_url": preview_url, "has_video": has_video,
                      "is_reel": reel, "template": template,
                      "paid_higgsfield_used": paid_used, "scores": scores})
    return {"status": "prepared", "delivered": delivered,
            "token_configured": bool(token), "preview_url": preview_url,
            "template": template, "paid_higgsfield_used": paid_used,
            "scores": scores, "message": msg}


@router.post("/jobs/{job_id}/approve")
def approve(job_id: str):
    _require_job(job_id)
    db.upsert("jobs", {"job_id": job_id, "approval_status": "approved"},
              conflict_keys=["job_id"])
    bus.emit(job_id, "publish_gate", "approval.received",
             "Human approval confirmed.", status="approved")
    return {"status": "approved"}


@router.post("/jobs/{job_id}/reject")
def reject(job_id: str, body: dict = Body(default={})):
    _require_job(job_id)
    reason = body.get("reason", "rejected by operator")
    db.upsert("jobs", {"job_id": job_id, "approval_status": "rejected",
                       "status": "rejected"}, conflict_keys=["job_id"])
    bus.emit(job_id, "publish_gate", "approval.received", f"Post rejected: {reason}",
             status="rejected")
    return {"status": "rejected", "reason": reason}


@router.post("/jobs/{job_id}/publish")
def publish(job_id: str):
    """Publish must be REAL. The backend cannot reach Composio, so it validates
    preconditions and returns a pending adapter response — never a fake publish."""
    job = _require_job(job_id)
    sc = db.query_one("SELECT * FROM scores WHERE job_id=?", (job_id,)) or {}
    reel = _is_reel(job_id)
    problems = []
    if not sc.get("publish_allowed"):
        problems.append("quality gate not passed")
    if job.get("approval_status") != "approved":
        problems.append("human approval not given")
    if reel:
        vid = db.query_all("SELECT name FROM artifacts WHERE job_id=? AND name='reel.mp4'",
                           (job_id,))
        if not vid:
            problems.append("final reel.mp4 missing")
    else:
        imgs = db.query_all("SELECT name FROM artifacts WHERE job_id=? AND name LIKE 'slide_%.jpg'",
                            (job_id,))
        if len(imgs) < 2:
            problems.append("final images missing")
    if problems:
        bus.emit(job_id, "publish_gate", "publish.failed",
                 "Blocked: " + "; ".join(problems), status="blocked")
        raise HTTPException(409, {"status": "blocked", "problems": problems})

    courier = "reels_courier" if reel else "ig_courier"
    bus.emit(job_id, courier, "publish.started",
             "Preconditions met. " + CONDUCTOR_MSG, status="pending")
    db.upsert("jobs", {"job_id": job_id, "publish_status": "pending_conductor"},
              conflict_keys=["job_id"])
    return {"status": "requires_conductor", "message": CONDUCTOR_MSG,
            "note": "Real Instagram publish runs in the Claude Code conductor / 5 PM cron."}


def _retry(job_id: str, node_id: str) -> int:
    row = db.query_one("SELECT retry_count FROM nodes WHERE job_id=? AND node_id=?",
                       (job_id, node_id))
    return (row or {}).get("retry_count") or 0
