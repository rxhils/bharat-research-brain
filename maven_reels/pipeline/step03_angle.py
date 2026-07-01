"""Step 3 (upgraded) — Angle Studio.

Generates 8-12 scroll-stopping angles across angle types (curiosity, shock,
contrarian, myth-busting, simple-explainer, money-flow, hidden-reason,
what-people-missed, why-this-matters, market-under-the-surface), scores each,
and picks the best. Deterministic templates seed them; the conductor may refine.
"""
from __future__ import annotations

from . import state


def _candidates(story: dict) -> list[dict]:
    sectors = story.get("affected_sectors") or ["the market"]
    sector = sectors[0].split("/")[0].strip()
    s = sector.lower()
    nums = story.get("key_numbers") or []
    big = next((n for n in nums if "%" in n or "crore" in n.lower()), None)
    cands = [
        {"type": "curiosity", "angle": f"The market moved today, but the real story was {s}."},
        {"type": "hidden_reason", "angle": f"The real reason {s} moved today."},
        {"type": "what_people_missed", "angle": f"Everyone watched the index. Few watched {s}."},
        {"type": "why_this_matters", "angle": f"Why {s} changed the market mood today."},
        {"type": "market_under_surface", "angle": "The market looked calm on the surface. Underneath, it wasn't."},
        {"type": "contrarian", "angle": f"The market didn't move because of one stock. It moved because of {s}."},
        {"type": "money_flow", "angle": f"Where the money actually went today — and why {s} felt it."},
        {"type": "simple_explainer", "angle": f"Today's market move, explained through {s}, in 15 seconds."},
        {"type": "myth_busting", "angle": "You think the index tells the story. Today it didn't."},
    ]
    if big:
        cands.insert(0, {"type": "shock", "angle": f"{big} — and it came down to one sector."})
    return cands


def _score(angle: str) -> int:
    a = angle.lower()
    score = 58
    if any(w in a for w in ("real story", "real reason", "few watched", "underneath",
                            "actually", "didn't", "missed")): score += 16
    if "why" in a: score += 8
    if any(c.isdigit() for c in a) or "%" in a: score += 8
    if len(angle) <= 62: score += 6
    return min(100, score)


def run(date: str, viral_fit: dict) -> dict:
    story = viral_fit["chosen"]["story"]
    cands = _candidates(story)
    for c in cands:
        c["angle_score"] = _score(c["angle"])
    cands.sort(key=lambda c: c["angle_score"], reverse=True)
    chosen = cands[0]
    payload = {
        "date": date, "story_headline": story.get("headline"),
        "candidates": cands, "count": len(cands),
        "chosen": chosen,
        "selected_angle": chosen["angle"], "angle_type": chosen["type"],
        "angle_score": chosen["angle_score"],
        "why_selected": (f"Highest scroll-stop ({chosen['angle_score']}) — frames the "
                         "event as a why/hidden-reason, not a recap, and fits 15-20s."),
        "backup_angles": [c["angle"] for c in cands[1:5]],
    }
    state.save_artifact(date, "angle", payload)
    return payload
