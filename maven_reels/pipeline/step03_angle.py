"""Step 3 — Angle Studio.

Turns the chosen story into a scroll-stopping IDEA (not a news summary). Produces
several candidate angles, scores each for scroll-stop, picks the best. Deterministic
templates seed the candidates; the conductor/LLM may refine at real-run time.
"""
from __future__ import annotations

from . import state


def _candidates(story: dict) -> list[dict]:
    head = story.get("headline", "the market move")
    sectors = story.get("affected_sectors", []) or ["the market"]
    nums = story.get("key_numbers", []) or []
    sector = sectors[0]
    big = next((n for n in nums if "%" in n or "crore" in n.lower()), None)
    cands = [
        {"angle": f"The real reason {sector.lower()} moved today", "type": "explainer"},
        {"angle": f"Everyone saw the headline — few understood why {sector.lower()} really moved",
         "type": "curiosity"},
        {"angle": f"One thing behind today's move that most retail investors missed",
         "type": "insider"},
    ]
    if big:
        cands.insert(0, {"angle": f"Why {big} moved on one story today", "type": "data"})
    return cands


def _scroll_score(angle: str) -> int:
    a = angle.lower()
    score = 60
    if "why" in a: score += 12
    if "real reason" in a or "missed" in a or "few understood" in a: score += 14
    if any(c.isdigit() for c in a): score += 8
    if len(angle) <= 60: score += 6
    return min(100, score)


def run(date: str, viral_fit: dict) -> dict:
    story = viral_fit["chosen"]["story"]
    cands = _candidates(story)
    for c in cands:
        c["scroll_score"] = _scroll_score(c["angle"])
    cands.sort(key=lambda c: c["scroll_score"], reverse=True)
    payload = {
        "date": date,
        "story_headline": story.get("headline"),
        "candidates": cands,
        "chosen": cands[0],
        "rationale": (f"'{cands[0]['angle']}' scored highest for scroll-stop "
                      f"({cands[0]['scroll_score']}) — it frames the event as a "
                      "why, not a recap."),
    }
    state.save_artifact(date, "angle", payload)
    return payload
