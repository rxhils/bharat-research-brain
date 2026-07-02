"""Step — Reel Improvement Director.

Reads a rejected reel's feedback + auditor scores and decides exactly what to
keep, what to change, and which steps to re-run for the next version. The plan is
deterministic and auditable (improvement_plan.json). Steps that need the Claude
Code conductor (fresh research, new voiceover, paid Higgsfield) are flagged —
never faked.
"""
from __future__ import annotations

from . import state

# feedback_type -> plan skeleton
PLANS: dict[str, dict] = {
    "weak_hook": {
        "keep": ["research", "viral_fit"],
        "change": ["angle", "hook", "script", "storyboard", "video"],
        "rerun_steps": ["angle_studio", "hook_lab", "script_room", "retention_editor",
                        "motion_storyboard", "subtitle_engine", "motion_graphics",
                        "cover_studio", "reel_auditor"],
        "needs_conductor": ["voice_studio"],   # narration changed -> new VO required
        "strategy": "Stronger scroll-stop hook; rebuild script + edit around it."},
    "boring_script": {
        "keep": ["research", "viral_fit", "angle"],
        "change": ["script", "pacing", "storyboard", "video"],
        "rerun_steps": ["script_room", "retention_editor", "motion_storyboard",
                        "subtitle_engine", "motion_graphics", "cover_studio", "reel_auditor"],
        "needs_conductor": ["voice_studio"],
        "strategy": "Tighter, punchier script; every line earns its 2 seconds."},
    "bad_animation": {
        "keep": ["research", "viral_fit", "angle", "hooks", "script", "voiceover"],
        "change": ["creative_direction", "shot_plan", "prompts", "scenes", "video", "cover"],
        "rerun_steps": ["higgsfield_creative_director", "higgsfield_shot_planner",
                        "higgsfield_prompt_builder", "higgsfield_scene_generator",
                        "scene_quality_inspector", "final_reel_assembler", "reel_auditor"],
        "needs_conductor": ["higgsfield_scene_generator"],   # PAID regeneration
        "strategy": "Rebuild prompts with stronger motion, regenerate scenes, reassemble."},
    "visuals_too_basic": {
        "keep": ["research", "viral_fit", "angle", "hooks", "script", "voiceover"],
        "change": ["creative_direction", "shot_plan", "prompts", "scenes", "video", "cover"],
        "rerun_steps": ["higgsfield_creative_director", "higgsfield_shot_planner",
                        "higgsfield_prompt_builder", "higgsfield_scene_generator",
                        "scene_quality_inspector", "final_reel_assembler", "reel_auditor"],
        "needs_conductor": ["higgsfield_scene_generator"],   # PAID regeneration
        "strategy": "New creative direction + regenerated Higgsfield scenes for a premium look."},
    "scenes_not_premium": {
        "keep": ["research", "viral_fit", "angle", "hooks", "script", "voiceover"],
        "change": ["creative_direction", "prompts", "scenes", "video", "cover"],
        "rerun_steps": ["higgsfield_creative_director", "higgsfield_prompt_builder",
                        "higgsfield_scene_generator", "scene_quality_inspector",
                        "final_reel_assembler", "reel_auditor"],
        "needs_conductor": ["higgsfield_scene_generator"],
        "strategy": "Stronger creative direction + regenerate the weak scenes."},
    "not_visually_captivating": {
        "keep": ["research", "viral_fit", "angle", "hooks", "script", "voiceover"],
        "change": ["creative_direction", "shot_plan", "prompts", "scenes", "video", "cover"],
        "rerun_steps": ["higgsfield_creative_director", "higgsfield_shot_planner",
                        "higgsfield_prompt_builder", "higgsfield_scene_generator",
                        "scene_quality_inspector", "final_reel_assembler", "reel_auditor"],
        "needs_conductor": ["higgsfield_scene_generator"],
        "strategy": "Full visual re-dress: bolder direction, stronger motion, new scenes."},
    "too_slow": {
        "keep": ["research", "viral_fit", "angle", "hooks"],
        "change": ["script_length", "scene_count", "transitions", "video"],
        "rerun_steps": ["retention_editor", "motion_storyboard", "subtitle_engine",
                        "motion_graphics", "cover_studio", "reel_auditor"],
        "needs_conductor": ["voice_studio"],
        "strategy": "Shorter script, more micro-scenes, faster transitions."},
    "bad_voiceover": {
        "keep": ["research", "viral_fit", "angle", "hooks", "script", "storyboard", "video_structure"],
        "change": ["voiceover", "subtitles"],
        "rerun_steps": ["subtitle_engine", "motion_graphics", "reel_auditor"],
        "needs_conductor": ["voice_studio"],
        "strategy": "Re-record VO (calm, confident, premium), remux the edit."},
    "bad_subtitles": {
        "keep": ["research", "viral_fit", "angle", "hooks", "script", "voiceover"],
        "change": ["subtitles", "video"],
        "rerun_steps": ["subtitle_engine", "motion_graphics", "reel_auditor"],
        "needs_conductor": [],
        "strategy": "Re-time + restyle kinetic captions; re-render."},
    "not_premium_enough": {
        "keep": ["research", "viral_fit", "angle", "hooks", "script", "voiceover"],
        "change": ["template", "motion_variation", "assets", "storyboard", "video", "cover"],
        "rerun_steps": ["template_selector", "motion_variation", "asset_picker",
                        "motion_storyboard", "motion_graphics", "cover_studio", "reel_auditor"],
        "needs_conductor": [],
        "strategy": "Full visual re-dress: premium layering, better cover, new accent."},
    "wrong_story": {
        "keep": [],
        "change": ["everything"],
        "rerun_steps": ["market_sentinel", "viral_fit", "angle_studio", "hook_lab",
                        "script_room", "retention_editor", "template_selector",
                        "motion_variation", "motion_storyboard", "asset_picker",
                        "subtitle_engine", "motion_graphics", "cover_studio", "reel_auditor"],
        "needs_conductor": ["market_sentinel", "voice_studio"],
        "strategy": "Completely new reel from fresh research."},
    "bad_data": {
        "keep": [],
        "change": ["everything"],
        "rerun_steps": ["market_sentinel"],
        "needs_conductor": ["market_sentinel", "voice_studio"],
        "strategy": "Stop and re-research. No reel until data is verified + sourced."},
    "try_different_style": {
        "keep": ["research", "viral_fit", "angle", "hooks", "script", "voiceover"],
        "change": ["template", "motion_variation", "assets", "video", "cover"],
        "rerun_steps": ["template_selector", "motion_variation", "asset_picker",
                        "motion_storyboard", "motion_graphics", "cover_studio", "reel_auditor"],
        "needs_conductor": [],
        "strategy": "Same story, different visual identity."},
    "improve_animations_quality": {
        "keep": ["research", "viral_fit", "angle", "hooks", "script", "voiceover"],
        "change": ["motion_variation", "storyboard", "transitions", "video", "cover", "sound"],
        "rerun_steps": ["motion_variation", "motion_storyboard", "asset_picker",
                        "motion_graphics", "cover_studio", "reel_auditor"],
        "needs_conductor": [],
        "strategy": ("One-click quality pass: more motion every 1-2s, stronger hook "
                     "animation, better layering + transitions + cover.")},
    "other": {
        "keep": ["research", "viral_fit"],
        "change": ["per_custom_feedback"],
        "rerun_steps": ["motion_variation", "motion_storyboard", "asset_picker",
                        "motion_graphics", "cover_studio", "reel_auditor"],
        "needs_conductor": [],
        "strategy": "General improvement pass guided by custom feedback."},
}

