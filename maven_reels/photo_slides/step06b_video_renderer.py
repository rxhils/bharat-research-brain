"""Agent 7 — Optional Reel MP4 Renderer (auto-publish mode ONLY).

NOT the default. Renders the 5 slides into a simple 1080x1920 crossfade
slideshow MP4 for API/Composio Reel publishing — used only when the operator
explicitly selects `slideshow_video_reel_auto`. No Remotion, no voiceover.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from . import config, state


class VideoRenderError(RuntimeError):
    pass


def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise VideoRenderError("ffmpeg not found on PATH")
    return exe


def run(job_id: str) -> dict:
    if not config.ALLOW_AUTO_REEL_VIDEO_MODE:
        raise VideoRenderError("ALLOW_AUTO_REEL_VIDEO_MODE is off — MP4 mode disabled")
    if config.DISABLE_REMOTION_FOR_REELS is False:  # honesty: we never use Remotion here
        pass

    design = state.load_artifact(job_id, "slide_design") or {}
    images = sorted(design.get("generated_images", []),
                    key=lambda i: i.get("slide_number", 0))
    paths = [Path(i["path"]) for i in images]
    if len(paths) != config.SLIDE_COUNT or not all(p.exists() for p in paths):
        raise VideoRenderError("need all 5 rendered slides before MP4 render")

    per, xf = config.VIDEO_SECONDS_PER_SLIDE, config.VIDEO_XFADE_SECONDS
    dest = state.job_dir(job_id) / f"reel_slideshow_{job_id}.mp4"

    cmd = [_ffmpeg(), "-y"]
    for p in paths:
        cmd += ["-loop", "1", "-t", f"{per}", "-i", str(p)]
    # chain of xfades: 5 stills -> 4 dissolves
    fc, prev = [], "[0:v]"
    offset = per - xf
    for i in range(1, len(paths)):
        out = f"[v{i}]"
        fc.append(f"{prev}[{i}:v]xfade=transition=fade:duration={xf}:"
                  f"offset={offset:.2f}{out}")
        prev = out
        offset += per - xf
    fc.append(f"{prev}format=yuv420p[vout]")
    cmd += ["-filter_complex", ";".join(fc), "-map", "[vout]",
            "-r", "30", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
            str(dest)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if proc.returncode != 0 or not dest.exists():
        raise VideoRenderError(f"ffmpeg failed: {proc.stderr[-400:]}")

    duration = round(len(paths) * per - (len(paths) - 1) * xf, 1)
    payload = {
        "mode": "slideshow_video_reel_auto",
        "video_path": str(dest),
        "width": config.SLIDE_W, "height": config.SLIDE_H,
        "duration_seconds": duration,
        "seconds_per_slide": per,
        "transitions": "crossfade",
        "voiceover": False,
        "renderer": "ffmpeg (no Remotion)",
        "status": "rendered",
        "generated_at": config.now_ist().isoformat(timespec="seconds"),
    }
    state.save_artifact(job_id, "video_render", payload)
    return payload
