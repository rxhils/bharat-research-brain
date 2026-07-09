"""Photo Reels runner: a live SIMULATION of the native photo-Reel pipeline.

Mirrors ``services/runner.py`` but walks the 10 photo-slide agents. It is
explicitly ``run_type="simulation"``: it emits structured events over the shared
bus so the dashboard graph + message feed animate, and it templates each agent's
summary from the MOST RECENT REAL photo-reel package (real headline + QA/Design
scores). It NEVER calls Higgsfield/Composio, never renders or publishes, and
stops at the package/review gate — a real publishing run happens in the Claude
Code conductor.
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import datetime

from .. import database as db
from ..config import REPO_ROOT
from ..events import IST, bus
from ..registry_photo_slides import GRAPH_ORDER_PHOTO, NODES_BY_ID_PHOTO

# The photo_slides package lives at the repo root; make it importable (same
# bootstrap as routes/photo_reels.py). Import is done lazily in _template().
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SIM_SECONDS = {
    "market_radar": 2.2, "fact_check": 0.7, "story_selector": 0.9,
    "slide_script": 0.8, "slide_design": 2.4, "design_judge": 0.9,
    "music_scout": 0.6, "viral_audio": 1.6, "export": 0.8,
    "qa_gate": 0.9, "package": 0.5,
}


def _now() -> str:
    return datetime.now(IST).isoformat(timespec="seconds")


def _set_node(job_id: str, node_id: str, **fields) -> None:
    spec = NODES_BY_ID_PHOTO[node_id]
    base = {
        "job_id": job_id, "node_id": node_id, "node_name": spec["name"],
        "component_class": spec["component_class"],
        "component_type": spec["component_type"],
        "intelligent": int(spec["intelligent"]),
        "actual_component": spec["actual_component"],
        "external": int(spec["external"]), "in_graph": int(spec["in_graph"]),
        "role": spec["role"], "ord": spec["order"],
    }
    base.update(fields)
    db.upsert("nodes", base, conflict_keys=["job_id", "node_id"])


def _template() -> dict:
    """Real fields from the latest real photo-reel package (read-only)."""
    try:
        from maven_reels.photo_slides import state as ps_state
        jobs = ps_state.list_jobs()
        if not jobs:
            return {}
        jid = jobs[0]
        sel = ps_state.load_artifact(jid, "story_selector") or {}
        qa = ps_state.load_artifact(jid, "qa_gate") or {}
        dj = ps_state.load_artifact(jid, "design_judge") or {}
        radar = ps_state.load_artifact(jid, "market_radar") or {}
        fc = ps_state.load_artifact(jid, "fact_check") or {}
        story = sel.get("selected_story") or {}
        return {
            "job_id": jid,
            "headline": story.get("headline") or "an Indian market story",
            "sector": story.get("sector_or_theme") or "Markets & Index",
            "qa": qa.get("overall_score"),
            "design": dj.get("overall_score"),
            "candidates": len(radar.get("candidate_stories") or []),
            "verified": len(fc.get("verified_stories") or []),
        }
    except Exception:
        return {}


def create_simulation_job(run_date: str | None = None) -> dict:
    d = run_date or datetime.now(IST).strftime("%Y-%m-%d")
    job_id = f"preel-{d}-{uuid.uuid4().hex[:6]}"
    db.upsert("jobs", {
        "job_id": job_id, "pipeline": "photo_reel", "run_type": "simulation",
        "date": d, "market_status": "n/a", "scheduled_time": "18:00 IST",
        "started_at": _now(), "created_at": _now(), "current_node": "market_radar",
        "approval_status": "pending", "publish_status": "not_published",
        "instagram_post_id": None, "instagram_post_url": None, "completed_at": None,
        "summary": "Simulated native photo-Reel run for the live dashboard.",
        "status": "running",
    }, conflict_keys=["job_id"])
    bus.emit(job_id, "market_radar", "job.created",
             f"Photo Reel pipeline triggered (simulation) for {d}.", status="running")
    return {"job_id": job_id, "status": "running"}


async def run_simulation(job_id: str) -> None:
    t = _template()
    hl = t.get("headline", "an Indian market story")
    sector = t.get("sector", "Markets & Index")
    qa, design = t.get("qa"), t.get("design")
    cand = t.get("candidates") or 10
    ver = t.get("verified") or cand
    summaries = {
        "market_radar": f"{cand} India market stories fetched & scored.",
        "fact_check": f"{ver} stories verified; unsourced/hype rejected.",
        "story_selector": f"Picked: “{hl}” ({sector}).",
        "slide_script": "5 slides written (hook / what / why / matters / takeaway).",
        "slide_design": "5x 1080x1920 slides rendered locally (text drawn exactly).",
        "design_judge": (f"Design {design}/100 — visual richness & layout passed."
                         if design is not None else "Visual quality reviewed."),
        "music_scout": "Licensed IG audio mood + search terms suggested.",
        "viral_audio": "Business-safe trending IG audio pick found for manual repost.",
        "export": "5 PNGs + caption + upload steps bundled as a ZIP.",
        "qa_gate": (f"QA {qa}/100 — facts/design/readability/compliance passed."
                    if qa is not None else "Deterministic QA gate passed."),
        "package": "Package ready for review (real publish runs in the conductor).",
    }

    bus.emit(job_id, "market_radar", "job.started",
             "Native Photo Reel run started (simulation).", status="running")

    for node_id in GRAPH_ORDER_PHOTO:
        secs = SIM_SECONDS.get(node_id, 0.8)
        spec = NODES_BY_ID_PHOTO[node_id]
        db.upsert("jobs", {"job_id": job_id, "current_node": node_id},
                  conflict_keys=["job_id"])
        _set_node(job_id, node_id, status="running", started_at=_now(),
                  progress=0, retry_count=0)
        bus.emit(job_id, node_id, "node.started", f"{spec['name']} started",
                 status="running")
        for p in (35, 75):
            await asyncio.sleep(secs / 2)
            _set_node(job_id, node_id, progress=p)
            bus.emit(job_id, node_id, "node.progress", f"{spec['name']} working…",
                     status="running", progress=p)
        summary = summaries.get(node_id, f"{spec['name']} completed.")
        _set_node(job_id, node_id, status="completed", progress=100,
                  completed_at=_now(), duration_ms=int(secs * 1000), summary=summary)
        if node_id == "design_judge" and design is not None:
            bus.emit(job_id, node_id, "quality.passed",
                     f"Design Judge {design}/100", status="passed")
        if node_id == "qa_gate" and qa is not None:
            bus.emit(job_id, node_id, "quality.passed",
                     f"QA gate {qa}/100 — PUBLISH_OK", status="PUBLISH_OK")
        bus.emit(job_id, node_id, "node.completed", summary, status="completed")

    db.upsert("jobs", {"job_id": job_id, "status": "completed",
                       "approval_status": "review", "current_node": "package",
                       "completed_at": _now()}, conflict_keys=["job_id"])
    bus.emit(job_id, "package", "job.completed",
             "Simulation complete — package ready for review. A real publish "
             "(Higgsfield hosting + Composio) runs in the Claude Code conductor.",
             status="completed")
