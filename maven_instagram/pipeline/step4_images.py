"""Step 4 — Build image jobs + post-process generated slides.

The actual generation runs on the Higgsfield MCP (model ``nano_banana_pro`` aka
NanoBanana). This module:
  1. Builds a UNIQUE prompt per slide (with a per-slide variation directive and
     a shared negative prompt) so the three slides never look repetitive.
  2. Defines the Higgsfield call payload (model, aspect_ratio, count).
  3. Post-processes downloaded renders into Instagram-ready JPEGs (1080x1350,
     <8MB) — this part runs locally and needs Pillow.

The orchestrator hands the job list to the MCP executor, then feeds the returned
local PNG paths back into ``postprocess``.
"""
from __future__ import annotations

from pathlib import Path

from . import config, state
from .config import (IMAGE_ASPECT_RATIO, IMAGE_JPEG_QUALITY, IMAGE_MAX_BYTES,
                     IMAGE_MODEL_PRIMARY, IMAGE_TARGET_H, IMAGE_TARGET_W,
                     PROMPTS_DIR)

NEGATIVE_PROMPT = (
    "basic Canva template, generic stock-market poster, random candlestick "
    "background, clutter, fake numbers, fake logos, unreadable tiny text, cheap "
    "AI look, cartoon style, meme style, overcomplicated 3D, glossy 3D coins, "
    "copied smallcase layout, watermark, gibberish text, bull/bear mascots, "
    "buy/sell arrows, price targets"
)

# Each slide gets a different composition so the set is not repetitive.
VARIATION = [
    "Slide 1 is the DARK COVER: near-black navy background, one oversized "
    "headline, a single faint downward trend line, index delta chips. Bold, "
    "editorial, lots of negative space.",
    "Slide 2 is a LIGHT DATA CARD: white/very-light-grey background, a single "
    "company stat block on the right, a small neutral horizontal bar for the "
    "day's move, teal accent rule. Calm and analytical.",
    "Slide 3 is a LIGHT SECTOR PANEL: light background, a minimal horizontal "
    "sector-performance bar list with exactly one highlighted bar, orange used "
    "only on the single worst bar. Structured and clean.",
]


def _load_template() -> str:
    tpl = PROMPTS_DIR / "image_prompt_template.txt"
    return tpl.read_text(encoding="utf-8") if tpl.exists() else _DEFAULT_TEMPLATE


def build_prompt(slide: dict, direction: dict, slide_idx: int) -> str:
    """Compose the full text prompt for one slide."""
    tpl = _load_template()
    bullets = "\n".join(f"- {b}" for b in slide["bullets"])
    # Prefer the refined per-slide visual direction; fall back to the default.
    variation = slide.get("visual_direction") or VARIATION[
        min(slide_idx - 1, len(VARIATION) - 1)
    ]
    eyebrow = slide.get("eyebrow")
    prompt = tpl.format(
        brand=config.BRAND_NAME,
        site=config.BRAND_SITE,
        topic=slide["headline"],
        slide_n=slide_idx,
        total=3,
        headline=slide["headline"],
        subtitle=slide["subtitle"],
        bullets=bullets,
        takeaway=slide["takeaway"],
        source=slide["source_footer"],
        style=direction.get("style", ""),
        background=direction.get("background", ""),
        typography=direction.get("typography", ""),
        variation=variation,
        negative=NEGATIVE_PROMPT,
    )
    if eyebrow:
        prompt += f"\nTop eyebrow label (small, uppercase, letter-spaced): {eyebrow}\n"
    return prompt


def build_image_jobs(date: str, content_plan: dict, creative: dict) -> dict:
    """Return the list of Higgsfield generation jobs (one per slide)."""
    selected_name = creative["selected"]
    direction = next(d for d in creative["directions"]
                     if d["concept_name"] == selected_name)

    jobs = []
    for slide in content_plan["carousel_plan"]:
        idx = slide["slide"]
        jobs.append({
            "slide": idx,
            "model": IMAGE_MODEL_PRIMARY,
            "aspect_ratio": IMAGE_ASPECT_RATIO,
            "count": 1,
            "prompt": build_prompt(slide, direction, idx),
            "negative_prompt": NEGATIVE_PROMPT,
            "target_png": str(config.run_dir(date) / config.SLIDE_FILENAMES[idx - 1]),
            "target_jpg": str(config.run_dir(date) / config.SLIDE_JPEG_FILENAMES[idx - 1]),
            "regenerate_rule": ("On retry, change layout, background, visual "
                                "metaphor and accent color — produce a genuinely "
                                "different premium version, do not repeat."),
        })

    payload = {"date": date, "model": IMAGE_MODEL_PRIMARY,
               "negative_prompt": NEGATIVE_PROMPT, "jobs": jobs,
               "status": "jobs_built"}
    state.save_artifact(date, "images", payload)
    return payload


def postprocess(png_path: str | Path, jpg_path: str | Path) -> dict:
    """Convert a generated render to an Instagram-ready 1080x1350 JPEG.

    Returns a dict with the final path + dimensions + byte size, or raises if
    Pillow is unavailable.
    """
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Pillow is required for image post-processing: pip install pillow"
        ) from exc

    png_path, jpg_path = Path(png_path), Path(jpg_path)
    img = Image.open(png_path).convert("RGB")

    # Cover-fit to exactly 1080x1350 (crop overflow, never distort).
    target_ratio = IMAGE_TARGET_W / IMAGE_TARGET_H
    w, h = img.size
    if w / h > target_ratio:
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    else:
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        img = img.crop((0, top, w, top + new_h))
    img = img.resize((IMAGE_TARGET_W, IMAGE_TARGET_H), Image.LANCZOS)

    quality = IMAGE_JPEG_QUALITY
    img.save(jpg_path, "JPEG", quality=quality, optimize=True)
    while jpg_path.stat().st_size > IMAGE_MAX_BYTES and quality > 60:
        quality -= 5
        img.save(jpg_path, "JPEG", quality=quality, optimize=True)

    return {
        "path": str(jpg_path),
        "width": IMAGE_TARGET_W,
        "height": IMAGE_TARGET_H,
        "bytes": jpg_path.stat().st_size,
        "jpeg_quality": quality,
    }


_DEFAULT_TEMPLATE = """Create a premium Instagram carousel slide for {brand}, an Indian stock market research brand ({site}).

Canvas: 1080x1350 px, 4:5 Instagram carousel.
Brand: {brand} / {site}
Topic: {topic}
Slide: {slide_n} of {total}

Text content to render cleanly and legibly:
Headline: {headline}
Subtitle: {subtitle}
Bullets:
{bullets}
Takeaway: {takeaway}
Footer source (tiny): {source}
Footer brand (tiny): {brand} · {site}

Visual style: {style}. Background: {background}. Typography: {typography}.
Premium finance-editorial design, clean, modern, minimalist, strong typographic
hierarchy, generous whitespace, subtle data elements, professional Indian-market
research aesthetic. One main visual idea only. All text must be real, legible and
spelled correctly.

Composition for THIS slide: {variation}

Avoid: {negative}
"""
