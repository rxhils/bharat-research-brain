"""Agent — Format Director (Maven Reels Newsroom). Local, free.

The missing creative brain: BEFORE hooks/scripts/prompts, it takes
story + selected format + reference patterns + template and locks the exact Reel
structure — first frame, hook style, text style, popup style, b-roll style,
retention pattern, final takeaway. Everything downstream builds to this.
Writes 36_format_director.json.
"""
from __future__ import annotations

from . import format_taxonomy, state
from .reel_template_library import template_for
from .step_viral_reference_bank import patterns_for


def run(date: str) -> dict:
    sf = _opt(date, "story_format") or {}
    fid = sf.get("selected_format", "hidden_mechanism")
    fmt = format_taxonomy.get(fid)
    ref = patterns_for(fid)
    tpl = template_for(fid)

    payload = {
        "date": date,
        "format": fid,
        "format_name": fmt["name"],
        "template_id": tpl.get("template_id"),
        "first_frame": ref.get("first_frame", fmt["first_frame_promise"]),
        "first_frame_promise": fmt["first_frame_promise"],
        "hook_style": ref.get("hook_pattern", "story-specific, contrarian"),
        "text_style": ref.get("text_style", "centered editorial title, one underlined key word"),
        "popup_style": ref.get("popup_style", "clean finance cards"),
        "broll_style": ref.get("broll_type", "realistic finance newsroom"),
        "voice_style": ref.get("voice_style", "calm, clear"),
        "retention_pattern": "a new visual/text beat every 1.8s; pattern interrupt on every scene",
        "camera_style": tpl.get("camera_style"),
        "color_style": tpl.get("color_style"),
        "audio_style": tpl.get("audio_style"),
        "final_takeaway": fmt["teaching_anchor"],
        "beats": tpl.get("beats", []),
        "model_routing_rules": tpl.get("model_routing_rules"),
        "save_reason": fmt["save_reason"],
        "share_reason": fmt["share_reason"],
        "compliance_note": fmt["compliance_note"],
        "avoid": ["fake tickers/numbers/logos", "abstract dashboards every scene",
                  "generic 'market update today' opener", "advice / buy-sell language"],
    }
    state.save_artifact(date, "format_director", payload)
    return payload


def _opt(date: str, key: str):
    try:
        return state.load_artifact(date, key)
    except Exception:
        return None
