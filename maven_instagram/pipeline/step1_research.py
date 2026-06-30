"""Step 1 — IndianMarketResearchAgent (validation + gating layer).

The live web research itself is performed by an LLM research agent (it needs web
access). This module is the deterministic contract around it: it validates the
agent's JSON against the schema, applies the importance/confidence thresholds,
and records how many post-worthy stories survived.

Usage:
    research = load_artifact(date, "research")   # produced by the research agent
    result = run(date, research)
"""
from __future__ import annotations

from . import schemas, state
from .config import MIN_CONFIDENCE_SCORE, MIN_IMPORTANCE_SCORE, TARGET_STORY_COUNT


def run(date: str, research: dict) -> dict:
    """Validate + gate the research payload; persist and return it."""
    schemas.validate_research(research)
    passing = schemas.passing_stories(research)

    count = len(passing)
    meta = research.setdefault("_meta", {})
    meta.update({
        "post_worthy_count": count,
        "thresholds": {
            "min_importance": MIN_IMPORTANCE_SCORE,
            "min_confidence": MIN_CONFIDENCE_SCORE,
        },
        "all_pass": count >= TARGET_STORY_COUNT,
    })
    if count < TARGET_STORY_COUNT:
        meta["shortfall_note"] = f"Only {count} post-worthy stories found today."

    # Keep only the passing stories, re-ranked, capped at the target count.
    research["top_3_stories"] = passing[:TARGET_STORY_COUNT]
    state.save_artifact(date, "research", research)
    return research
