"""Agent — Popup Planner (Maven Reels Newsroom). Local, free.

Chunk 3: designs the popup/data cards (the cause->effect explanation beats) with
strict art direction — one phrase, 3-7 words, centered, one highlighted word,
one underline, no clutter, no paragraph, no fake numbers. Reads format_director +
reel_variants (winner) + script_saveable. Writes 41_popup_plan.json.
"""
from __future__ import annotations

from . import state

# format → the cause->effect popup label
_POPUP_LABEL = {
    "hidden_mechanism": "INDEX vs SECTOR",
    "one_sector": "SECTOR → INDEX",
    "policy_signal": "POLICY → SECTOR",
    "retail_mistake": "MISTAKE vs CORRECT",
    "market_myth": "HEADLINE vs REALITY",
    "risk_explainer": "HOW THE TRAP WORKS",
}

CARD_RULES = ["one phrase only", "3-7 words", "centered", "strong hierarchy",
              "one highlighted word", "one underline", "no clutter", "no paragraph",
              "no generic caption", "no fake numbers / tickers / logos"]


def _winner(date: str) -> dict:
    rv = _opt(date, "reel_variants") or {}
    for v in rv.get("variants", []):
        if v.get("variant") == rv.get("chosen_variant"):
            return v
    return {}


def _short(text: str, n: int) -> str:
    return " ".join((text or "").split()[:n]).upper()


def run(date: str) -> dict:
    fd = _opt(date, "format_director") or {}
    sc = _opt(date, "script_saveable") or {}
    fid = fd.get("format", "hidden_mechanism")
    winner = _winner(date)

    label = _POPUP_LABEL.get(fid, "INDEX vs SECTOR")
    lesson = sc.get("saveable_lesson", "")

    cards = []
    # hero hook card
    hook = (sc.get("lines", {}) or {}).get("hook", "")
    cards.append({"scene_role": "hero_hook", "type": "Hero Hook Card",
                  "text": _short(hook, 6), "highlight_word": _short(hook, 6).split()[-1] if hook else "",
                  "underline": True})
    # mechanism / cause->effect popup
    cards.append({"scene_role": "mechanism", "type": "Cause → Effect Card",
                  "text": label, "highlight_word": label.split()[-1],
                  "underline": True})
    # takeaway / lesson card
    cards.append({"scene_role": "lesson", "type": "Takeaway Card",
                  "text": _short(lesson, 7), "highlight_word": _short(lesson, 7).split()[-1] if lesson else "",
                  "underline": True})
    # maven CTA
    cards.append({"scene_role": "cta", "type": "Maven CTA Card",
                  "text": "UNDERSTAND THE MARKET WITH MAVEN", "highlight_word": "MAVEN",
                  "underline": False})

    payload = {
        "date": date, "format": fid, "popup_label": label,
        "card_rules": CARD_RULES,
        "cards": cards,
        "count": len(cards),
        "note": "Art-direction spec for the designed cards; the Production Prompts "
                "agent renders these via nano_banana_pro (exact text only).",
    }
    state.save_artifact(date, "popup_plan", payload)
    return payload


def _opt(date: str, key: str):
    try:
        return state.load_artifact(date, key)
    except Exception:
        return None
