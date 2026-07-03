"""Step — Higgsfield Model Router.

For every planned shot, pick the CHEAPEST Higgsfield video model that satisfies
that scene's complexity tier — never one model for everything, never the most
expensive by default, and every choice comes with a written reason + fallback.

Model metadata lives in model_cost_config.json (editable; costs marked
confirmed were preflighted via get_cost). The Claude Code conductor can refresh
the file from models_explore — the backend itself cannot reach MCP, so the
config file is the source of truth at run time.

Cost guard: if the reel's total estimate exceeds MAX_REEL_GENERATION_COST the
plan is BLOCKED (requires_ui_confirmation stays true regardless — paid
generation always needs the operator's click).
"""
from __future__ import annotations

import json
from pathlib import Path

from . import config, state

CONFIG_PATH = Path(__file__).resolve().parent / "model_cost_config.json"
REALISTIC_MAP_PATH = Path(__file__).resolve().parent / "model_router_realistic_map.json"

# shot purpose -> complexity tier
TIER_OF = {"hook": "hero_motion", "data": "medium_motion", "reason": "medium_motion",
           "context": "simple_motion", "impact": "simple_motion", "cta": "simple_motion"}
# tier -> minimum acceptable quality tiers (ordered weakest-acceptable first)
TIER_QUALITY = {"simple_motion": ("standard", "good", "cinematic"),
                "medium_motion": ("good", "cinematic"),
                "hero_motion": ("cinematic",),
                }
QUALITY_TARGET = {"simple_motion": 80, "medium_motion": 85, "hero_motion": 90}


def _models() -> list[dict]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))["models"]


def _pick(tier: str, duration: float) -> tuple[dict | None, dict | None]:
    """(selected, fallback): cheapest model meeting the tier's quality floor,
    9:16 + duration + text-to-video support required."""
    ok = [m for m in _models()
          if m.get("supports_9_16") and m.get("supports_text_to_video")
          and m.get("max_duration", 0) >= duration
          and m.get("quality_tier") in TIER_QUALITY[tier]]
    ok.sort(key=lambda m: (float(m.get("relative_cost", 999)),
                           0 if m.get("reliability") == "high" else 1))
    return (ok[0] if ok else None), (ok[1] if len(ok) > 1 else (ok[0] if ok else None))


def run(date: str, *, shot_plan: dict) -> dict:
    plan, total = [], 0.0
    for s in shot_plan.get("shots", []):
        tier = TIER_OF.get(s["purpose"], "simple_motion")
        sel, fb = _pick(tier, config.HIGGSFIELD_GEN_CLIP_SECONDS)
        if sel is None:
            plan.append({"scene_id": s["shot_id"], "scene_complexity": tier,
                         "selected_model": None, "fallback_model": None,
                         "reason": "no configured model satisfies this tier",
                         "estimated_cost": None, "quality_target": QUALITY_TARGET[tier]})
            continue
        cost = float(sel.get("relative_cost", 0))
        total += cost
        plan.append({
            "scene_id": s["shot_id"], "purpose": s["purpose"],
            "scene_complexity": tier,
            "selected_model": sel["model"],
            "reason": (f"cheapest {sel['quality_tier']}-tier model meeting the "
                       f"{tier} floor at {cost}cr"
                       + ("" if sel.get("cost_confirmed") else " (cost estimated)")),
            "estimated_cost": cost,
            "fallback_model": (fb or {}).get("model"),
            "quality_target": QUALITY_TARGET[tier],
        })

    over = total > config.MAX_REEL_GENERATION_COST
    payload = {
        "date": date, "scene_model_plan": plan,
        "total_estimated_cost": round(total, 1),
        "max_reel_generation_cost": config.MAX_REEL_GENERATION_COST,
        "blocked_over_budget": over,
        "paid_generation_required": True,
        "requires_ui_confirmation": config.REQUIRE_COST_CONFIRMATION,
        "note": ("Per-scene cheapest-suitable routing from model_cost_config.json "
                 "(editable; conductor refreshes it from models_explore)."),
    }
    state.save_artifact(date, "scene_model_plan", payload)
    return payload


# ---------------------------------------------------------------------------
# Camera Router — realistic-footage routing (Newsroom rework, Chunk 1).
# Picks a model per shot by FOOTAGE TYPE (from Location Scout) using only models
# confirmed present in the live catalog. Honest about unconfirmed pricing.
# ---------------------------------------------------------------------------
def _realistic_map() -> dict:
    return json.loads(REALISTIC_MAP_PATH.read_text(encoding="utf-8"))


def _footage_type(purpose: str, world: str, m: dict) -> str:
    ov = m.get("purpose_to_type_override", {})
    if purpose in ov:
        return ov[purpose]
    world_map = m.get("footage_world_to_type", {}).get(world, {})
    return world_map.get(purpose, world_map.get("default", "real_world_broll"))


def route_realistic(date: str, *, shot_plan: dict, location_scout: dict | None = None) -> dict:
    """Per-shot realistic-footage model routing → model_routing_plan.json.
    Reads Location Scout's footage world; falls back to finance_newsroom."""
    m = _realistic_map()
    routes = {r["footage_type"]: r for r in m["routing_map"]}
    world = (location_scout or {}).get("selected_footage_world", "finance_newsroom")

    per_scene, unknown_cost = [], False
    for s in shot_plan.get("shots", []):
        ft = _footage_type(s.get("purpose", ""), world, m)
        r = routes.get(ft, routes["real_world_broll"])
        model_meta = m["confirmed_models"].get(r["preferred_model"], {})
        cost = model_meta.get("cost_credits")
        needs = model_meta.get("needs_pricing_confirmation", True)
        unknown_cost = unknown_cost or needs
        per_scene.append({
            "scene_id": s["shot_id"], "purpose": s.get("purpose"),
            "footage_type": ft,
            "selected_model": r["preferred_model"],
            "fallback_model": r["fallback_model"],
            "reason": r["quality_reason"],
            "cost_tier": r["cost_tier"],
            "estimated_cost": cost,
            "cost_confirmed": not needs,
            "needs_pricing_confirmation": needs,
            "quality_target": 90 if ft == "hero_realistic" else 82,
        })
    payload = {
        "date": date, "available_models_checked": True,
        "model_catalog_source": m["catalog_source"],
        "footage_world": world,
        "unavailable_requested": m.get("unavailable_requested", []),
        "routing_map": m["routing_map"],
        "per_scene_model_plan": per_scene,
        "pricing_note": ("Some routed models have unconfirmed credit cost — marked "
                         "needs_pricing_confirmation. Preflight with get_cost before any "
                         "real spend; never fabricate pricing."
                         if unknown_cost else "All routed model costs confirmed."),
        "paid_generation_required": True,
        "requires_ui_confirmation": True,
    }
    state.save_artifact(date, "model_routing_plan", payload)
    return payload
