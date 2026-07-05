"""Agent — 3-Variant Blueprint Lab (Maven Reels Newsroom). Local, free.

Before spending ANY Higgsfield credits, generate THREE competing blueprints for
the selected story and pick the best on a viral score:
  Variant A — Contrarian hook
  Variant B — Hidden mechanism
  Variant C — Saveable lesson
Each variant = first frame + hook + script skeleton + scene plan + text cards +
popup cards + model plan + estimated cost + viral score. Deterministic scoring;
no LLM, no credits. Writes 37_reel_variants.json.

The winner feeds the Higgsfield Blueprint / Production Router downstream.
"""
from __future__ import annotations

from . import config, format_taxonomy, state
from .reel_template_library import template_for
from .step_viral_reference_bank import patterns_for, reject_hooks

# per-scene credit estimate by routed model (from the live capability matrix)
_COST = {"nano_banana_pro": 2.0, "veo3_1": 11.0, "seedance1_5": 4.8}

_ANGLES = [
    ("A", "contrarian", "Contrarian hook", "surface_is_wrong"),
    ("B", "hidden_mechanism", "Hidden mechanism", "reveal_underneath"),
    ("C", "saveable_lesson", "Saveable lesson", "one_lesson"),
]


def _short(text: str, n: int) -> str:
    return " ".join((text or "").split()[:n]).upper()


def _hook_for(angle_key: str, fmt: dict, story: dict) -> str:
    sector = (story.get("sector") or "the market").strip()
    base = {
        "A": f"{sector} wasn't the real story.",
        "B": fmt["example_hook"],
        "C": f"Most investors misread {sector}.",
    }[angle_key]
    return base


def _scene_plan(tpl: dict, fmt: dict, story: dict, hook: str) -> list[dict]:
    """Map the template beats to concrete scenes with exact card text + model."""
    anchor = fmt["teaching_anchor"]
    headline = story.get("headline") or story.get("title") or fmt["name"]
    card_text = {
        "hook": _short(hook, 6),
        "mechanism": _short(headline, 6),
        "cause": _short(headline, 6),
        "reality": _short(anchor, 6),
        "mistake": _short(anchor, 6),
        "transmission": _short(headline, 6),
        "lesson": _short(anchor, 6),
        "cta": "UNDERSTAND THE MARKET WITH MAVEN",
    }
    scenes = []
    for i, beat in enumerate(tpl.get("beats", []), 1):
        st = beat["scene_type"]
        is_card = st in ("hero_text", "popup_card", "key_takeaway", "cta")
        model = ("nano_banana_pro" if is_card
                 else "veo3_1" if beat.get("role") in ("context", "sector", "policy",
                                                       "headline", "setup", "pov") and i <= 3
                 else "seedance1_5")
        scenes.append({
            "scene_id": f"shot_{i:02d}", "scene_type": st, "role": beat.get("role"),
            "requires_text_fidelity": is_card,
            "exact_text": card_text.get(beat.get("role"), "") if is_card else "",
            "popup": beat.get("popup") if st == "popup_card" else None,
            "footage_world": beat.get("world") if not is_card else None,
            "model": model,
            "duration": _beat_seconds(beat.get("t", "")),
        })
    return scenes


def _beat_seconds(t: str) -> float:
    try:
        a, b = t.split("-"); return round(float(b) - float(a), 1)
    except Exception:
        return 3.0


def _viral_score(hook: str, scenes: list[dict], fmt: dict) -> tuple[int, dict]:
    words = len(hook.split())
    specificity = 25 if any(c.isdigit() for c in hook) or fmt["id"] != "hidden_mechanism" else 18
    first_frame = 20 if words <= 8 else 12
    curiosity = 20 if hook.rstrip(".").lower() not in [h.lower() for h in reject_hooks()] else 4
    truth = 15
    cards = [s for s in scenes if s["requires_text_fidelity"]]
    save_share = 10 if any(s["role"] == "lesson" for s in scenes) else 5
    visual = 10 if len(scenes) >= 6 and cards else 6
    breakdown = {"specificity": specificity, "first_frame_clarity": first_frame,
                 "curiosity": curiosity, "truthfulness": truth,
                 "save_share_potential": save_share, "visual_potential": visual}
    return sum(breakdown.values()), breakdown


def run(date: str) -> dict:
    sf = _opt(date, "story_format") or {}
    fid = sf.get("selected_format", "hidden_mechanism")
    fmt = format_taxonomy.get(fid)
    tpl = template_for(fid)
    ref = patterns_for(fid)
    story = sf.get("selected_story", {})

    variants = []
    for key, angle_id, label, mode in _ANGLES:
        hook = _hook_for(key, fmt, story)
        scenes = _scene_plan(tpl, fmt, story, hook)
        score, breakdown = _viral_score(hook, scenes, fmt)
        est_cost = round(sum(_COST.get(s["model"], 5.0) for s in scenes), 1)
        variants.append({
            "variant": key, "angle": angle_id, "label": label,
            "first_frame": ref.get("first_frame"),
            "hook": hook,
            "script_skeleton": [
                f"Hook: {hook}",
                f"What: {story.get('headline') or fmt['name']}",
                f"Why: {fmt['when_to_use']}",
                f"Lesson: {fmt['teaching_anchor']}",
                "Maven CTA: Understand the market with Maven.",
            ],
            "scene_plan": scenes,
            "text_cards": [{"scene_id": s["scene_id"], "exact_text": s["exact_text"]}
                           for s in scenes if s["requires_text_fidelity"]],
            "popup_cards": [{"scene_id": s["scene_id"], "popup": s["popup"]}
                            for s in scenes if s["scene_type"] == "popup_card"],
            "model_plan": {s["scene_id"]: s["model"] for s in scenes},
            "estimated_cost_credits": est_cost,
            "viral_score": score, "viral_breakdown": breakdown,
        })

    winner = max(variants, key=lambda v: (v["viral_score"], -v["estimated_cost_credits"]))
    payload = {
        "date": date, "format": fid, "format_name": fmt["name"],
        "variants": variants,
        "chosen_variant": winner["variant"],
        "chosen_reason": f"highest viral score ({winner['viral_score']}) at "
                         f"{winner['estimated_cost_credits']}cr",
        "note": "Blueprints only — no credits spent. Winner feeds the Higgsfield Blueprint.",
    }
    state.save_artifact(date, "reel_variants", payload)
    return payload


def _opt(date: str, key: str):
    try:
        return state.load_artifact(date, key)
    except Exception:
        return None
