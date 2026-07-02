"""Step — Duplicate Topic Check.

Before the Viral Fit Gate picks a story, compare research candidates against the
last 10 reel runs. A story that closely matches a recently-used topic is
penalized (unless it is clearly the biggest event of the day — i.e. it still wins
after the penalty). Output: 02_duplicate_check.json.
"""
from __future__ import annotations

import re

from . import run_history, state

_STOP = {"the", "a", "an", "and", "of", "in", "on", "to", "for", "as", "at",
         "by", "with", "after", "amid", "over", "today", "market", "markets",
         "stock", "stocks", "india", "indian"}


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", str(text).lower())
            if w not in _STOP and len(w) > 2}


def _similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


def _was_published(run_dir: str) -> bool:
    """Only PUBLISHED reels count as 'used' topics — unpublished drafts and
    test iterations of the same day never penalize their own story."""
    import json
    from pathlib import Path
    d = Path(run_dir)
    for name in ("_final_output.json", "17_publish.json", "20_publish.json"):
        p = d / name
        if p.exists():
            try:
                j = json.loads(p.read_text(encoding="utf-8"))
                if j.get("status") == "published" or j.get("instagram_post_url") \
                        or j.get("permalink"):
                    return True
            except Exception:
                continue
    return False


def run(run_key: str, research: dict) -> dict:
    recents = [r for r in run_history.recent_runs(exclude=run_key, limit=10)
               if _was_published(r["dir"])]
    recent_topics = [run_history.chosen_headline(r["viral_fit"]) for r in recents]
    recent_topics = [t for t in recent_topics if t]

    penalized, best_risk = [], 0.0
    for story in research.get("top_3_stories") or research.get("stories") or []:
        head = str(story.get("headline", ""))
        worst = max((_similarity(head, t) for t in recent_topics), default=0.0)
        best_risk = max(best_risk, worst)
        if worst >= 0.5:
            penalized.append({"headline": head, "similarity": round(worst, 2),
                              "matched_recent": next(t for t in recent_topics
                                                     if _similarity(head, t) == worst)})

    risk = "high" if best_risk >= 0.7 else "medium" if best_risk >= 0.5 else "low"
    payload = {
        "run_key": run_key,
        "recent_reel_topics": recent_topics,
        "duplicate_risk": risk,
        "penalized_stories": penalized,
        "selected_story_is_duplicate": False,   # viral_fit fills the final answer
        "reason": (f"{len(penalized)} candidate(s) overlap recent reels; they are "
                   "penalized in the Viral Fit Gate unless clearly the day's biggest event."
                   if penalized else "No overlap with the last 10 reels."),
    }
    state.save_artifact(run_key, "duplicate_check", payload)
    return payload