# a failing auditor score -> extra reroute even without explicit feedback
SCORE_REROUTE = {
    "hook": "weak_hook", "retention": "too_slow", "edit_quality": "bad_animation",
    "visual_quality": "visuals_too_basic", "subtitle": "bad_subtitles",
    "voiceover": "bad_voiceover",
}


def run(run_key: str, *, feedback_type: str, custom_feedback: str = "",
        quality: dict | None = None) -> dict:
    plan = PLANS.get(feedback_type, PLANS["other"])
    scores = (quality or {}).get("scores", {})
    gates = (quality or {}).get("gates", {})

    # fold in auditor failures the human didn't mention
    extra = sorted({SCORE_REROUTE[k] for k, v in scores.items()
                    if k in SCORE_REROUTE and gates.get(k) and v < gates[k]}
                   - {feedback_type})
    rerun = list(dict.fromkeys(plan["rerun_steps"] +
                               [s for e in extra for s in PLANS[e]["rerun_steps"]]))

    target = {k: max(gates.get(k, 90), scores.get(k, 0) + 5) for k in
              ("hook", "retention", "edit_quality", "visual_quality")}

    payload = {
        "run_key": run_key,
        "feedback_type": feedback_type,
        "custom_feedback": custom_feedback,
        "improvement_plan": {
            "keep": plan["keep"], "change": plan["change"],
            "rerun_steps": rerun,
            "reason": plan["strategy"] + (f" Also fixing auditor fails: {extra}." if extra else ""),
            "target_scores": target,
        },
        "next_version_strategy": plan["strategy"],
        "reroute_to": rerun,
        "needs_conductor": plan["needs_conductor"],
        "locally_completable": not plan["needs_conductor"],
        "auditor_failures_folded_in": extra,
    }
    state.save_artifact(run_key, "improvement_plan", payload)
    return payload
