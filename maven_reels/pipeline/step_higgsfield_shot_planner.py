"""Step — Higgsfield Shot Planner.

Turns the edited script into 5-6 cinematic animated SHOTS (2-4s each) that form
a proper short-form story arc: hook -> context -> data/move -> reason -> impact
-> Maven CTA. Each shot carries the visual concept + motion + camera the Prompt
Builder turns into a generation prompt. Important on-screen text/numbers are
NEVER part of the Higgsfield scene — they are overlaid later by the assembler.
"""
from __future__ import annotations

from . import config, state

# (purpose, seconds, camera) — durations sum to TARGET_REEL_DURATION_SECONDS=18
_ARC = [
    ("hook",    2.5, "hard push-in that lands on the hero visual"),
    ("context", 3.0, "slow lateral glide across a market dashboard wall"),
    ("data",    3.0, "rising crane move over glowing data panels"),
    ("reason",  3.5, "focus pull from foreground blur to the core visual"),
    ("impact",  3.0, "wide settling shot with subtle parallax depth"),
    ("cta",     3.0, "calm slow zoom toward a clean branded space"),
]

_CONCEPTS = {
    "hook":    "the single strongest scroll-stopping hero visual of the day's story",
    "context": "an animated premium market dashboard establishing the Indian market setting",
    "data":    "abstract glowing data panels and index motion suggesting the day's move (no real numbers)",
    "reason":  "a visual metaphor for the driver behind the move (flows, sectors, policy, liquidity)",
    "impact":  "the market landscape settling into its new state — breadth, depth, mood",
    "cta":     "a calm premium branded end-space with clean negative room for the Maven CTA overlay",
}


def _voiceover_slices(script_edited: dict) -> dict[str, str]:
    """Map script segments onto shot purposes for VO alignment."""
    segs = {s.get("label"): s.get("narration", "") for s in script_edited.get("segments", [])}
    return {
        "hook": segs.get("hook", ""),
        "context": segs.get("what", ""),
        "data": segs.get("what", ""),
        "reason": segs.get("why", ""),
        "impact": segs.get("understand", ""),
        "cta": segs.get("cta", ""),
    }


def run(date: str, *, story: dict, hooks: dict, script_edited: dict,
        creative_direction: dict) -> dict:
    direction = creative_direction.get("selected_direction", {})
    motion = direction.get("motion_language", "smooth cinematic motion")
    motifs = direction.get("visual_motifs", [])
    vo = _voiceover_slices(script_edited)
    on_screen_hook = hooks.get("on_screen_hook", hooks.get("selected_hook", ""))

    arc = _ARC[: config.MAX_HIGGSFIELD_SCENES_PER_REEL]
    shots, t = [], 0.0
    for i, (purpose, secs, camera) in enumerate(arc, start=1):
        motif = motifs[(i - 1) % len(motifs)] if motifs else "premium data wall"
        shots.append({
            "shot_id": f"shot_{i:02d}",
            "start": round(t, 2), "end": round(t + secs, 2), "duration": secs,
            "purpose": purpose,
            "voiceover": vo.get(purpose, ""),
            "on_screen_text": on_screen_hook if purpose == "hook" else "",
            "visual_concept": f"{_CONCEPTS[purpose]} — built around the motif: {motif}",
            "motion": motion,
            "camera": camera,
            "transition_out": "hard cut" if purpose == "hook" else "smooth motion cut",
            "text_overlay_needed": purpose in ("hook", "data", "cta"),
            "higgsfield_prompt_notes": (
                f"Direction: {direction.get('name', '')}. Style: {direction.get('style', '')}. "
                f"Mood: {direction.get('mood', '')}. Strongest shot of the reel."
                if purpose == "hook" else
                f"Direction: {direction.get('name', '')}. Keep visually distinct from other shots."),
        })
        t += secs

    payload = {"date": date, "total_duration": round(t, 1),
               "shot_count": len(shots), "shots": shots,
               "direction": direction.get("name")}
    state.save_artifact(date, "shot_plan", payload)
    return payload
