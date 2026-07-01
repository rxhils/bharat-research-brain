"""Step 6 (upgraded) — Motion Storyboard.

Replaces the 5-7 static Ken-Burns scenes with 8-12 fast MICRO-scenes, each mapped
to an animated scene *kind* the Motion Graphics Engine (Remotion) knows how to
render: hook / stat / chips / reason / chart / outro. Targets a 15-20s reel with
a visual change every ~1-2s and the hook on frame 0.

Deterministic: derives scene content from the chosen story + edited script + hook.
Output artifact: 07_motion_storyboard.json.
"""
from __future__ import annotations

import re

from . import state


def _num(key_numbers: list[str]) -> tuple[str, float, str, str]:
    """Pull a headline stat: (label, value, suffix, sub) from key numbers."""
    for kn in key_numbers or []:
        m = re.search(r"(-?\d+(?:\.\d+)?)\s*%", kn)
        if m:
            label = re.split(r"[:\-]", kn)[0].strip()[:16].upper() or "INDEX"
            sub = "3-year low" if "low" in kn.lower() else ""
            return label, float(m.group(1)), "%", sub
    return "NIFTY", -0.3, "%", ""


def run(date: str, *, story: dict, hooks: dict, script_edited: dict,
        viral_fit: dict) -> dict:
    hook = hooks["chosen"]["text"]
    on_hook = " ".join(hook.replace("—", "").split()[:7])
    sectors = (story.get("affected_sectors") or ["Banks", "IT", "Energy"])[:4]
    sectors = [re.sub(r"\s*\(.*\)", "", s).split("/")[0].strip() for s in sectors]
    label, value, suffix, sub = _num(story.get("key_numbers", []))
    why = " ".join(str(story.get("why_it_matters", "")).split()[:9]) or "One sector moved the whole market"
    take = " ".join(str(story.get("investor_takeaway", "")).split()[:9]) or "Watch the sectors, not just the index"

    # 9 micro-scenes, fast pacing, total ~18s
    scenes = [
        {"kind": "hook", "duration": 1.4, "title": on_hook, "on_screen": on_hook,
         "visual": "Hook slams in over dark market grid", "motion": "scale-pop + underline wipe",
         "transition_out": "flash", "sfx": "impact", "asset": "asset_bg_dark"},
        {"kind": "stat", "duration": 2.6, "label": label, "value": value, "suffix": suffix, "sub": sub,
         "on_screen": f"{label} {value}{suffix}", "visual": "Index stat card slides up + number counter",
         "motion": "slide-up + count-up", "transition_out": "slide", "sfx": "tick", "asset": "asset_bg_dark"},
        {"kind": "chips", "duration": 2.0, "chips": sectors, "on_screen": " / ".join(sectors),
         "visual": "Sector chips stagger in", "motion": "stagger-pop", "transition_out": "wipe",
         "sfx": "tick", "asset": "asset_bg_panel"},
        {"kind": "reason", "duration": 3.0, "text": why, "on_screen": why,
         "visual": "Key reason as kinetic text card", "motion": "word-by-word rise",
         "transition_out": "fade", "sfx": "", "asset": "asset_bg_dark"},
        {"kind": "chart", "duration": 2.6, "points": [8, 7.2, 7.4, 6, 5.2, 3.4, 2.7, 2.4],
         "on_screen": "", "visual": "Mini index line draws down", "motion": "line-draw + dot",
         "transition_out": "flash", "sfx": "whoosh", "asset": "asset_bg_dark"},
        {"kind": "reason", "duration": 2.4, "text": take, "on_screen": take,
         "visual": "Takeaway as kinetic text", "motion": "word-by-word rise",
         "transition_out": "fade", "sfx": "", "asset": "asset_bg_panel"},
        {"kind": "outro", "duration": 2.4, "text": "Understand the Indian market with Maven",
         "on_screen": "Maven · trymaven.in", "visual": "Maven end card", "motion": "scale-in",
         "transition_out": "", "sfx": "", "asset": "asset_bg_end"},
    ]
    # assign start times
    t = 0.0
    for i, s in enumerate(scenes, start=1):
        s["scene"] = i
        s["start"] = round(t, 2)
        s["end"] = round(t + s["duration"], 2)
        t += s["duration"]

    payload = {"date": date, "total_duration": round(t, 1), "scene_count": len(scenes),
               "fps": 30, "scenes": scenes}
    state.save_artifact(date, "storyboard", payload)
    return payload
