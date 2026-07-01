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
               step_higgsfield_asset_request, step11_subtitles, step14_caption,
               step15_compliance, step16_quality)


def prepare(date: str) -> dict:
    """date is a run key: 'YYYY-MM-DD' (legacy) or a job id like
    'reel-2026-07-02-1700-001' — both map to outputs/maven_reels/<key>/."""
    research = state.load_artifact(date, "research")   # produced by reel research agent
    step01_research.run(date, research)
    dup = step_duplicate_check.run(date, research)
    viral_fit = step02_viral_fit.run(date, research, duplicate_check=dup)
    story = viral_fit["chosen"]["story"]

    angle = step03_angle.run(date, viral_fit)
    hooks = step04_hooks.run(date, angle, viral_fit)
    script = step05_script.run(date, story, hooks)
    edited = step06_retention.run(date, script)

    # cost-optimized path: choose a template + motion variation, then storyboard.
    # If the composition is too similar to recent reels, rotate the variation and
    # retry (up to the number of presets) — uniqueness without new generation.
    template = step_template_selector.run(date, story=story, angle=angle)
    variation = step_motion_variation.run(date, template=template)
    uniqueness = None
    for attempt in range(len(config.MOTION_VARIATIONS)):
        storyboard = step6_motion_storyboard.run(date, story=story, hooks=hooks,
                                                 script_edited=edited, viral_fit=viral_fit,
                                                 template=template, variation=variation)
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
    higgs = step_higgsfield_asset_request.run(date, asset_picker=asset_picker)

    subtitles = step11_subtitles.run(date, edited)
    caption = step14_caption.run(date, story, hooks, angle)
    compliance = step15_compliance.run(date, hooks=hooks, angle=angle,
                                       script_edited=edited, caption=caption)
    quality = step16_quality.run(date, hooks=hooks, script_edited=edited,
                                 storyboard=storyboard, compliance=compliance,
                                 caption=caption, subtitles=subtitles,
                                 asset_picker=asset_picker,
                                 cost_guard=asset_picker.get("cost_guard"),
                                 research=research, visual_uniqueness=uniqueness)

    rs = state.RunState.load_or_new(date)
    for k in ("research", "viral_fit", "angle", "hooks", "script", "retention",
              "template", "motion_variation", "storyboard", "asset_picker",
              "higgsfield_request", "subtitles", "caption", "compliance", "quality"):
        rs.mark(k)
    return {"date": date, "chosen_story": story.get("headline"),
            "viral_fit": viral_fit["chosen"]["viral_fit"],
            "duplicate_risk": dup["duplicate_risk"],
            "hook": hooks["chosen"]["text"], "scenes": storyboard["scene_count"],
            "template": template["selected_template"],
            "variation": variation["variation_id"],
            "visual_uniqueness": (uniqueness or {}).get("visual_uniqueness_score"),
            "paid_generation_required": asset_picker["paid_generation_required"],
            "new_generations": asset_picker["estimated_new_generations"],
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
