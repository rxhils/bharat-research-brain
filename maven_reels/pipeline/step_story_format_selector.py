"""Agent — Story + Format Selector (Maven Reels Newsroom). Local, free.

Upgrades "pick the most Reel-able story" into "pick the story AND the viral
format it should become". Reads the chosen story (viral_fit / research) and maps
it to one of the six canonical formats, with an explicit reason it can go viral,
its save/share reasons, the first-frame promise, and a compliance-risk flag.
Writes 35_story_format.json.
"""
from __future__ import annotations

from . import format_taxonomy, state
from .step_viral_reference_bank import patterns_for

# advisory / risk words that raise the compliance flag on a story
_RISK_WORDS = ["buy", "sell", "target", "multibagger", "guaranteed", "sure shot",
               "tip", "double your", "penny stock"]


def _story_blob(date: str, story: dict | None) -> tuple[dict, str]:
    if story is None:
        vf = _opt(date, "viral_fit") or {}
        story = vf.get("chosen") or vf.get("selected_story") or {}
        if not story:
            res = _opt(date, "research") or {}
            cands = res.get("stories") or res.get("candidates") or []
            story = cands[0] if cands else {}
    blob = " ".join(str(story.get(k, "")) for k in
                    ("headline", "title", "summary", "sector", "why_it_matters", "angle"))
    return story, blob


def run(date: str, *, story: dict | None = None) -> dict:
    story, blob = _story_blob(date, story)
    scores = format_taxonomy.score_formats(blob)
    # Learning loop tie-breaker: nudge by empirical save/share performance, but
    # only among formats the story actually supports (score > 0) — relevance first.
    from .step_learning_loop import load_performance  # noqa: PLC0415
    fboost = load_performance().get("boosts", {}).get("format", {})
    weighted = {f: scores[f] * fboost.get(f, 1.0) for f in scores}
    fid = (max(weighted, key=lambda k: weighted[k])
           if any(v > 0 for v in scores.values()) else format_taxonomy.best_format(blob))
    fmt = format_taxonomy.get(fid)
    ref = patterns_for(fid)

    low = blob.lower()
    risk_hits = [w for w in _RISK_WORDS if w in low]
    compliance_risk = ("elevated" if risk_hits else
                       "watch" if fid == "risk_explainer" else "low")

    payload = {
        "date": date,
        "selected_story": {
            "headline": story.get("headline") or story.get("title", ""),
            "sector": story.get("sector", ""),
            "source": story.get("source") or story.get("url", ""),
            "summary": story.get("summary", ""),
        },
        "selected_format": fid,
        "selected_format_name": fmt["name"],
        "format_scores": scores,
        "why_this_format_can_go_viral": (
            f"{fmt['name']}: {fmt['when_to_use']} {ref.get('why_it_works', '')}"),
        "first_frame_promise": fmt["first_frame_promise"],
        "example_hook_direction": fmt["example_hook"],
        "save_reason": fmt["save_reason"],
        "share_reason": fmt["share_reason"],
        "teaching_anchor": fmt["teaching_anchor"],
        "compliance_risk": compliance_risk,
        "compliance_note": fmt["compliance_note"]
        + (f" Advisory-language words present ({', '.join(risk_hits)}) — must be reframed educationally."
           if risk_hits else ""),
    }
    state.save_artifact(date, "story_format", payload)
    return payload


def _opt(date: str, key: str):
    try:
        return state.load_artifact(date, key)
    except Exception:
        return None
