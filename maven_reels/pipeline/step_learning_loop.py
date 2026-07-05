"""Agent — Learning Loop (Maven Reels Newsroom). Local, free.

Chunk 6: turns REAL post-publish metrics into signal for future decisions.
Reads the reel_metrics table + each published reel's format / hook bucket /
visual pack / saveable lesson, aggregates saves+shares-weighted performance per
dimension, and writes system/reel_performance.json. The Story+Format Selector
consults it as a light tie-breaker (never overrides sourced relevance).

No fabricated metrics — only reels that have real recorded numbers count.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import config, state

PERF_PATH = Path(config.OUTPUT_ROOT) / "system" / "reel_performance.json"


def _opt(job_id: str, key: str):
    try:
        return state.load_artifact(job_id, key)
    except Exception:
        return None


def _engagement(m: dict) -> float:
    """Saves + shares are the strongest spread signals; weight them heavily."""
    s = lambda k: float(m.get(k) or 0)
    return s("saves") * 3 + s("shares") * 3 + s("likes") + s("comments") + s("views") * 0.01


def rebuild(metrics_rows: list[dict]) -> dict:
    """metrics_rows: list of reel_metrics dicts (each has job_id + numbers)."""
    dims = {"format": {}, "hook_bucket": {}, "visual_pack": {}, "saveable_lesson": {}}
    n_used = 0
    for m in metrics_rows:
        if not any(m.get(k) for k in ("saves", "shares", "views", "likes")):
            continue  # no real numbers → skip, never invent
        job = m.get("job_id")
        sf = _opt(job, "story_format") or {}
        hk = _opt(job, "hooks_format") or {}
        vp = _opt(job, "visual_pack") or {}
        sv = _opt(job, "script_saveable") or {}
        eng = _engagement(m)
        n_used += 1
        for dim, val in (("format", sf.get("selected_format")),
                         ("hook_bucket", hk.get("hook_bucket")),
                         ("visual_pack", vp.get("selected_pack")),
                         ("saveable_lesson", sv.get("saveable_lesson_key"))):
            if not val:
                continue
            d = dims[dim].setdefault(val, {"n": 0, "engagement": 0.0})
            d["n"] += 1
            d["engagement"] += eng

    # normalise each dimension to a 0.8-1.2 boost around its mean
    boosts = {}
    for dim, vals in dims.items():
        if not vals:
            boosts[dim] = {}
            continue
        avg = sum(v["engagement"] / v["n"] for v in vals.values()) / len(vals)
        boosts[dim] = {}
        for k, v in vals.items():
            mean_eng = v["engagement"] / v["n"]
            ratio = (mean_eng / avg) if avg else 1.0
            boosts[dim][k] = round(max(0.8, min(1.2, ratio)), 3)

    payload = {"reels_with_metrics": n_used, "dimensions": dims, "boosts": boosts,
               "note": "Empirical performance boosts (0.8-1.2) from real saves/shares. "
                       "Consulted as a tie-breaker only — never overrides sourced relevance."}
    PERF_PATH.parent.mkdir(parents=True, exist_ok=True)
    PERF_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def load_performance() -> dict:
    if not PERF_PATH.exists():
        return {"reels_with_metrics": 0, "boosts": {}}
    return json.loads(PERF_PATH.read_text(encoding="utf-8"))


def format_boost(format_id: str) -> float:
    return float(load_performance().get("boosts", {}).get("format", {}).get(format_id, 1.0))
