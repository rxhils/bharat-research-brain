"""Agent 3 — Photo Reel Story Selector.

Picks the ONE verified story best suited to a 5-image native photo Reel.
Deterministic ranking across: visual potential, simplicity, curiosity,
retail relevance, save/share value, compliance safety, 5-slide fit.
"""
from __future__ import annotations

import re

from . import config, state

_CURIOSITY = ["why", "how", "record", "first", "biggest", "surprise", "falls",
              "jumps", "surges", "crashes", "hits", "despite", "but"]
_RETAIL_THEMES = {"Markets & Index", "Banking", "Policy & Macro", "IT & AI",
                  "Auto", "IPO & Deals"}


def _dims(story: dict) -> dict[str, int]:
    text = f"{story['headline']} {story['summary']}".lower()
    words = len(story["headline"].split())
    has_num = bool(re.search(r"\d", text))
    return {
        "visual_potential": 80 if has_num else (
            65 if story["sector_or_theme"] == "Policy & Macro" else 50),
        "simplicity": 85 if words <= 10 else (70 if words <= 14 else 50),
        "curiosity": min(50 + 12 * sum(1 for k in _CURIOSITY if k in text), 90),
        "retail_relevance": 85 if story["sector_or_theme"] in _RETAIL_THEMES else 60,
        "save_share_value": 80 if has_num else 60,
        "compliance_safety": story.get("fact_confidence", 0),
        "five_slide_fit": 80 if len(story["summary"].split()) >= 15 else 55,
    }


def run(job_id: str) -> dict:
    fc = state.load_artifact(job_id, "fact_check") or {}
    stories = fc.get("verified_stories", [])

    ranked = []
    for s in stories:
        d = _dims(s)
        ranked.append((round(sum(d.values()) / len(d)), d, s))
    ranked.sort(key=lambda r: r[0], reverse=True)

    if not ranked:
        payload = {
            "selected_story": {}, "why_selected": "", "reel_angle": "",
            "save_reason": "", "share_reason": "", "score": 0,
            "status": "no_verified_story",
            "note": "No verified story available — run blocked; nothing fabricated.",
            "generated_at": config.now_ist().isoformat(timespec="seconds"),
        }
        state.save_artifact(job_id, "story_selector", payload)
        return payload

    score, dims, story = ranked[0]
    payload = {
        "selected_story": story,
        "why_selected": (f"Highest composite ({score}/100) across visual potential "
                         f"({dims['visual_potential']}), simplicity ({dims['simplicity']}), "
                         f"curiosity ({dims['curiosity']}), retail relevance "
                         f"({dims['retail_relevance']}) and compliance safety "
                         f"({dims['compliance_safety']})."),
        "reel_angle": (f"Explain '{story['headline']}' in 5 clean slides: hook -> "
                       "what happened -> why -> why it matters -> takeaway."),
        "save_reason": "One clear market lesson a viewer can revisit before their next decision.",
        "share_reason": ("Simple enough to send to a friend who asks 'what "
                         "happened in the market today?'"),
        "score": score,
        "dimension_scores": dims,
        "runner_ups": [{"story_id": s["story_id"], "headline": s["headline"],
                        "score": sc} for sc, _, s in ranked[1:4]],
        "status": "selected",
        "generated_at": config.now_ist().isoformat(timespec="seconds"),
    }
    state.save_artifact(job_id, "story_selector", payload)
    return payload
