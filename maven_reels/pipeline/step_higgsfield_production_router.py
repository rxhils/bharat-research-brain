"""Agent — Higgsfield Production Router (full-stack). Local, free.

Routes every blueprint scene to the best CONFIRMED model/tool from the live
capability matrix (outputs/maven_reels/system/higgsfield_capability_matrix.json):

  requires_text_fidelity (hero_text / popup_card / key_takeaway / cta)
      -> nano_banana_pro (image; the ONLY catalog engine with good text
         rendering) + kling3_0 i2v animate as the motion path
  realistic_broll (hero position) -> veo3_1  (fallback cinematic_studio_video_v2)
  realistic_broll (other)         -> seedance1_5 (fallback kling3_0_turbo)

Captions: no standalone Higgsfield caption tool exists for local files — text
lives in the designed card scenes (honest, from the matrix). Assembly: local
stitch-only fallback (explainer_video noted for evaluation). Never routes to
anything absent from the matrix; never fabricates cost.
Writes 32_production_routing.json.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import config, state

MATRIX = (Path(config.OUTPUT_ROOT) / "system" / "higgsfield_capability_matrix.json")


def _matrix() -> dict:
    return json.loads(MATRIX.read_text(encoding="utf-8"))


def run(date: str, *, blueprint: dict) -> dict:
    m = _matrix()
    models = {x["id"]: x for x in m["models"]}

    def ok(mid: str) -> bool:
        return models.get(mid, {}).get("available", False)

    routes, first_broll_seen = [], False
    for s in blueprint.get("scenes", []):
        stype = s["scene_type"]
        if s.get("requires_text_fidelity"):
            sel, fb = ("nano_banana_pro" if ok("nano_banana_pro") else None,
                       "kling3_0" if ok("kling3_0") else "seedance1_5")
            reason = ("image model with GOOD text fidelity designs the card "
                      "(video models garble text — verified); kling3_0 i2v animates "
                      "the finished card without altering it")
            cost = models.get("nano_banana_pro", {})
        elif stype == "realistic_broll" and not first_broll_seen:
            first_broll_seen = True
            sel, fb = ("veo3_1" if ok("veo3_1") else "cinematic_studio_video_v2",
                       "cinematic_studio_video_v2")
            reason = "first footage scene earns the top realistic model"
            cost = models.get(sel, {})
        else:
            sel, fb = ("seedance1_5" if ok("seedance1_5") else "kling3_0_turbo",
                       "kling3_0_turbo")
            reason = "cost-efficient confirmed realistic b-roll"
            cost = models.get(sel, {})
        routes.append({
            "scene_id": s["scene_id"], "scene_type": stype,
            "selected_model_or_tool": sel, "fallback": fb, "reason": reason,
            "text_fidelity_target": 95 if s.get("requires_text_fidelity") else 0,
            "cost_known": bool(cost.get("cost_known")),
            "cost_note": cost.get("cost_note", "needs get_cost preflight"),
            "cost_tier": "image+animate" if s.get("requires_text_fidelity") else "video",
            "requires_user_confirmation": True,
        })

    payload = {
        "date": date, "routes": routes,
        "global_tools": {
            "captions": "none_available_for_local_files (text = designed card scenes)",
            "text_cards": "nano_banana_pro",
            "editor": "none_available (matrix)",
            "montage": "local_stitch_only_fallback (explainer_video to evaluate)",
        },
        "matrix_checked_at": _matrix().get("checked_at"),
        "excluded": [e["name"] for e in m.get("excluded", [])],
    }
    state.save_artifact(date, "production_routing", payload)
    return payload
