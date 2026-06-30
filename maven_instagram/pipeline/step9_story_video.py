"""Step 9 — Build a 9:16 Story video (with clean music) from the 3 slides.

Why this exists: Instagram's publishing API cannot attach its licensed music
library to posts, and feed photo carousels carry no audio. The automatable,
license-safe way to put "clean nice music" on the account is a short Story
*video* with an ORIGINAL, royalty-free ambient track baked in.

This module:
  1. Composites each 1080x1350 slide onto a 1080x1920 navy Story canvas (PIL).
  2. Synthesizes a calm ~15s ambient pad with ffmpeg `sine` sources (original
     audio — no copyright/licensing exposure).
  3. Muxes frames + audio into an H.264 MP4 that Instagram accepts as a Story.

Requires: ffmpeg on PATH, Pillow. No third-party audio is downloaded.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from . import config, state

STORY_W, STORY_H = 1080, 1920
SECONDS_PER_SLIDE = 5
NAVY = (11, 18, 32)            # #0B1220
GREY = (154, 167, 184)        # #9AA7B8


def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("ffmpeg not found on PATH — required for the Story video")
    return exe


def _build_frames(date: str, slide_jpgs: list[Path]) -> list[Path]:
    from PIL import Image, ImageDraw, ImageFont

    rd = config.run_dir(date)
    frames: list[Path] = []
    try:
        font = ImageFont.truetype("arialbd.ttf", 30)
        small = ImageFont.truetype("arial.ttf", 26)
    except Exception:
        font = small = ImageFont.load_default()

    for i, sp in enumerate(slide_jpgs, start=1):
        canvas = Image.new("RGB", (STORY_W, STORY_H), NAVY)
        slide = Image.open(sp).convert("RGB")
        # Slides are 1080x1350; center vertically with navy bands top/bottom.
        y = (STORY_H - slide.height) // 2
        canvas.paste(slide, (0, y))
        draw = ImageDraw.Draw(canvas)
        top = "MAVEN  ·  DAILY MARKET DIGEST"
        draw.text((60, 120), top, font=small, fill=GREY)
        bottom = "Full breakdown in our latest post  →  trymaven.in"
        draw.text((60, STORY_H - 150), bottom, font=small, fill=GREY)
        fp = rd / f"story_frame_{i}.png"
        canvas.save(fp)
        frames.append(fp)
    return frames


def _build_music(date: str, seconds: int) -> Path:
    """Synthesize a calm, original A-major7 ambient pad via ffmpeg sines."""
    rd = config.run_dir(date)
    out = rd / "story_music.m4a"
    # A2, E3, A3, C#4 — soft, warm, with slow tremolo, echo space, gentle fades.
    freqs = [110.00, 164.81, 220.00, 277.18]
    inputs: list[str] = []
    for f in freqs:
        inputs += ["-f", "lavfi", "-i", f"sine=frequency={f}:duration={seconds}"]
    fc = (
        "[0]volume=0.16,tremolo=f=0.18:d=0.4[a0];"
        "[1]volume=0.13[a1];[2]volume=0.12[a2];[3]volume=0.10[a3];"
        "[a0][a1][a2][a3]amix=inputs=4:normalize=0,"
        "aecho=0.8:0.85:70:0.25,highpass=f=70,lowpass=f=6500,"
        f"afade=t=in:d=2,afade=t=out:st={max(0, seconds-2)}:d=2,"
        "volume=2.2[aout]"
    )
    cmd = [_ffmpeg(), "-y", *inputs, "-filter_complex", fc,
           "-map", "[aout]", "-c:a", "aac", "-b:a", "160k", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)
    return out


def build_story_video(date: str, slide_jpgs: list[str | Path] | None = None) -> dict:
    rd = config.run_dir(date)
    if slide_jpgs is None:
        slide_jpgs = [rd / fn for fn in config.SLIDE_JPEG_FILENAMES]
    slide_jpgs = [Path(p) for p in slide_jpgs]
    seconds = SECONDS_PER_SLIDE * len(slide_jpgs)

    frames = _build_frames(date, slide_jpgs)
    music = _build_music(date, seconds)

    # Concat-demuxer list with per-frame durations.
    listing = rd / "story_frames.txt"
    lines = []
    for fp in frames:
        lines.append(f"file '{fp.as_posix()}'")
        lines.append(f"duration {SECONDS_PER_SLIDE}")
    lines.append(f"file '{frames[-1].as_posix()}'")  # last frame held
    listing.write_text("\n".join(lines), encoding="utf-8")

    out = rd / "story.mp4"
    cmd = [_ffmpeg(), "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
           "-i", str(music), "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-r", "30", "-c:a", "aac", "-b:a", "160k", "-shortest",
           "-t", str(seconds), str(out)]
    subprocess.run(cmd, check=True, capture_output=True)

    meta = {
        "date": date,
        "story_video": str(out),
        "music": str(music),
        "width": STORY_W,
        "height": STORY_H,
        "seconds": seconds,
        "bytes": out.stat().st_size if out.exists() else 0,
        "music_note": "Original royalty-free ambient pad synthesized with ffmpeg "
                      "sine sources. No third-party / licensed audio used.",
    }
    state.save_artifact(date, "story", meta)
    return meta
