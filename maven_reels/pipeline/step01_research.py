"""Step 1 — Market Sentinel (reel research gate).

The live web research is performed by a reel-tuned LLM agent (needs web access).
This module validates its JSON and persists it. Reel research favours stories
that are important AND emotional/simple/visually explainable.
"""
from __future__ import annotations

from . import schemas, state


def run(date: str, research: dict) -> dict:
    schemas.validate_research(research)
    meta = research.setdefault("_meta", {})
    meta["story_count"] = len(research["top_3_stories"])
    state.save_artifact(date, "research", research)
    return research
