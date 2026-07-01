"""Step 7 — Storyboard.

Turns the tightened script into 5-7 scenes, each with short on-screen text, a
duration, and a visual beat. Every scene = one screen the viewer reads fast.
"""
from __future__ import annotations

from . import schemas, state


def _onscreen(narration: str, label: str) -> str:
    words = narration.replace("…", "").strip().split()
    short = " ".join(words[:8])
    return short if short else label.title()


def run(date: str, script_edited: dict, story: dict) -> dict:
    scenes = []
    for i, seg in enumerate(script_edited["segments"], start=1):
        secs = seg["seconds"]
        # split long segments into 2 scenes so a visual changes ~every 3s
        parts = 2 if secs >= 8 else 1
        for p in range(parts):
            scenes.append({
                "scene": len(scenes) + 1,
                "from_segment": seg["label"],
                "seconds": round(secs / parts, 1),
                "on_screen": _onscreen(seg["narration"], seg["label"]),
                "visual_beat": _beat(seg["label"], story),
            })
    scenes = scenes[:7]
    payload = {"date": date, "scenes": scenes, "scene_count": len(scenes),
               "total_seconds": round(sum(s["seconds"] for s in scenes), 1)}
    schemas.validate_storyboard(payload)
    state.save_artifact(date, "storyboard", payload)
    return payload


def _beat(label: str, story: dict) -> str:
    sector = (story.get("affected_sectors") or ["market"])[0]
    return {
        "hook": "Full-bleed bold hook text on dark navy; one accent glow.",
        "what": f"Index/{sector} stat card with the day's numbers.",
        "why": "Single cause-and-effect diagram; one arrow, minimal.",
        "understand": "One-line insight on clean background; large type.",
        "cta": "Maven wordmark + trymaven.in on dark; calm.",
    }.get(label, "Clean data card.")
