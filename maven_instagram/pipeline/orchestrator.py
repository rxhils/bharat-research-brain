"""Orchestrator — runs the pipeline steps in order with shared state.

Design goals (from the brief):
  * modular: each step can be rerun independently
  * never regenerate research if only design fails
  * never regenerate images if only caption fails
  * never publish without the final validation + explicit confirmation
  * nothing lost: every step persists JSON before the next runs

The two network steps (image generation, publish) are delegated to an Executor
(see mcp_adapter). With the default NoopExecutor the orchestrator runs in
"prepare" mode: it builds every artifact and the exact MCP payloads, stopping
before any live image-gen or publish so the agent/human can drive those.
"""
from __future__ import annotations

import argparse

from . import (config, logging_setup, state, step1_research, step2_content_plan,
               step3_creative_direction, step4_images, step5_caption,
               step6_hashtags, step7_quality_check, step8_publish)
from .mcp_adapter import Executor, NoopExecutor

STEPS = ["research", "content", "creative", "images", "caption", "hashtags",
         "quality", "publish"]


def run_research(date: str) -> dict:
    research = state.load_artifact(date, "research")  # produced by research agent
    return step1_research.run(date, research)


def run_content(date: str) -> dict:
    research = state.load_artifact(date, "research")
    return step2_content_plan.run(date, research)


def run_creative(date: str) -> dict:
    return step3_creative_direction.run(date)


def run_images_build(date: str) -> dict:
    content = state.load_artifact(date, "content_plan")
    creative = state.load_artifact(date, "creative")
    return step4_images.build_image_jobs(date, content, creative)


def run_caption(date: str) -> dict:
    research = state.load_artifact(date, "research")
    content = state.load_artifact(date, "content_plan")
    return step5_caption.run(date, research, content)


def run_hashtags(date: str) -> dict:
    research = state.load_artifact(date, "research")
    return step6_hashtags.run(date, research)


def run_quality(date: str, aesthetic_score: int | None = None) -> dict:
    return step7_quality_check.run(
        date,
        research=state.load_artifact(date, "research"),
        content_plan=state.load_artifact(date, "content_plan"),
        images=state.load_artifact(date, "images"),
        caption=state.load_artifact(date, "caption"),
        hashtags=state.load_artifact(date, "hashtags"),
        aesthetic_score=aesthetic_score,
    )


def run_publish_build(date: str, image_urls: list[str]) -> dict:
    caption = state.load_artifact(date, "caption")["caption"]
    return step8_publish.build_payloads(date, image_urls, caption)


def prepare_all(date: str, executor: Executor | None = None) -> dict:
    """Run every non-network step and build payloads. Stops before live
    image-gen and publish (delegated to the executor / agent)."""
    executor = executor or NoopExecutor()
    log = logging_setup.get_logger("orchestrator", date, config.run_dir(date))
    rs = state.RunState.load_or_new(date)

    log.info("Step 1: research validation + gating")
    research = run_research(date); rs.mark("research")

    log.info("Step 2: content plan")
    run_content(date); rs.mark("content")

    log.info("Step 3: creative direction")
    run_creative(date); rs.mark("creative")

    log.info("Step 4: build image jobs (generation delegated to Higgsfield MCP)")
    images = run_images_build(date); rs.mark("images_built")

    log.info("Step 5: caption")
    run_caption(date); rs.mark("caption")

    log.info("Step 6: hashtags")
    run_hashtags(date); rs.mark("hashtags")

    log.info("Prepared. Next: generate images (Higgsfield), post-process, "
             "run quality gate, then publish (Composio) after confirmation.")
    return {"date": date, "post_worthy": research["_meta"]["post_worthy_count"],
            "image_jobs": len(images["jobs"]), "state": rs.completed}


def main() -> None:
    parser = argparse.ArgumentParser(description="Maven IG carousel pipeline")
    parser.add_argument("step", choices=["prepare", *STEPS],
                        help="run the whole prepare phase or a single step")
    parser.add_argument("--date", default=config.run_date())
    parser.add_argument("--aesthetic-score", type=int, default=None,
                        help="visual review score 0-100 for the quality gate")
    args = parser.parse_args()

    if args.step == "prepare":
        print(prepare_all(args.date))
    elif args.step == "research":
        print(run_research(args.date)["_meta"])
    elif args.step == "content":
        print(run_content(args.date)["carousel_plan"])
    elif args.step == "creative":
        print(run_creative(args.date)["selected"])
    elif args.step == "images":
        print(run_images_build(args.date)["status"])
    elif args.step == "caption":
        print(run_caption(args.date)["char_count"], "chars")
    elif args.step == "hashtags":
        print(run_hashtags(args.date)["hashtags"])
    elif args.step == "quality":
        print(run_quality(args.date, args.aesthetic_score)["verdict"])
    elif args.step == "publish":
        print("Publish is agent/human-gated; use step8_publish after confirmation.")


if __name__ == "__main__":
    main()
