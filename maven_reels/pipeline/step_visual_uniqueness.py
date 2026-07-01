"""Step — Visual Uniqueness Check.

Ensures a new reel LOOKS different from the last 5 reels even when it reuses the
asset library. Compares template, motion variation, accent colour, background
asset combination, scene order and scene count. Gate: score >= 85. On failure the
orchestrator rotates the motion variation and re-storyboards before review.
Output: 10_visual_uniqueness.json.
"""
from __future__ import annotations

from . import run_history, state

GATE = 85

# penalty per matched dimension vs the most-similar recent reel
PENALTIES = {
    "template": 15, "variation": 20, "accent": 10,
    "assets": 15, "scene_order": 15, "scene_count": 5,
}


def _signature(template: dict | None, variation: dict | None,
               storyboard: dict | None, picker: dict | None) -> dict:
    scenes = (storyboard or {}).get("scenes", [])
    return {
        "template": (template or {}).get("selected_template"),
        "variation": (variation or {}).get("variation_id"),
        "accent": (variation or {}).get("accent_color"),
        "assets": tuple(sorted(a.get("asset_id", "") for a in
                               (picker or {}).get("selected_assets", []))),
        "scene_order": tuple(s.get("kind") for s in scenes),
        "scene_count": len(scenes),
    }


def _family(run_key: str) -> str:
    """Version family: reel-2026-06-30-v2 and 2026-06-30 are the SAME reel."""
    import re
    return re.sub(r"-v\d+$", "", run_key).removeprefix("reel-")


def run(run_key: str, *, template: dict | None, variation: dict | None,
        storyboard: dict | None, asset_picker: dict | None) -> dict:
    mine = _signature(template, variation, storyboard, asset_picker)
    # versions of the SAME reel are expected to share story/template — uniqueness
    # measures sameness ACROSS different reels, so exclude the version family
    recents = [r for r in run_history.recent_runs(exclude=run_key, limit=8)
               if _family(r["run_key"]) != _family(run_key)][:5]

    worst_score, worst_key, worst_matches = 100, None, []
    for r in recents:
        theirs = _signature(r["template"], r["variation"], r["storyboard"],
                            r["asset_picker"])
        matches = [k for k in PENALTIES if mine[k] and mine[k] == theirs[k]]
        score = 100 - sum(PENALTIES[k] for k in matches)
        if score < worst_score:
            worst_score, worst_key, worst_matches = score, r["run_key"], matches

    payload = {
        "run_key": run_key,
        "visual_uniqueness_score": worst_score,
        "gate": GATE,
        "passed": worst_score >= GATE,
        "signature": {k: list(v) if isinstance(v, tuple) else v for k, v in mine.items()},
        "reused_assets": [a.get("asset_id") for a in
                          (asset_picker or {}).get("selected_assets", [])],
        "new_variations": [mine["variation"]] if mine["variation"] else [],
        "too_similar_to": [worst_key] if worst_key and worst_score < GATE else [],
        "matched_dimensions": worst_matches,
        "note": ("Asset reuse is fine for cost; sameness of template+variation+"
                 "composition is what this gate blocks."),
    }
    state.save_artifact(run_key, "visual_uniqueness", payload)
    return payload
