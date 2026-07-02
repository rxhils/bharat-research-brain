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
    """Truncate to `limit` chars WITHOUT leaving a dangling mid-sentence
    fragment (the old `[:limit] + "…"` behavior read as broken/garbled when
    spoken by TTS — e.g. "The Sensex rose 443.97…"). Prefers cutting at the
    last complete sentence within the limit; falls back to a clean
    word-boundary cut ending in a period (TTS-friendly, unlike "…")."""
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    truncated = text[:limit]
    cut = max(truncated.rfind(". "), truncated.rfind("! "), truncated.rfind("? "))
    if cut >= limit * 0.4:  # a real sentence boundary, not too aggressive a cut
        return truncated[:cut + 1].strip()
    return truncated.rsplit(" ", 1)[0].rstrip(",;:") + "."


def run(date: str, story: dict, hooks: dict) -> dict:
    # Tight 15-20s reel: short, punchy lines (45-65 words total).
    hook = hooks["chosen"]["text"]
    what = _clean(story.get("what_happened", ""), 110)
    why = _clean(story.get("why_it_matters", ""), 130)
    take = _clean(story.get("investor_takeaway", ""), 100)

    segments = [
        {"label": "hook", "t0": 0.0, "seconds": 1.5, "narration": hook},
        {"label": "what", "t0": 1.5, "seconds": 4.5, "narration": what},
        {"label": "why", "t0": 6.0, "seconds": 5.5, "narration": why},
        {"label": "understand", "t0": 11.5, "seconds": 4.0,
         "narration": take or "Watch the sectors, not just the index."},
        {"label": "cta", "t0": 15.5, "seconds": 3.0,
         "narration": f"Understand the Indian market with {BRAND_NAME}. {BRAND_SITE}."},
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
