"""Agent — Higgsfield Production Prompts (full-stack). Local, free.

Production-ready prompt per blueprint scene: designed-card prompts (exact text,
premium typography, underline/highlight, NO extra words) for text-fidelity
scenes; realistic-footage prompts (via Location Scout) for b-roll. Writes
33_production_prompts.json.
"""
from __future__ import annotations

from . import state
from .step_higgsfield_prompt_builder import NO_TEXT_POSITIVE, REALISTIC_NEGATIVE, _realistic_prompt

CARD_NEGATIVE = ("plain subtitle overlay, ugly font, thick black outline, default caption, "
                 "random gibberish, unreadable text, misspelled words, extra words, fake "
                 "numbers, fake ticker symbols, fake logo, cluttered dashboard, cheap AI "
                 "look, meme style, cartoon finance, bad typography, distorted letters, watermark")


def _card_prompt(s: dict, scout: dict) -> str:
    text = s.get("exact_text", "")
    words = text.split()
    hi = " ".join(words[-2:]) if len(words) > 2 else text
    st = scout.get("shot_style", {})
    return (f"Design a premium vertical 9:16 finance-Reel {s['scene_type']} card for Maven, "
            f"an Indian stock-market research brand.\n"
            f"The card must contain EXACTLY this centered text and nothing else: \"{text}\"\n"
            f"Typography: {s.get('typography_direction', 'bold geometric sans, centered, premium')}. "
            f"Highlight the phrase \"{hi}\" with a teal/green accent and a clean underline.\n"
            f"Background: clean, softly-lit abstract finance space matching "
            f"{s.get('footage_world', 'finance_newsroom')} — {st.get('color_palette', 'navy + teal')}, "
            f"{st.get('lighting', 'soft premium')} lighting, generous negative space.\n"
            f"Design rules: visually appealing, modern startup-finance aesthetic, not a basic "
            f"subtitle, no thick black outline, no other readable words, no fake numbers, no "
            f"tickers, no logos, no clutter.\n"
            f"Output: one designed still card, vertical 9:16, high resolution.")


def run(date: str, *, blueprint: dict, routing: dict) -> dict:
    scout = _opt(date, "location_scout") or {}
    routes = {r["scene_id"]: r for r in routing.get("routes", [])}
    prompts = []
    for i, s in enumerate(blueprint.get("scenes", [])):
        r = routes.get(s["scene_id"], {})
        is_card = bool(s.get("requires_text_fidelity"))
        prompts.append({
            "scene_id": s["scene_id"], "scene_type": s["scene_type"],
            "purpose": s["purpose"], "duration": s["duration"],
            "model_or_tool": r.get("selected_model_or_tool"),
            "fallback": r.get("fallback"),
            "exact_text": s.get("exact_text", ""),
            "prompt": (_card_prompt(s, scout) if is_card
                       else _realistic_prompt(
                           {"purpose": s["purpose"], "motion": "subtle real camera motion",
                            "camera": s.get("camera_motion", "")}, scout, i)),
            "negative_prompt": CARD_NEGATIVE if is_card else REALISTIC_NEGATIVE,
            "animate_with": r.get("fallback") if is_card else None,
            "animate_note": ("animate the finished card via i2v WITHOUT changing the text, "
                             "subtle premium motion only" if is_card else ""),
            "voiceover_line": s.get("voiceover_line", ""),
            "quality_requirements": (["exact text only", "no gibberish", "centered",
                                      "premium typography", "underline visible"]
                                     if is_card else ["photoreal", "no readable text"]),
            "requires_user_confirmation": True,
        })
    payload = {"date": date, "prompts": prompts, "count": len(prompts),
               "no_text_positive": NO_TEXT_POSITIVE}
    state.save_artifact(date, "production_prompts", payload)
    return payload


def _opt(date: str, key: str):
    try:
        return state.load_artifact(date, key)
    except Exception:
        return None
