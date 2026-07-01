"""Reels runner — trading-day guard + a live SIMULATION run for the dashboard.

Animates the 22 reel nodes with structured events and realistic timing, marks the
external media nodes (Scene/Voice/Cover/Reels Courier) as pending, and STOPS at
the reel-auditor/approval gate. Never fakes media or a publish. run_type="reel-sim".
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime

from .. import database as db
from ..events import IST, bus
from ..registry_reels import REEL_GRAPH_ORDER, REEL_NODES_BY_ID
from .runner import is_trading_day  # reuse the shared trading-day check

SIM_SECONDS = {n: 0.7 for n in REEL_GRAPH_ORDER}
SIM_SECONDS.update({"market_sentinel": 2.2, "scene_studio": 2.4, "voice_studio": 1.6,
                    "cut_room": 1.8, "cover_studio": 1.4})
# External media nodes: shown pending in a no-media simulation.
PENDING_NODES = {"scene_studio", "voice_studio", "cover_studio", "reels_courier",
                 "signal_tracker"}
SUMMARIES = {
    "closing_bell": "Reel workflow started.",
    "claude_conductor": "Bridging Python + Higgsfield/Composio.",
    "market_sentinel": "Found reel-worthy stories.",
    "viral_fit": "Picked the best REEL story (not just the most important).",
    "angle_studio": "Framed a scroll-stopping angle.",
    "hook_lab": "7 hook buckets scored; strongest chosen.",
    "script_room": "Timed 20-35s script written.",
    "retention_editor": "Cut filler, tightened pacing under 35s.",
    "storyboard": "5-7 scenes planned.",
    "visual_director": "Dark-terminal design system selected.",
    "subtitle_engine": "Captions timed.",
    "cut_room": "ffmpeg reel assembled (requires generated scenes).",
    "caption_desk": "Reel caption + hashtags written.",
    "compliance_shield": "Clean — no advisory/hype language.",
    "reel_auditor": "hook 88 / retention 100 / compliance 100 — visual needs the real video.",
    "publish_gate": "Awaiting the real reel + human approval.",
}


def _now() -> str:
    return datetime.now(IST).isoformat(timespec="seconds")


def _set(job_id, nid, **f):
    s = REEL_NODES_BY_ID[nid]
    base = {"job_id": job_id, "node_id": nid, "node_name": s["name"],
            "component_class": s["component_class"], "component_type": s["component_type"],
            "intelligent": int(s["intelligent"]), "actual_component": s["actual_component"],
            "external": int(s["external"]), "in_graph": int(s["in_graph"]),
            "role": s["role"], "ord": s["order"]}
    base.update(f)
    db.upsert("nodes", base, conflict_keys=["job_id", "node_id"])


def create_simulation_job(run_date: str | None = None) -> dict:
    d = run_date or datetime.now(IST).strftime("%Y-%m-%d")
    open_, reason = is_trading_day(d)
    job_id = f"reel-sim-{d}-{uuid.uuid4().hex[:5]}"
    db.upsert("jobs", {
        "job_id": job_id, "run_type": "reel-sim", "pipeline": "reel", "date": d,
        "market_status": "open" if open_ else "closed", "scheduled_time": "17:00 IST",
        "started_at": _now(), "created_at": _now(), "current_node": "closing_bell",
        "approval_status": "pending", "publish_status": "not_published",
        "instagram_post_id": None, "instagram_post_url": None, "completed_at": None,
        "summary": "Simulated Reel run for the live dashboard.",
        "status": "running" if open_ else "skipped",
    }, conflict_keys=["job_id"])
    if not open_:
        bus.emit(job_id, "closing_bell", "job.skipped_market_closed",
                 f"Market closed ({reason}). No reel today.", status="skipped")
        return {"job_id": job_id, "status": "skipped", "reason": reason}
    bus.emit(job_id, "closing_bell", "job.created",
             f"Reel Closing Bell triggered (simulation) for {d}.", status="running")
    return {"job_id": job_id, "status": "running"}


async def run_simulation(job_id: str) -> None:
    bus.emit(job_id, "closing_bell", "job.started", "Reel run started.", status="running")
    for nid in REEL_GRAPH_ORDER:
        if nid in ("reels_courier", "signal_tracker"):
            break
        spec = REEL_NODES_BY_ID[nid]
        db.upsert("jobs", {"job_id": job_id, "current_node": nid}, conflict_keys=["job_id"])
        if nid in PENDING_NODES:
            _set(job_id, nid, status="pending", summary="Requires Claude Code conductor (Higgsfield MCP).")
            bus.emit(job_id, nid, "node.retrying", f"{spec['name']} needs the conductor (no media in sim).", status="pending")
            continue
        secs = SIM_SECONDS.get(nid, 0.7)
        _set(job_id, nid, status="running", started_at=_now(), progress=0)
        bus.emit(job_id, nid, "node.started", f"{spec['name']} started", status="running")
        await asyncio.sleep(secs)
        summary = SUMMARIES.get(nid, f"{spec['name']} completed.")
        _set(job_id, nid, status="completed", progress=100, completed_at=_now(),
             duration_ms=int(secs * 1000), summary=summary)
        if nid == "compliance_shield":
            bus.emit(job_id, nid, "quality.started", "Running compliance scan…")
        if nid == "reel_auditor":
            bus.emit(job_id, nid, "quality.passed", "hook 88 / retention 100 / compliance 100", status="PUBLISH_OK")
        bus.emit(job_id, nid, "node.completed", summary, status="completed")

    _set(job_id, "reels_courier", status="approval_required",
         summary="Awaiting real reel + approval — publish runs in the conductor.")
    _set(job_id, "signal_tracker", status="pending", summary="Analytics after a real publish.")
    _set(job_id, "run_vault", status="completed", progress=100, completed_at=_now(),
         summary="Reel state + artifacts stored.")
    db.upsert("jobs", {"job_id": job_id, "status": "awaiting_approval",
                       "approval_status": "required", "current_node": "publish_gate",
                       "completed_at": _now()}, conflict_keys=["job_id"])
    bus.emit(job_id, "reels_courier", "approval.required",
             "Reel gate passed. Human approval required before publishing.",
             status="approval_required")
