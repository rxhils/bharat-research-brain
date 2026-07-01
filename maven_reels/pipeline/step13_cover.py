"""Step 13 — Cover Frame Studio.

A dedicated grid cover (cover.jpg): big hook, clean dark background, Maven
branding, one visual idea. Generated as its own Higgsfield still so the profile
grid looks premium even before the reel plays. Generation runs via the conductor.
"""
from __future__ import annotations

from . import config, state
from .config import BRAND_NAME, BRAND_SITE, IMAGE_MODEL


def build_cover_job(date: str, hooks: dict, visual_direction: dict) -> dict:
    hook = hooks["chosen"]["text"].rstrip(".?") + ""
    direction = visual_direction["selected"]
    prompt = (
        f"Vertical 9:16 (1080x1920) premium Instagram Reel COVER for {BRAND_NAME}, "
        f"an Indian stock market brand. Design system: {direction}, dark navy "
        f"background, deep negative space, one clean accent. ONE big bold hook "
        f"headline centered: \"{hook}\". Small {BRAND_NAME} · {BRAND_SITE} in the "
        f"footer. One visual idea, no clutter, no fake numbers, no logos, premium "
        f"finance-editorial. Avoid cheap AI look, cartoon, meme, candlestick spam."
    )
    payload = {"date": date, "model": IMAGE_MODEL, "aspect_ratio": "9:16",
               "hook": hook, "prompt": prompt,
               "target_jpg": str(config.run_dir(date) / "cover.jpg"),
               "status": "job_built"}
    state.save_artifact(date, "cover", payload)
    return payload
