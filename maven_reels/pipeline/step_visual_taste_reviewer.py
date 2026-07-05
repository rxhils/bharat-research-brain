"""Agent — Visual Taste Reviewer (Maven Reels Newsroom). Honest, free.

Chunk 4: scores the generated frames for premium look / typography / popup /
fake-text / AI-slop. The backend has NO vision model, so — like the Scene Vision
Inspector — it does NOT fabricate a verdict. It reads any real vision review
(scene_vision) that a vision-capable reviewer filled in, applies the strict
non-negotiable gate, and otherwise marks review_required. Writes 43_visual_taste.json.

Hard gate (only enforced when real frame scores exist):
  typography >= 90, first_frame >= 92, realism >= 90, popup_design >= 88,
  ai_slop_risk <= 15.
"""
from __future__ import annotations

from . import state

GATE = {"typography": 90, "first_frame": 92, "realism": 90, "popup_design": 88,
        "ai_slop_risk_max": 15}


def run(date: str) -> dict:
    vision = _opt(date, "scene_vision") or {}
    reviewed = bool(vision.get("vision_review_available"))
    reviews = vision.get("scene_reviews", [])

    if not reviewed:
        payload = {
            "date": date, "review_available": False, "review_required": True,
            "gate": GATE,
            "note": "No vision review yet — the backend cannot score visual taste without a "
                    "vision model. A vision-capable reviewer must score the frames "
                    "(scene_vision) before this gate can pass. Not faking a verdict.",
            "passed": None,
        }
        state.save_artifact(date, "visual_taste", payload)
        return payload

    def avg(field, default=None):
        vals = [r[field] for r in reviews if r.get(field) is not None]
        return round(sum(vals) / len(vals)) if vals else default

    realism = avg("realism_score", 0)
    typography = avg("typography_score", avg("realism_score", 0))
    popup = avg("popup_design_score", typography)
    first_frame = next((r.get("first_frame_score") for r in reviews
                        if r.get("scene_id", "").endswith("01")), None) or realism
    slop = avg("ai_slop_risk", 0) or (40 if vision.get("fake_text_scenes") else 0)
    fake_text = bool(vision.get("fake_text_scenes"))

    fails = []
    if typography < GATE["typography"]: fails.append(f"typography {typography} < {GATE['typography']}")
    if first_frame < GATE["first_frame"]: fails.append(f"first_frame {first_frame} < {GATE['first_frame']}")
    if realism < GATE["realism"]: fails.append(f"realism {realism} < {GATE['realism']}")
    if popup < GATE["popup_design"]: fails.append(f"popup_design {popup} < {GATE['popup_design']}")
    if slop > GATE["ai_slop_risk_max"]: fails.append(f"ai_slop_risk {slop} > {GATE['ai_slop_risk_max']}")
    if fake_text: fails.append(f"fake text in {', '.join(vision['fake_text_scenes'])}")

    payload = {
        "date": date, "review_available": True, "review_required": False,
        "scores": {"typography": typography, "first_frame": first_frame,
                   "realism": realism, "popup_design": popup, "ai_slop_risk": slop},
        "gate": GATE, "failures": fails, "passed": len(fails) == 0,
        "reroute_to": ("scene_generator" if fake_text or realism < GATE["realism"]
                       else "production_prompts" if typography < GATE["typography"] else ""),
        "verdict": "premium visual quality" if not fails else
                   f"visual taste gate FAILED: {'; '.join(fails)}",
    }
    state.save_artifact(date, "visual_taste", payload)
    return payload


def _opt(date: str, key: str):
    try:
        return state.load_artifact(date, key)
    except Exception:
        return None
