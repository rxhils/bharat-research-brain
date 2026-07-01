"""Step 12 — Cut Room (ffmpeg).

Assembles the final 1080x1920 reel from scene stills + voiceover + subtitles +
music in a SINGLE fast pass: the concat demuxer holds each still for its scene
duration, then one filter_complex scales/crops, burns subtitles, and mixes the
voiceover over a ducked music bed. Runs with the run directory as cwd so all
paths are relative — which also sidesteps the Windows `subtitles=` drive-letter
escaping gotcha.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from . import config, state
from .config import REEL_H, REEL_W

SUB_STYLE = ("FontName=Arial,Fontsize=15,Bold=1,PrimaryColour=&H00FFFFFF,"
             "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,"
             "Alignment=2,MarginV=90")


def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("ffmpeg not found on PATH")
    return exe


def _music(ff: str, seconds: float, rd: Path) -> str:
    """Original calm ambient bed via ffmpeg sines (fast). Returns filename."""
    out = "_music.m4a"
    freqs = [110.0, 164.81, 220.0]
    inputs = []
    for f in freqs:
        inputs += ["-f", "lavfi", "-i", f"sine=frequency={f}:duration={seconds}"]
    fc = ("[0]volume=0.10[a0];[1]volume=0.08[a1];[2]volume=0.07[a2];"
          "[a0][a1][a2]amix=inputs=3:normalize=0,aecho=0.8:0.85:60:0.2,"
          f"afade=t=in:d=1,afade=t=out:st={max(0, seconds - 1.5)}:d=1.5[m]")
    subprocess.run([ff, "-y", *inputs, "-filter_complex", fc, "-map", "[m]",
                    "-c:a", "aac", "-b:a", "128k", out], check=True,
                   capture_output=True, cwd=str(rd))
    return out


def build_reel(date: str, storyboard: dict) -> dict:
    ff = _ffmpeg()
    rd = config.run_dir(date)
    scenes = storyboard["scenes"]
    for sc in scenes:
        if not (rd / f"scene_{sc['scene']}.jpg").exists():
            raise FileNotFoundError(f"scene image missing: scene_{sc['scene']}.jpg")

    # concat list (relative filenames), each still held for its scene duration
    lines = []
    for sc in scenes:
        lines.append(f"file 'scene_{sc['scene']}.jpg'")
        lines.append(f"duration {sc['seconds']}")
    lines.append(f"file 'scene_{scenes[-1]['scene']}.jpg'")  # concat demuxer needs last repeated
    (rd / "_scenes.txt").write_text("\n".join(lines), encoding="utf-8")

    total = sum(s["seconds"] for s in scenes)
    _music(ff, total, rd)

    has_vo = (rd / "voiceover.mp3").exists()
    has_srt = (rd / "captions.srt").exists()
    vf = (f"scale={REEL_W}:{REEL_H}:force_original_aspect_ratio=increase,"
          f"crop={REEL_W}:{REEL_H},fps=30,format=yuv420p")
    if has_srt:
        vf += f",subtitles=captions.srt:force_style='{SUB_STYLE}'"

    cmd = [ff, "-y", "-f", "concat", "-safe", "0", "-i", "_scenes.txt"]
    if has_vo:
        cmd += ["-i", "voiceover.mp3"]
    cmd += ["-i", "_music.m4a"]
    music_idx = 2 if has_vo else 1
    if has_vo:
        fc = f"[0:v]{vf}[v];[{music_idx}:a]volume=0.22[m];[1:a][m]amix=inputs=2:duration=first[a]"
        maps = ["-map", "[v]", "-map", "[a]"]
    else:
        fc = f"[0:v]{vf}[v]"
        maps = ["-map", "[v]", "-map", f"{music_idx}:a"]
    cmd += ["-filter_complex", fc, *maps, "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "26", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
            "-r", "30", "-shortest", "reel.mp4"]
    subprocess.run(cmd, check=True, capture_output=True, cwd=str(rd))

    out = rd / "reel.mp4"
    meta = {"date": date, "reel": str(out), "width": REEL_W, "height": REEL_H,
            "seconds": round(total, 1), "bytes": out.stat().st_size,
            "has_voiceover": has_vo, "has_subtitles": has_srt}
    state.save_artifact(date, "reel_video", meta)
    return meta
