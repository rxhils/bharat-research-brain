"""Agent — Scriptroom (saveable, Maven Reels Newsroom). Local, free.

Chunk 3: a Reel must leave the viewer with a simple MENTAL MODEL, not just recap
the news. Structure: Hook → Fact → Mechanism → Lesson → Maven CTA. Every script
must carry exactly one of the 7 canonical saveable lessons; if the story maps to
none, the Reel is blocked (no saveable lesson, no Reel). Reads format_director +
story_format + hooks_format. Writes 39_script_saveable.json.
Educational only — sourced fact, no advice, ends on a teaching anchor.
"""
from __future__ import annotations

from . import state

# The 7 canonical saveable lessons (mental models).
SAVEABLE_LESSONS = {
    "index_not_market": "The index isn't the whole market.",
    "sector_weight": "Sector weight can move the whole index.",
    "rates_banks_first": "Rate moves hit banks first.",
    "policy_by_sector": "Policy affects different sectors differently.",
    "earnings_expectations": "Earnings change expectations, not just prices.",
    "flows_sentiment": "FII/DII flows can move sentiment.",
    "hidden_risk": "Risk comes from what you don't see.",
}

# format → the mental model it most naturally teaches
_FORMAT_LESSON = {
    "hidden_mechanism": "index_not_market",
    "one_sector": "sector_weight",
    "policy_signal": "policy_by_sector",
    "retail_mistake": "earnings_expectations",
    "market_myth": "index_not_market",
    "risk_explainer": "hidden_risk",
}

# keyword → lesson override when the story clearly points elsewhere
_LESSON_SIGNALS = {
    "rates_banks_first": ["rate", "repo", "rbi", "bank", "banks", "banking"],
    "flows_sentiment": ["fii", "dii", "flows", "foreign", "inflow", "outflow"],
    "sector_weight": ["sector", "heavyweight", "weight", "index weight"],
    "policy_by_sector": ["policy", "sebi", "budget", "tax", "regulation"],
    "hidden_risk": ["risk", "scam", "trap", "leverage", "default", "fraud"],
    "earnings_expectations": ["earnings", "results", "profit", "guidance", "q1", "q2"],
}


def _pick_lesson(fid: str, blob: str) -> str | None:
    low = blob.lower()
    for lesson, kws in _LESSON_SIGNALS.items():
        if any(kw in low for kw in kws):
            return lesson
    return _FORMAT_LESSON.get(fid)


def run(date: str) -> dict:
    fd = _opt(date, "format_director") or {}
    sf = _opt(date, "story_format") or {}
    hk = _opt(date, "hooks_format") or {}
    fid = fd.get("format") or sf.get("selected_format", "hidden_mechanism")
    story = sf.get("selected_story", {})
    headline = story.get("headline", "")
    sector = (story.get("sector") or "the market").split("/")[0].strip()
    source = story.get("source", "")
    hook = hk.get("selected_hook") or fd.get("first_frame_promise", "")

    blob = " ".join(str(story.get(k, "")) for k in ("headline", "summary", "sector"))
    lesson_key = _pick_lesson(fid, blob)
    lesson = SAVEABLE_LESSONS.get(lesson_key or "", "")

    fact = headline or f"{sector} led the market today."
    mechanism = fd.get("final_takeaway") or "The move has a reason underneath the number."
    cta = "Follow Maven to understand what moves underneath."

    lines = {
        "hook": hook,
        "fact": fact + (f" (Source: {source})" if source else ""),
        "mechanism": mechanism,
        "lesson": lesson,
        "cta": cta,
    }
    narration = " ".join([hook, fact + ".", mechanism, lesson, cta]).replace("..", ".")
    words = len(narration.split())

    blocked = not lesson_key
    payload = {
        "date": date, "format": fid,
        "structure": ["hook", "fact", "mechanism", "lesson", "cta"],
        "lines": lines,
        "narration": narration,
        "word_count": words,
        "saveable_lesson_key": lesson_key,
        "saveable_lesson": lesson,
        "has_saveable_lesson": bool(lesson_key),
        "script_blocked": blocked,
        "blocked_reason": ("Story maps to none of the 7 saveable lessons — no saveable "
                           "lesson, no Reel.") if blocked else "",
        "source_cited": bool(source),
        "compliance_note": "Educational; sourced fact; ends on a teaching anchor. No advice.",
    }
    state.save_artifact(date, "script_saveable", payload)
    return payload


def _opt(date: str, key: str):
    try:
        return state.load_artifact(date, key)
    except Exception:
        return None
