"""Health, meta, and settings endpoints."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Body

from .. import database as db
from ..events import IST, bus
from ..registry import AGENT_TYPE_LABELS
from ..services.runner import is_trading_day
from ..settings_store import get_settings, update_settings

router = APIRouter(prefix="/api")


@router.get("/health")
def health():
    counts = {t: db.query_one(f"SELECT COUNT(*) AS n FROM {t}")["n"]
              for t in ("jobs", "nodes", "events", "artifacts")}
    return {"status": "ok", "service": "Maven Newsroom OS", "db": counts,
            "time_ist": datetime.now(IST).isoformat(timespec="seconds")}


@router.get("/meta")
def meta():
    today = datetime.now(IST).strftime("%Y-%m-%d")
    open_, reason = is_trading_day(today)
    s = get_settings()
    return {
        "product": "Maven Newsroom OS",
        "subtitle": "Daily Indian Market Intelligence Engine",
        "date_ist": today,
        "market": {"open": open_, "reason": reason},
        "next_run": s["schedule_label"],
        "run_name": s["run_name"],
        "trigger_agent": s["trigger_agent"],
        "type_labels": AGENT_TYPE_LABELS,
        "thresholds": s["thresholds"],
    }


@router.get("/settings")
def read_settings():
    return get_settings()


@router.post("/settings")
def write_settings(patch: dict = Body(default={})):
    merged = update_settings(patch)
    tg = merged.get("integrations", {}).get("telegram", {})
    bus.configure_telegram(tg.get("status") == "connected", tg.get("verbose", False))
    return merged
