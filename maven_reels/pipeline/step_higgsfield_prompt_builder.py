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

# Newsroom rework: realistic finance-MEDIA footage, not abstract AI dashboards.
REALISTIC_NEGATIVE = ("no readable text, no fake text, no fake numbers, no fake "
                      "stock tickers, no fake company names, no fake logos, no buy "
                      "or sell arrows, no trading-signal visuals, no gibberish "
                      "panels, no cluttered AI dashboard, no floating fake panels, "
                      "no random candlestick wall, no cartoon bull, no cartoon "
                      "bear, no meme style, no cheap AI look, no distorted faces, "
                      "no warped hands, no morphing artifacts, no watermark")


def _realistic_prompt(shot: dict, scout: dict, idx: int) -> str:
    """Realistic finance-media b-roll prompt from the Location Scout footage world."""
    world = scout.get("selected_footage_world", "finance_newsroom")
    refs = scout.get("realistic_visual_references") or ["premium finance newsroom"]
    ref = refs[idx % len(refs)]
    st = scout.get("shot_style", {})
    rules = "; ".join(scout.get("scene_environment_rules", []))
    return (f"Realistic, premium FINANCE-MEDIA b-roll footage for Maven, an Indian "
            f"stock-market research brand — filmed-documentary look, photoreal, NOT "
            f"an abstract dashboard.\n"
            f"Scene purpose: {shot['purpose']}.\n"
            f"Footage world: {world}. Real environment: {ref}.\n"
            f"Motion: {shot.get('motion','subtle real camera motion')}. "
            f"Camera: {st.get('camera', shot.get('camera','controlled glide'))}. "
            f"Lighting: {st.get('lighting','clean broadcast')}. "
            f"Mood: {st.get('mood','credible, premium')}. "
            f"Colour: {st.get('color_palette','navy + teal + white')}. "
            f"Realism: {st.get('realism_level','photoreal')}.\n"
            f"Real continuous filmed motion throughout — never a static frame, never "
            f"a slideshow, never floating fake UI. {rules}. Leave clean negative "
            f"space for text overlays and subtitles.\n"
            f"Output: animated MP4 video clip, vertical 9:16, 2-4 seconds.")

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
        intensity: str | None = None, model_plan: dict | None = None,
        location_scout: dict | None = None, routing_plan: dict | None = None) -> dict:
    """When location_scout + routing_plan are supplied (Newsroom live run), build
    REALISTIC finance-media b-roll prompts and route the model per shot from the
    Camera Router. Falls back to the legacy abstract prompt when they are absent."""
    direction = creative_direction.get("selected_direction", {})
    # prefer the realistic Camera Router routing; fall back to the cost router
    realistic = {p["scene_id"]: p for p in (routing_plan or {}).get("per_scene_model_plan", [])}
    routed = {p["scene_id"]: p for p in (model_plan or {}).get("scene_model_plan", [])}
    scout = location_scout if (location_scout and location_scout.get("selected_footage_world")) else None
    method = config.HIGGSFIELD_GENERATION_METHOD
    prompts = []
    for i, s in enumerate(shot_plan.get("shots", [])):
        route = realistic.get(s["shot_id"]) or routed.get(s["shot_id"], {})
        prompts.append({
            "shot_id": s["shot_id"],
            "purpose": s["purpose"],
            "prompt": (_realistic_prompt(s, scout, i) if scout else _motion_prompt(s, direction, intensity)),
            "seed_image_prompt": _seed_prompt(s, direction) if method == "image_seed" else None,
            "negative_prompt": REALISTIC_NEGATIVE if scout else NEGATIVE,
            "duration": config.HIGGSFIELD_GEN_CLIP_SECONDS,
            "target_duration_in_reel": s["duration"],
            "aspect_ratio": "9:16",
            "model_recommendation": route.get("selected_model", config.HIGGSFIELD_VIDEO_MODEL),
            "fallback_model": route.get("fallback_model"),
            "estimated_cost": route.get("estimated_cost"),
            "cost_confirmed": route.get("cost_confirmed"),
            "needs_pricing_confirmation": route.get("needs_pricing_confirmation"),
            "footage_type": route.get("footage_type"),
            "scene_complexity": route.get("scene_complexity"),
            "seed_model": config.HIGGSFIELD_SEED_MODEL if method == "image_seed" else None,
            "requires_paid_generation": True,
        })

    payload = {"date": date, "shot_prompts": prompts, "count": len(prompts),
               "intensity": intensity or "standard",
               "footage_world": (scout or {}).get("selected_footage_world"),
               "prompt_style": "realistic_finance_media" if scout else "abstract_premium",
               "method": method,
               "why": ("direct text-to-video (cheapest); the no-text/no-numbers "
                       "compliance rule is enforced by prompt + negative prompt "
                       "and verified by the Scene Quality Inspector"
                       if method == "text_to_video" else
                       "seed stills contain no text -> motion clips can never "
                       "contain baked/garbled text")}
    state.save_artifact(date, "shot_prompts", payload)
    return payload
