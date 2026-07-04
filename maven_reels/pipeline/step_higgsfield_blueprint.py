"""Agent — Higgsfield Blueprint (Maven Reels Newsroom, full-stack production).

The single production blueprint for a Reel where HIGGSFIELD creates every
visual: realistic footage scenes AND designed text/title/popup/CTA cards.
Text-first structure (no plain-subtitle reel):

  1 hero_text      — designed centered hook card (exact text)
  2 realistic_broll— footage, voice carries the story
  3 popup_card     — designed info card (what happened)
  4 realistic_broll— footage (why it happened)
  5 key_takeaway   — designed centered takeaway card
  6 cta            — Maven branded end card

Text fidelity honesty: video models render garbled text (verified in a real
run), so every requires_text_fidelity scene is produced via the image model
(nano_banana_pro — 'good' text rendering in the capability matrix) and then
animated/held; the router enforces this. Local code never designs the text.
Reads the existing agents' artifacts; writes 31_higgsfield_blueprint.json.
"""
from __future__ import annotations

from . import config, state

# scene template: (scene_type, purpose, seconds, needs_exact_text)
_STRUCTURE = [
    ("hero_text", "hook", 2.5, True),
    ("realistic_broll", "context", 3.5, False),
    ("popup_card", "data", 3.0, True),
    ("realistic_broll", "reason", 3.5, False),
    ("key_takeaway", "impact", 3.0, True),
    ("cta", "cta", 2.5, True),
]


def _opt(date: str, key: str):
    try:
        return state.load_artifact(date, key)
    except Exception:
        return None


def _short(text: str, n: int = 7) -> str:
    words = str(text).strip().rstrip(".").split()
    return " ".join(words[:n]).upper()


def run(date: str) -> dict:
    story = ((_opt(date, "viral_fit") or {}).get("chosen") or {}).get("story") or {}
    hooks = _opt(date, "hooks") or {}
    script = _opt(date, "script_edited") or {}
    scout = _opt(date, "location_scout") or {}
    trend = _opt(date, "trendscout") or {}
    direction = (_opt(date, "creative_direction") or {}).get("selected_direction", {})

    world = scout.get("selected_footage_world", "finance_newsroom")
    segs = {s.get("label"): s.get("narration", "") for s in script.get("segments", [])}
    hook_text = _short(hooks.get("on_screen_hook") or hooks.get("selected_hook")
                       or segs.get("hook", "MARKET MOVED TODAY"))
    takeaway = _short(segs.get("understand") or segs.get("why")
                      or "UNDERSTAND WHY IT MOVED")
    popup = _short(segs.get("what") or story.get("headline", "WHAT HAPPENED"), 6)
    vo_for = {"hook": segs.get("hook", ""), "context": segs.get("what", ""),
              "data": segs.get("what", ""), "reason": segs.get("why", ""),
              "impact": segs.get("understand", ""), "cta": segs.get("cta", "")}
    text_for = {"hook": hook_text, "data": popup, "impact": takeaway,
                "cta": "UNDERSTAND THE MARKET WITH MAVEN"}

    scenes = []
    for i, (stype, purpose, dur, needs_text) in enumerate(_STRUCTURE, 1):
        scenes.append({
            "scene_id": f"shot_{i:02d}",
            "scene_type": stype,
            "duration": dur,
            "purpose": purpose,
            "voiceover_line": vo_for.get(purpose, ""),
            "exact_text": text_for.get(purpose, "") if needs_text else "",
            "popup_text": popup if stype == "popup_card" else "",
            "visual_concept": (f"designed {stype} card, centered premium typography"
                               if needs_text else
                               f"realistic {world} footage — {purpose}"),
            "footage_world": world,
            "camera_motion": scout.get("shot_style", {}).get("camera", "controlled glide"),
            "typography_direction": ("bold geometric sans, centered, teal highlight, "
                                     "clean underline on the key phrase, premium finance"
                                     if needs_text else ""),
            "animation_direction": ("center punch / underline draw" if needs_text
                                    else "real filmed motion"),
            "audio_need": "none (voiceover carries audio)",
            "requires_text_fidelity": needs_text,
        })

    payload = {
        "date": date,
        "target_duration": round(sum(s["duration"] for s in scenes), 1),
        "aspect_ratio": "9:16", "resolution": "1080x1920",
        "production_mode": "higgsfield_full_stack",
        "story": {"headline": story.get("headline"), "sources": story.get("sources")
                  or story.get("source_urls")},
        "script": script.get("narration", ""),
        "creative_style_package": direction.get("name", ""),
        "trend_structure": trend.get("recommended_reel_structure", ""),
        "scenes": scenes,
        "caption_plan": {"engine": "nano_banana_pro cards (no plain running subtitles)",
                         "note": "text lives in designed card scenes; no local text design"},
        "assembly_plan": {"preferred": "explainer_video (Higgsfield) if suitable",
                          "fallback": "local stitch/trim/mux ONLY (no text design)"},
    }
    state.save_artifact(date, "higgsfield_blueprint", payload)
    return payload
