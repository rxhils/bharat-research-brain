"""Step 5 — Script Room.

Writes a timed 20-35s script from the chosen hook + story:
  0-2 hook / 2-8 what / 8-18 why / 18-28 understand / 28-33 CTA.
Deterministic draft; the conductor/LLM refines voice at real-run time. No advice.
"""
from __future__ import annotations

from . import compliance_util as _c
from . import schemas, state
from .config import BRAND_NAME, BRAND_SITE


def _clean(text: str, limit: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


def run(date: str, story: dict, hooks: dict) -> dict:
    hook = hooks["chosen"]["text"]
    what = _clean(story.get("what_happened", ""), 170)
    why = _clean(story.get("why_it_matters", ""), 200)
    take = _clean(story.get("investor_takeaway", ""), 170)

    segments = [
        {"label": "hook", "t0": 0, "seconds": 2, "narration": hook},
        {"label": "what", "t0": 2, "seconds": 6, "narration": what},
        {"label": "why", "t0": 8, "seconds": 10, "narration": why},
        {"label": "understand", "t0": 18, "seconds": 10,
         "narration": take or "Watching just the index isn't enough — the sector "
                             "moves tell you what's really happening."},
        {"label": "cta", "t0": 28, "seconds": 5,
         "narration": f"Understand the Indian market better with {BRAND_NAME}. {BRAND_SITE}."},
    ]
    total = sum(s["seconds"] for s in segments)
    payload = {
        "date": date,
        "segments": segments,
        "total_seconds": total,
        "narration": " ".join(s["narration"] for s in segments),
        "compliance": {"violations": _c.scan_payload([s["narration"] for s in segments])},
    }
    schemas.validate_script(payload)
    state.save_artifact(date, "script", payload)
    return payload
