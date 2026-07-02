"""Reels orchestrator.

prepare() runs every DETERMINISTIC step end-to-end (no paid media, no LLM, no
publish): research gate -> viral fit -> angle -> hooks -> script -> retention ->
storyboard -> visual direction -> scene jobs -> subtitles -> cover job -> caption
-> compliance -> reel auditor. The external steps (Higgsfield scenes/voiceover,
ffmpeg cut, Composio Reels publish) run in the Claude Code conductor.
"""
from __future__ import annotations

import argparse

from . import (config, state, step01_research, step02_viral_fit, step03_angle,
               step04_hooks, step05_script, step06_retention, step_duplicate_check,
               step_template_selector, step_motion_variation, step_visual_uniqueness,
               step6_motion_storyboard, step7_asset_director, step_asset_picker,
               step_higgsfield_asset_request, step11_subtitles,
               step14_caption, step15_compliance, step16_quality,
               step_renderer_selector, step_higgsfield_creative_director,
               step_higgsfield_shot_planner, step_higgsfield_prompt_builder,
               step_higgsfield_scene_generator, step_higgsfield_model_router)


def prepare(date: str, renderer: str | None = None) -> dict:
    """date is a run key: 'YYYY-MM-DD' (legacy) or a job id like
    'reel-2026-07-02-1700-001' — both map to outputs/maven_reels/<key>/.
    renderer: higgsfield_primary (default) | remotion_fallback | simulation_only."""
    research = state.load_artifact(date, "research")   # produced by reel research agent
    step01_research.run(date, research)
    dup = step_duplicate_check.run(date, research)
    viral_fit = step02_viral_fit.run(date, research, duplicate_check=dup)
    story = viral_fit["chosen"]["story"]

    angle = step03_angle.run(date, viral_fit)
    hooks = step04_hooks.run(date, angle, viral_fit)
    script = step05_script.run(date, story, hooks)
    edited = step06_retention.run(date, script)

    renderer_sel = step_renderer_selector.run(date, requested=renderer)

    # cost-optimized path: choose a template + motion variation, then storyboard.
    # If the composition is too similar to recent reels, rotate the variation and
    # retry (up to the number of presets) — uniqueness without new generation.
    template = step_template_selector.run(date, story=story, angle=angle)
    variation = step_motion_variation.run(date, template=template)
    is_higgsfield = renderer_sel["renderer"] != "remotion_fallback"
    uniqueness, asset_picker = None, None
    for attempt in range(len(config.MOTION_VARIATIONS)):
        storyboard = step6_motion_storyboard.run(date, story=story, hooks=hooks,
                                                 script_edited=edited, viral_fit=viral_fit,
                                                 template=template, variation=variation)
        if not is_higgsfield:
            # STATIC PLATES exist ONLY for the explicit Remotion fallback —
            # Higgsfield-primary reels never touch still-image assets.
            step7_asset_director.run(date, storyboard)
            asset_picker = step_asset_picker.run(date, storyboard=storyboard,
                                                 template=template, story=story)
        uniqueness = step_visual_uniqueness.run(date, template=template,
                                                variation=variation,
                                                storyboard=storyboard,
                                                asset_picker=asset_picker)
        if uniqueness["passed"]:
            break
        # rotate to the next preset, avoiding the one that collided
        order = list(config.MOTION_VARIATIONS)
        nxt = order[(order.index(variation["variation_id"]) + 1) % len(order)]
        variation = step_motion_variation.run(date, force_id=nxt)
    higgs = (step_higgsfield_asset_request.run(date, asset_picker=asset_picker)
             if asset_picker is not None else None)

    # HIGGSFIELD-PRIMARY chain (free/deterministic here): creative direction ->
    # shot plan -> prompts -> generation plan (gated; conductor executes after a
    # UI trigger). The template/storyboard/asset chain above stays intact as the
    # explicit Remotion fallback path — never used silently.
    direction = step_higgsfield_creative_director.run(date, story=story,
                                                      angle=angle, hooks=hooks)
    shot_plan = step_higgsfield_shot_planner.run(date, story=story, hooks=hooks,
                                                 script_edited=edited,
                                                 creative_direction=direction)
    # per-scene cheapest-suitable model routing BEFORE prompts are built
    model_plan = step_higgsfield_model_router.run(date, shot_plan=shot_plan)
    shot_prompts = step_higgsfield_prompt_builder.run(date, shot_plan=shot_plan,
                                                      creative_direction=direction,
                                                      model_plan=model_plan)
    scene_gen = step_higgsfield_scene_generator.plan(date, shot_prompts=shot_prompts,
                                                     renderer=renderer_sel)

    # if clips already exist on disk (conductor already generated), inspect them
    scene_quality = None
    if step_higgsfield_scene_generator.clips_on_disk(date):
        from . import step_scene_quality_inspector
        scene_quality = step_scene_quality_inspector.run(date, scene_generation=scene_gen)

    subtitles = step11_subtitles.run(date, edited)
    caption = step14_caption.run(date, story, hooks, angle)
    compliance = step15_compliance.run(date, hooks=hooks, angle=angle,
                                       script_edited=edited, caption=caption)
    quality = step16_quality.run(date, hooks=hooks, script_edited=edited,
                                 storyboard=storyboard, compliance=compliance,
                                 caption=caption, subtitles=subtitles,
                                 asset_picker=asset_picker,
                                 cost_guard=(asset_picker or {}).get("cost_guard"),
                                 research=research, visual_uniqueness=uniqueness,
                                 fresh_video=scene_gen, viral_fit=viral_fit,
                                 scene_quality=scene_quality,
                                 renderer=renderer_sel["renderer"])

    rs = state.RunState.load_or_new(date)
    for k in ("research", "viral_fit", "angle", "hooks", "script", "retention",
              "renderer_selection", "creative_direction", "shot_plan",
              "shot_prompts", "scene_generation", "template", "motion_variation",
              "storyboard", "asset_picker", "higgsfield_request", "subtitles",
              "caption", "compliance", "quality"):
        rs.mark(k)
    return {"date": date, "chosen_story": story.get("headline"),
            "viral_fit": viral_fit["chosen"]["viral_fit"],
            "duplicate_risk": dup["duplicate_risk"],
            "hook": hooks["chosen"]["text"],
            "renderer": renderer_sel["renderer"],
            "creative_direction": direction["selected_direction"].get("name"),
            "shots": shot_plan["shot_count"],
            "generation_status": scene_gen["generation_status"],
            "estimated_generation_cost": scene_gen["estimated_cost_credits"],
            "template": template["selected_template"],
            "variation": variation["variation_id"],
            "visual_uniqueness": (uniqueness or {}).get("visual_uniqueness_score"),
            "verdict": quality["verdict"], "scores": quality["scores"]}


def main() -> None:
    p = argparse.ArgumentParser(description="Maven Reels pipeline")
    p.add_argument("step", choices=["prepare"])
    p.add_argument("--date", default=config.run_date())
    args = p.parse_args()
    if args.step == "prepare":
        print(prepare(args.date))


if __name__ == "__main__":
    main()
