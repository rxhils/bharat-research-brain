"""Step 9 — Scene Studio.

Builds a unique Higgsfield prompt per storyboard scene (9:16 premium background —
minimal/no baked text, since the Cut Room overlays crisp animated captions). The
generation itself runs on the Higgsfield MCP (nano_banana_pro) via the conductor;
this module builds the jobs and post-processes the returned frames to 1080x1920.
"""
from __future__ import annotations

from pathlib import Path

from . import config, state
from .config import IMAGE_ASPECT, IMAGE_MODEL, REEL_H, REEL_W

NEGATIVE = ("cheap AI look, cartoon, meme, random candlestick spam, fake logos, "
            "fake numbers, clutter, unreadable text, gibberish text, watermark, "
            "bull/bear mascots, buy/sell arrows, 3D coins, overdesigned")


def build_prompt(scene: dict, direction: dict) -> str:
    return (
        f"Vertical 9:16 (1080x1920) background frame for a premium Maven Indian-"
        f"market reel. Design system: {direction.get('background','dark navy')}; "
        f"{direction.get('typography','bold sans')}. Visual beat: {scene['visual_beat']} "
        f"Leave the lower third clean for captions. One main visual idea, deep "
        f"negative space, calm premium finance-editorial mood, dark theme. "
        f"Minimal or NO baked text (captions are added separately). "
        f"Avoid: {NEGATIVE}."
    )


def build_scene_jobs(date: str, storyboard: dict, visual_direction: dict) -> dict:
    direction = next((d for d in visual_direction["directions"]
                      if d["name"] == visual_direction["selected"]),
                     visual_direction["directions"][0])
    jobs = []
    rd = config.run_dir(date)
    for sc in storyboard["scenes"]:
        i = sc["scene"]
        jobs.append({
            "scene": i, "model": IMAGE_MODEL, "aspect_ratio": IMAGE_ASPECT,
            "seconds": sc["seconds"], "on_screen": sc["on_screen"],
            "prompt": build_prompt(sc, direction), "negative_prompt": NEGATIVE,
            "target_png": str(rd / f"scene_{i}.png"),
            "target_jpg": str(rd / f"scene_{i}.jpg"),
        })
    payload = {"date": date, "model": IMAGE_MODEL, "aspect_ratio": IMAGE_ASPECT,
               "jobs": jobs, "status": "jobs_built"}
    state.save_artifact(date, "scenes", payload)
    return payload


def postprocess(png_path: str | Path, jpg_path: str | Path) -> dict:
    from PIL import Image
    png_path, jpg_path = Path(png_path), Path(jpg_path)
    img = Image.open(png_path).convert("RGB")
    tr = REEL_W / REEL_H
    w, h = img.size
    if w / h > tr:
        nw = int(h * tr); left = (w - nw) // 2; img = img.crop((left, 0, left + nw, h))
    else:
        nh = int(w / tr); top = (h - nh) // 2; img = img.crop((0, top, w, top + nh))
    img = img.resize((REEL_W, REEL_H), Image.LANCZOS)
    img.save(jpg_path, "JPEG", quality=90, optimize=True)
    return {"path": str(jpg_path), "width": REEL_W, "height": REEL_H,
            "bytes": jpg_path.stat().st_size}
