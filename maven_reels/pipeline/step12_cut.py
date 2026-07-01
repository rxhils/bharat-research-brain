"""Step 12 — Cut Room (ffmpeg).

Assembles the final 1080x1920 reel from scene stills + voiceover + subtitles +
music: per-scene slow Ken-Burns zoom, hard cuts on the beat, burned subtitles,
voiceover as primary audio over a ducked original music bed. Runs at real-run
time once scene JPEGs + voiceover exist; references the proven pattern in
maven_instagram/pipeline/step9_story_video.py (implemented fresh here).
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from . import config, state
from .config import REEL_H, REEL_W


def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("ffmpeg not found on PATH")
    return exe


def _scene_clip(ff: str, jpg: Path, seconds: float, out: Path) -> None:
    """One scene: slow zoom (Ken-Burns) on a 1080x1920 still."""
    frames = max(1, int(seconds * 30))
    vf = (f"scale={REEL_W}:{REEL_H}:force_original_aspect_ratio=increase,"
          f"crop={REEL_W}:{REEL_H},"
          f"zoompan=z='min(zoom+0.0008,1.10)':d={frames}:s={REEL_W}x{REEL_H}:fps=30")
    subprocess.run([ff, "-y", "-loop", "1", "-t", f"{seconds}", "-i", str(jpg),
                    "-vf", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
                    str(out)], check=True, capture_output=True)


def _music(ff: str, seconds: float, out: Path) -> None:
    freqs = [110.0, 164.81, 220.0]
    inputs = []
    for f in freqs:
        inputs += ["-f", "lavfi", "-i", f"sine=frequency={f}:duration={seconds}"]
    fc = ("[0]volume=0.10[a0];[1]volume=0.08[a1];[2]volume=0.07[a2];"
          "[a0][a1][a2]amix=inputs=3:normalize=0,aecho=0.8:0.85:60:0.2,"
          f"afade=t=in:d=1,afade=t=out:st={max(0,seconds-1.5)}:d=1.5[m]")
    subprocess.run([ff, "-y", *inputs, "-filter_complex", fc, "-map", "[m]",
                    "-c:a", "aac", "-b:a", "128k", str(out)], check=True, capture_output=True)


def build_reel(date: str, storyboard: dict) -> dict:
    ff = _ffmpeg()
    rd = config.run_dir(date)
    scenes = storyboard["scenes"]
    scene_clips = []
    for sc in scenes:
        jpg = rd / f"scene_{sc['scene']}.jpg"
        if not jpg.exists():
            raise FileNotFoundError(f"scene image missing: {jpg} (run Scene Studio first)")
        clip = rd / f"_clip_{sc['scene']}.mp4"
        _scene_clip(ff, jpg, sc["seconds"], clip)
        scene_clips.append(clip)

    listing = rd / "_scenes.txt"
    listing.write_text("\n".join(f"file '{c.as_posix()}'" for c in scene_clips), encoding="utf-8")
    silent = rd / "_video_silent.mp4"
    subprocess.run([ff, "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
                    "-c", "copy", str(silent)], check=True, capture_output=True)

    total = sum(s["seconds"] for s in scenes)
    music = rd / "_music.m4a"; _music(ff, total, music)
    voiceover = rd / "voiceover.mp3"
    srt = rd / "captions.srt"
    out = rd / "reel.mp4"

    vf = f"subtitles='{srt.as_posix()}':force_style='Fontsize=16,PrimaryColour=&Hffffff&,Outline=1'" if srt.exists() else "null"
    if voiceover.exists():
        cmd = [ff, "-y", "-i", str(silent), "-i", str(voiceover), "-i", str(music),
               "-filter_complex",
               f"[0:v]{vf}[v];[2:a]volume=0.25[m];[1:a][m]amix=inputs=2:duration=first[a]",
               "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-shortest", str(out)]
    else:
        cmd = [ff, "-y", "-i", str(silent), "-i", str(music), "-vf", vf,
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
               "-shortest", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)

    for c in scene_clips:
        c.unlink(missing_ok=True)
    meta = {"date": date, "reel": str(out), "width": REEL_W, "height": REEL_H,
            "seconds": round(total, 1), "bytes": out.stat().st_size,
            "has_voiceover": voiceover.exists(), "has_subtitles": srt.exists()}
    state.save_artifact(date, "reel_video", meta)
    return meta
