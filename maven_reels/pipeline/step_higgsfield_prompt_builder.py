"""Step — Higgsfield Prompt Builder.

Builds a strong, compliance-safe generation prompt for every planned shot:
image-seed prompt (nano_banana_pro still) + animation directive (seedance1_5
image-to-video). The image-seed->animate method is deliberate: the seed never
contains text, so the motion clip can never contain baked/garbled text —
enforcing the hard rule that all real numbers/claims are overlaid locally.
"""
from __future__ import annotations

from . import config, state

NEGATIVE = ("cheap stock market video, random candlestick spam, low quality AI "
            "artifacts, fake numbers, readable nonsense text, fake logo, clutter, "
            "meme style, cartoon bull, cartoon bear, buy signal, sell signal, "
            "trading call, overexposed, blurry, ugly text, distorted charts, "
            "watermark, 3D coins")

_STYLE = ("premium financial newsroom, modern Indian stock market intelligence, "
          "cinematic data visualization, high-end dark finance aesthetic, clean "
          "market dashboard, elegant lighting, crisp depth, sophisticated motion "
          "graphics feel")

_RULES = ("Important: No readable text. No fake numbers. No fake stock tickers. "
          "No fake company logos. No buy/sell arrows. No trading signal visuals. "
          "No clutter. No cartoon style. No meme style. No cheap AI look. Leave "
          "clean negative space for text overlays and subtitles.")


def _seed_prompt(shot: dict, direction: dict) -> str:
    palette = ", ".join(direction.get("color_palette", [])[:3])
    return (f"Create a premium 9:16 finance scene still for Maven, an Indian stock "
            f"market research brand — this frame will be animated into video.\n"
            f"Scene purpose: {shot['purpose']}.\n"
            f"Visual concept: {shot['visual_concept']}.\n"
            f"Style: {_STYLE}. Direction: {direction.get('name','')} — "
            f"{direction.get('style','')}. Mood: {direction.get('mood','')}. "
            f"Palette accents: {palette}.\n{_RULES}\n"
            f"Output: vertical 9:16, high resolution, clean, premium, visually captivating.")


def _motion_prompt(shot: dict, direction: dict, intensity: str | None = None) -> str:
    boost = ("" if intensity != "high" else
             "\nEnergy: HIGH — bolder camera moves, faster reveals, stronger "
             "depth and light dynamics. Still smooth and premium, never chaotic.")
    return (f"Animate this premium 9:16 finance scene for a cinematic reel.\n"
            f"Scene purpose: {shot['purpose']}.\n"
            f"Motion: {shot['motion']}.\n"
            f"Camera: {shot['camera']}.\n"
            f"Motion language: {direction.get('motion_language','calm premium motion')}. "
            f"Smooth, high-end, no chaotic movement, no morphing artifacts.{boost}\n{_RULES}")


def run(date: str, *, shot_plan: dict, creative_direction: dict,
        intensity: str | None = None) -> dict:
    direction = creative_direction.get("selected_direction", {})
    prompts = [{
        "shot_id": s["shot_id"],
        "purpose": s["purpose"],
        "prompt": _motion_prompt(s, direction, intensity),
        "seed_image_prompt": _seed_prompt(s, direction),
        "negative_prompt": NEGATIVE,
        "duration": config.HIGGSFIELD_GEN_CLIP_SECONDS,
        "target_duration_in_reel": s["duration"],
        "aspect_ratio": "9:16",
        "model_recommendation": config.HIGGSFIELD_VIDEO_MODEL,
        "seed_model": config.HIGGSFIELD_SEED_MODEL,
        "requires_paid_generation": True,
    } for s in shot_plan.get("shots", [])]

    payload = {"date": date, "shot_prompts": prompts, "count": len(prompts),
               "intensity": intensity or "standard",
               "method": "image_seed_then_animate",
               "why": "seed stills contain no text -> motion clips can never "
                      "contain baked/garbled text (compliance hard rule)"}
    state.save_artifact(date, "shot_prompts", payload)
    return payload
