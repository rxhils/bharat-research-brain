"""Step — Higgsfield Creative Director.

Sets the reel's overall visual identity BEFORE any scene is generated: proposes
3 premium creative directions matched to the story/angle/mood and selects one.
Deterministic (keyword-routed like the template selector); the conductor may
refine wording at run time but never the compliance rules.

Hard rules baked into every direction: no cartoon/meme style, no cheap stock
footage, no bull/bear mascots, no fake logos/numbers, no buy/sell arrows, no
clutter — and generous negative space for subtitles/overlays.
"""
from __future__ import annotations

import re

from . import state

AVOID = ["cartoon style", "meme style", "cheap stock footage", "bull/bear mascots",
         "fake company logos", "fake numbers", "buy/sell arrows", "clutter",
         "readable text baked into video"]

DIRECTIONS: dict[str, dict] = {
    "dark_market_shock": {
        "name": "Dark Market Shock",
        "style": "dark financial newsroom, cinematic market dashboard walls",
        "mood": "urgent but controlled — serious, not fearmongering",
        "color_palette": ["#05070A", "#EF4444", "#22D3EE", "#E6EDF3"],
        "motion_language": "fast push-ins, red data-glow sweeps, hard cinematic reveals",
        "visual_motifs": ["falling data wall", "dimmed trading floor", "red glow panels"],
        "why_it_fits": "Market falls, volatility, panic days.",
    },
    "green_market_pulse": {
        "name": "Green Market Pulse",
        "style": "dark navy premium dashboard, green glowing cards, upward energy",
        "mood": "confident, optimistic, premium",
        "color_palette": ["#0A1220", "#27C281", "#22D3EE", "#E6EDF3"],
        "motion_language": "rising camera glides, green glow pulses, upward parallax",
        "visual_motifs": ["ascending data columns", "glowing green cards", "light sweep"],
        "why_it_fits": "Rallies, recoveries, positive sector moves.",
    },
    "policy_impact_brief": {
        "name": "Policy Impact Brief",
        "style": "modern institutional finance newsroom, clean blue/white panels",
        "mood": "authoritative, calm, institutional",
        "color_palette": ["#0B1220", "#38BDF8", "#F8FAFC", "#94A3B8"],
        "motion_language": "measured camera moves, document/data-wave reveals, panel wipes",
        "visual_motifs": ["policy document visual", "institutional pillars", "data waves"],
        "why_it_fits": "RBI / SEBI / government / budget / regulation stories.",
    },
    "sector_heatmap_motion": {
        "name": "Sector Heatmap Motion",
        "style": "animated sector tiles, heatmap panels, premium data wall",
        "mood": "analytical, dynamic, precise",
        "color_palette": ["#05070A", "#F59E0B", "#27C281", "#EF4444"],
        "motion_language": "tiles shifting/settling, heat gradients breathing, camera drift over data wall",
        "visual_motifs": ["sector tile grid", "heatmap panels", "moving chips"],
        "why_it_fits": "Banking / IT / energy / defence sector-driven days.",
    },
    "what_investors_missed": {
        "name": "What Investors Missed",
        "style": "dark investigative newsroom, layered data reveals, premium mystery",
        "mood": "curious, intelligent, reveal-driven",
        "color_palette": ["#05070A", "#22D3EE", "#8B5CF6", "#E6EDF3"],
        "motion_language": "slow zoom into data layers, spotlight reveals, focus pulls",
        "visual_motifs": ["hidden layer reveal", "spotlight on data", "depth-of-field shift"],
        "why_it_fits": "Hidden-reason explainers, under-the-surface stories.",
    },
}

_ROUTES = [
    ("policy_impact_brief", r"\b(rbi|sebi|budget|policy|tax|regulation|repo|government)\b"),
    ("sector_heatmap_motion", r"\b(sector|banking|bank nifty|nifty it|pharma|auto|fmcg|metal|realty|energy|defence)\b"),
    ("what_investors_missed", r"\b(missed|hidden|misunderstood|under the surface|overlooked)\b"),
    ("dark_market_shock", r"\b(fall|falls|fell|slide|crash|drop|drops|decline|losing|sell-?off|red)\b"),
    ("green_market_pulse", r"\b(rally|rallies|rebound|bounce|gain|gains|jump|jumps|surge|reclaim|snap)\b"),
]


def _blob(story: dict, angle: dict | None, hooks: dict | None) -> str:
    return " ".join(str(x) for x in [
        story.get("headline", ""), story.get("what_happened", ""),
        (angle or {}).get("selected_angle", ""), (angle or {}).get("angle_type", ""),
        (hooks or {}).get("selected_hook", ""),
    ]).lower()


def run(date: str, *, story: dict, angle: dict | None = None,
        hooks: dict | None = None) -> dict:
    blob = _blob(story, angle, hooks)
    scored = []
    for key, pat in _ROUTES:
        hits = len(re.findall(pat, blob))
        scored.append((hits, key))
    scored.sort(reverse=True)
    ranked = [k for _, k in scored]
    top3 = ranked[:3]
    selected_key = top3[0]

    def _card(key: str) -> dict:
        d = dict(DIRECTIONS[key])
        d["avoid"] = AVOID
        return d

    payload = {
        "date": date,
        "creative_directions": [_card(k) for k in top3],
        "selected_direction": {**_card(selected_key), "key": selected_key},
        "selection_reason": f"Best keyword-fit for the story ({selected_key}).",
    }
    state.save_artifact(date, "creative_direction", payload)
    return payload
