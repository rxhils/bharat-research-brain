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
               step04_hooks, step05_script, step06_retention, step6_motion_storyboard,
               step7_asset_director, step11_subtitles, step14_caption,
               step15_compliance, step16_quality)


def prepare(date: str) -> dict:
    research = state.load_artifact(date, "research")   # produced by reel research agent
    step01_research.run(date, research)
    viral_fit = step02_viral_fit.run(date, research)
    story = viral_fit["chosen"]["story"]

    angle = step03_angle.run(date, viral_fit)
    hooks = step04_hooks.run(date, angle, viral_fit)
    script = step05_script.run(date, story, hooks)
    edited = step06_retention.run(date, script)
    storyboard = step6_motion_storyboard.run(date, story=story, hooks=hooks,
                                             script_edited=edited, viral_fit=viral_fit)
    step7_asset_director.run(date, storyboard)

    step11_subtitles.run(date, edited)
    caption = step14_caption.run(date, story, hooks, angle)
    compliance = step15_compliance.run(date, hooks=hooks, angle=angle,
                                       script_edited=edited, caption=caption)
    quality = step16_quality.run(date, hooks=hooks, script_edited=edited,
                                 storyboard=storyboard, compliance=compliance)

    rs = state.RunState.load_or_new(date)
    for k in ("research", "viral_fit", "angle", "hooks", "script", "retention",
              "storyboard", "visual_direction", "scenes_built", "subtitles",
              "cover_built", "caption", "compliance", "quality"):
        rs.mark(k)
    return {"date": date, "chosen_story": story.get("headline"),
            "viral_fit": viral_fit["chosen"]["viral_fit"],
            "hook": hooks["chosen"]["text"], "scenes": storyboard["scene_count"],
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
