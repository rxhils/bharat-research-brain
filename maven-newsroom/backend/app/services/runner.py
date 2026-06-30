"""Closing Bell runner: trading-day guard + a live SIMULATION run to watch.

The simulation animates the real pipeline order with structured events and
realistic timing, using the most recent real run as its content template. It is
explicitly run_type="simulation" and STOPS at the publish gate with
approval_required — it never calls Instagram and never claims a publish. A real
publishing run happens in the Claude Code conductor / 5 PM cron, which can reach
the Higgsfield + Composio MCPs.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import date as date_cls
from datetime import datetime

from .. import database as db
from ..config import NSE_HOLIDAYS_2026, OUTPUT_ROOT
from ..events import IST, bus
from ..registry import GRAPH_ORDER, NODES_BY_ID
from . import ingest

SIM_SECONDS = {
    "closing_bell": 0.6, "claude_conductor": 0.8, "market_sentinel": 2.4,
    "conviction_gate": 0.6, "slide_architect": 0.8, "art_director": 0.7,
    "prompt_forge": 0.9, "nano_studio": 2.6, "pixel_lab": 1.0,
    "caption_desk": 0.7, "hashtag_desk": 0.6, "compliance_shield": 0.7,
    "meta_auditor": 1.0, "publish_gate": 0.9,
}


def is_trading_day(d: str) -> tuple[bool, str]:
    try:
        dt = date_cls.fromisoformat(d)
    except Exception:
        return False, "invalid date"
    if dt.weekday() >= 5:
        return False, "weekend"
    if d in NSE_HOLIDAYS_2026:
        return False, "NSE/BSE holiday"
    return True, "open"


def _now() -> str:
    return datetime.now(IST).isoformat(timespec="seconds")


def _set_node(job_id, node_id, **fields):
    spec = NODES_BY_ID[node_id]
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


# Backwards-compatible alias used by route handlers.
_set_agent = _set_node


def _template():
    dates = ingest.list_run_dates()
    if not dates:
        return {}
    d = OUTPUT_ROOT / dates[-1]
    out = {}
    for k, f in (("research", "01_research.json"),
                 ("creative", "03_creative_direction.json")):
        p = d / f
        if p.exists():
            try:
                out[k] = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
    return out


def create_simulation_job(run_date: str | None = None) -> dict:
    d = run_date or datetime.now(IST).strftime("%Y-%m-%d")
    open_, reason = is_trading_day(d)
    job_id = f"sim-{d}-{uuid.uuid4().hex[:6]}"

    db.upsert("jobs", {
        "job_id": job_id, "run_type": "simulation", "date": d,
        "market_status": "open" if open_ else "closed",
        "scheduled_time": "17:00 IST", "started_at": _now(), "created_at": _now(),
        "current_node": "closing_bell", "approval_status": "pending",
        "publish_status": "not_published", "instagram_post_id": None,
        "instagram_post_url": None, "completed_at": None,
        "summary": "Simulated Closing Bell run for the live dashboard.",
        "status": "running" if open_ else "skipped",
    }, conflict_keys=["job_id"])

    if not open_:
        bus.emit(job_id, "closing_bell", "job.skipped_market_closed",
                 f"Market closed today ({reason}). No daily Maven post generated.",
                 status="skipped", payload={"reason": reason})
        return {"job_id": job_id, "status": "skipped", "reason": reason}

    bus.emit(job_id, "closing_bell", "job.created",
             f"Closing Bell triggered (simulation) for {d}.", status="running")
    return {"job_id": job_id, "status": "running", "reason": reason}


async def run_simulation(job_id: str) -> None:
    tmpl = _template()
    research = tmpl.get("research", {})
    n = len(research.get("top_3_stories", [])) or 3
    selected = (tmpl.get("creative", {}) or {}).get("selected", "Hybrid Cover+Cards")
    summaries = {
        "closing_bell": "Indian market open — full workflow started.",
        "claude_conductor": "Bridging Python + Higgsfield/Composio MCP.",
        "market_sentinel": f"{n} verified market-moving stories found.",
        "conviction_gate": f"{n} cleared importance>=7 & confidence>=8.",
        "slide_architect": "3-slide carousel plan built.",
        "art_director": f"Direction: {selected}.",
        "prompt_forge": "3 unique slide prompts forged.",
        "nano_studio": "3 images via nano_banana_pro (simulated render).",
        "pixel_lab": "Cropped to 1080x1350, JPEG, <8MB.",
        "caption_desk": "Caption written, compliant.",
        "hashtag_desk": "16 hashtags.",
        "compliance_shield": "Clean — no advisory/hype language.",
        "meta_auditor": "content 100 / design 94 / compliance 100 -> PUBLISH_OK",
        "publish_gate": "Preflight passed — awaiting human approval.",
    }

    bus.emit(job_id, "closing_bell", "job.started", "Closing Bell Run started.",
             status="running")

    for node_id in GRAPH_ORDER:
        if node_id == "ig_courier":
            break  # never auto-publish from the simulation
        secs = SIM_SECONDS.get(node_id, 0.8)
        spec = NODES_BY_ID[node_id]
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
        if node_id == "compliance_shield":
            bus.emit(job_id, node_id, "quality.started", "Running compliance scan…")
        if node_id == "meta_auditor":
            bus.emit(job_id, node_id, "quality.passed",
                     "content 100 / design 94 / compliance 100", status="PUBLISH_OK")
        bus.emit(job_id, node_id, "node.completed", summary, status="completed")

    _set_node(job_id, "ig_courier", status="approval_required", progress=0,
              summary="Awaiting approval — real publish runs in the Claude Code conductor.")
    _set_node(job_id, "run_vault", status="completed", progress=100,
              completed_at=_now(), summary="Run state + artifacts stored.")
    db.upsert("jobs", {"job_id": job_id, "status": "awaiting_approval",
                       "approval_status": "required", "current_node": "publish_gate",
                       "completed_at": _now()}, conflict_keys=["job_id"])
    bus.emit(job_id, "ig_courier", "approval.required",
             "Quality gate passed. Human approval required before publishing.",
             status="approval_required")
