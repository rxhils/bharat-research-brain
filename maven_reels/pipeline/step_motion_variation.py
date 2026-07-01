"""Step — Motion Variation Engine.

Makes each daily reel look unique WITHOUT any new Higgsfield generation, by
varying accent colour, hook/transition/chart/subtitle/card motion. Picks the
template's preferred preset by default; otherwise rotates deterministically by
date (reproducible — no RNG, so reruns are stable).
"""
from __future__ import annotations

from . import config, state

PRESETS = config.MOTION_VARIATIONS
ORDER = list(PRESETS.keys())


def _rotate(date: str) -> str:
    h = sum(ord(c) for c in date)
    return ORDER[h % len(ORDER)]


def run(date: str, *, template: dict | None = None, force_id: str | None = None,
        avoid: list[str] | None = None) -> dict:
    preferred = (template or {}).get("motion_style")
    variation_id = (force_id if force_id in PRESETS
                    else preferred if preferred in PRESETS else _rotate(date))
    # uniqueness retry: rotate past any preset we must avoid
    for bad in (avoid or []):
        if variation_id == bad:
            variation_id = ORDER[(ORDER.index(variation_id) + 1) % len(ORDER)]
    p = PRESETS[variation_id]
    payload = {
        "date": date, "variation_id": variation_id,
        "accent_color": p["accent"], "hook_animation": p["hook_animation"],
        "transition_style": p["transition_style"], "chart_style": p["chart_style"],
        "subtitle_style": p["subtitle_style"], "card_style": p["card_style"],
        "reason": (f"Template preferred '{variation_id}'." if preferred in PRESETS
                   else f"Rotated to '{variation_id}' by date for freshness."),
        "all_variations": ORDER,
    }
    state.save_artifact(date, "motion_variation", payload)
    return payload
