"""Agent — Prompt Bible (Maven Reels Newsroom). Local, free.

One continuity document every generation step follows, so the crew works from a
single source of truth instead of scattered per-step prompts. It assembles the
story, Trendscout patterns, Creative Director, Location Scout footage world, hook,
script, shot plan, and the realistic Camera Router model choices into shots[],
each with model + prompt + negative + voiceover + text + continuity notes.
Writes prompt_bible.json.

Chunk 1 = scaffolding/assembly. It stamps the footage world + global negatives
onto each shot and carries the router's model choice; the deeper real-world-b-roll
prompt rewriting is the next chunk (Scene Generator improvements).
"""
from __future__ import annotations

from . import state

GLOBAL_NEGATIVE = (
    "no readable text, no fake text, no fake letters, no fake words, no fake numbers, "
    "no fake ticker symbols, no fake company names, no fake logos, no gibberish panels, "
    "no gibberish text, no stock tips, no buy or sell arrows, no trading-signal overlays, "
    "no cluttered AI dashboard, no floating fake panels, no cartoon bull, no cartoon bear, "
    "no meme style, no cheap AI look, no generic purple gradient finance background, "
    "no distorted faces, no warped hands, no morphing artifacts, no watermark. "
    "If screens are visible, keep them blurred / non-readable abstract data blocks only."
)


def _opt(date: str, key: str) -> dict | None:
    try:
        return state.load_artifact(date, key)
    except Exception:
        return None


def run(date: str) -> dict:
    story = (_opt(date, "viral_fit") or {}).get("chosen", {}).get("story") \
        or (_opt(date, "research") or {}).get("top_3_stories", [{}])[0] if _opt(date, "research") else {}
    trend = _opt(date, "trendscout") or {}
    brief = _opt(date, "creative_direction") or _opt(date, "creative_brief") or {}
    scout = _opt(date, "location_scout") or {}
    hooks = _opt(date, "hooks") or {}
    script = _opt(date, "script_edited") or {}
    shot_plan = _opt(date, "shot_plan") or {}
    prompts = _opt(date, "shot_prompts") or {}
    routing = _opt(date, "model_routing_plan") or {}

    prompt_by_shot = {p["shot_id"]: p for p in prompts.get("shot_prompts", [])}
    model_by_shot = {r["scene_id"]: r for r in routing.get("per_scene_model_plan", [])}
    vo_by_label = {seg.get("label"): seg.get("narration", "") for seg in script.get("segments", [])}

    shots = []
    for s in shot_plan.get("shots", []):
        sid = s["shot_id"]
        p = prompt_by_shot.get(sid, {})
        r = model_by_shot.get(sid, {})
        shots.append({
            "shot_id": sid, "purpose": s.get("purpose"),
            "footage_type": r.get("footage_type"),
            "model": r.get("selected_model"),
            "model_reason": r.get("reason"),
            "fallback_model": r.get("fallback_model"),
            "cost_confirmed": r.get("cost_confirmed"),
            "needs_pricing_confirmation": r.get("needs_pricing_confirmation"),
            "prompt": p.get("prompt", ""),
            "negative_prompt": p.get("negative_prompt") or GLOBAL_NEGATIVE,
            "voiceover_line": s.get("voiceover") or vo_by_label.get(s.get("purpose"), ""),
            "text_overlay": s.get("on_screen_text", ""),
            "continuity_notes": (f"footage world: {scout.get('selected_footage_world', '—')}; "
                                 f"style: {scout.get('shot_style', {})}"),
        })

    payload = {
        "date": date,
        "reel_style": "realistic premium finance media reel",
        "story_summary": story.get("summary") or story.get("headline", ""),
        "viewer_takeaway": brief.get("teaching_goal") or (brief.get("creative_brief") or {}).get("teaching_goal", ""),
        "visual_continuity": scout.get("why_this_world_fits", ""),
        "footage_world": scout.get("selected_footage_world", ""),
        "text_style": (trend.get("recommended_text_style")
                       or "centered kinetic typography, one underlined key word per screen"),
        "voice_style": "calm, credible Indian finance-media narration; educational, no hype",
        "shots": shots,
        "global_negative_prompt": GLOBAL_NEGATIVE,
        "scaffold_note": "Chunk 1 assembly. Real-world b-roll prompt rewriting is the next chunk.",
    }
    state.save_artifact(date, "prompt_bible", payload)
    return payload
