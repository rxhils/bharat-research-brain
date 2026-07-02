"""Step — Higgsfield Prompt Builder.

Builds a strong, compliance-safe generation prompt for every planned shot:
image-seed prompt (nano_banana_pro still) + animation directive (seedance1_5
image-to-video). The image-seed->animate method is deliberate: the seed never
contains text, so the motion clip can never contain baked/garbled text —
enforcing the hard rule that all real numbers/claims are overlaid locally.
"""
from __future__ import annotations

from . import config, state

NEGATIVE = ("static image, still poster, slideshow, cheap Canva animation, "
            "cheap stock market video, random candlestick spam, low quality AI "
            "artifacts, fake numbers, readable nonsense text, fake logo, clutter, "
            "meme style, cartoon bull, cartoon bear, buy signal, sell signal, "
            "trading call, cluttered trading screen, overexposed, blurry, "
            "distorted, ugly text, distorted charts, watermark, 3D coins")

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
    palette = ", ".join(direction.get("color_palette", [])[:3])
    return (f"Create a premium vertical 9:16 ANIMATED finance video scene for "
            f"Maven, an Indian stock market research brand.\n"
            f"Scene purpose: {shot['purpose']}.\n"
            f"Visual concept: {shot['visual_concept']}.\n"
            f"Motion style: {shot['motion']}.\n"
            f"Camera movement: {shot['camera']}.\n"
            f"Aesthetic: {_STYLE}. Direction: {direction.get('name','')} — "
            f"{direction.get('style','')}. Mood: {direction.get('mood','')}. "
            f"Palette accents: {palette}. Motion language: "
            f"{direction.get('motion_language','calm premium motion')}. "
            f"Real continuous motion throughout — never a static frame, never a "
            f"slideshow. Smooth, high-end, no chaotic movement, no morphing "
            f"artifacts.{boost}\n{_RULES}\n"
            f"Output: animated MP4 video clip, vertical 9:16, 2-4 seconds.")


def run(date: str, *, shot_plan: dict, creative_direction: dict,
        intensity: str | None = None, model_plan: dict | None = None) -> dict:
    direction = creative_direction.get("selected_direction", {})
    routed = {p["scene_id"]: p for p in (model_plan or {}).get("scene_model_plan", [])}
    method = config.HIGGSFIELD_GENERATION_METHOD
    prompts = []
    for s in shot_plan.get("shots", []):
        route = routed.get(s["shot_id"], {})
        prompts.append({
            "shot_id": s["shot_id"],
            "purpose": s["purpose"],
            "prompt": _motion_prompt(s, direction, intensity),
            "seed_image_prompt": _seed_prompt(s, direction) if method == "image_seed" else None,
            "negative_prompt": NEGATIVE,
            "duration": config.HIGGSFIELD_GEN_CLIP_SECONDS,
            "target_duration_in_reel": s["duration"],
            "aspect_ratio": "9:16",
            "model_recommendation": route.get("selected_model", config.HIGGSFIELD_VIDEO_MODEL),
            "fallback_model": route.get("fallback_model"),
            "estimated_cost": route.get("estimated_cost"),
            "scene_complexity": route.get("scene_complexity"),
            "seed_model": config.HIGGSFIELD_SEED_MODEL if method == "image_seed" else None,
            "requires_paid_generation": True,
        })

    payload = {"date": date, "shot_prompts": prompts, "count": len(prompts),
               "intensity": intensity or "standard",
               "method": method,
               "why": ("direct text-to-video (cheapest); the no-text/no-numbers "
                       "compliance rule is enforced by prompt + negative prompt "
                       "and verified by the Scene Quality Inspector"
                       if method == "text_to_video" else
                       "seed stills contain no text -> motion clips can never "
                       "contain baked/garbled text")}
    state.save_artifact(date, "shot_prompts", payload)
    return payload
