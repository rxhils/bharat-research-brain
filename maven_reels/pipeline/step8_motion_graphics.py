"""Step 8 (upgraded) — Motion Graphics Engine (Remotion).

Turns the Motion Storyboard into a real animated 1080x1920 reel via a Remotion
composition (kinetic typography, number counters, chart reveals, staggered
chips, kinetic subtitles, brand + progress chrome), then muxes the voiceover
over a ducked ffmpeg music bed. This replaces the Ken-Burns slideshow.

Remotion renders a SILENT motion video; ffmpeg adds audio + extracts the cover.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from . import config, state, step_sound_design

REMOTION_DIR = Path(__file__).resolve().parent.parent / "remotion"
FPS = 30
W, H = 1080, 1920


def _fresh_video_clip_for_scene(date: str, scene_num: int) -> str | None:
    """Primary background source: a completed Fresh Video Mode clip for this
    scene (see step_fresh_video_scenes.py). Only used if actually on disk."""
    try:
        spec = state.load_artifact(date, "fresh_video_scenes")
    except FileNotFoundError:
        return None
    for r in spec.get("results", []):
        if r.get("scene") == scene_num and r.get("status") == "completed":
            clip = config.run_dir(date) / r.get("clip_path", "")
            if clip.exists():
                return clip.name  # staged flat into remotion/public/run/
    return None


def build_props(date: str, storyboard: dict, subtitles: list[dict]) -> dict:
    assets_dir = config.run_dir(date) / "assets"
    scenes = []
    for s in storyboard["scenes"]:
        sc = {"start": s["start"], "duration": s["duration"], "kind": s["kind"]}
        for k in ("title", "label", "value", "suffix", "sub", "chips", "text", "points", "accent"):
            if s.get(k) not in (None, "", []):
                sc[k] = s[k]
        clip = _fresh_video_clip_for_scene(date, s["scene"])
        if clip:
            sc["bg_video"] = clip   # PRIMARY: fresh Higgsfield video
        else:
            asset = s.get("asset")
            if asset and (assets_dir / f"{asset}.jpg").exists():
                sc["bg"] = f"{asset}.jpg"   # FALLBACK 1: static library plate
        scenes.append(sc)
    return {"fps": FPS, "durationSeconds": round(storyboard["total_duration"], 2),
            "brand": {"name": config.BRAND_NAME, "site": config.BRAND_SITE},
            "theme": {"accent": storyboard.get("accent_color", "#22D3EE")},
            "template": storyboard.get("template"),
            "variation": storyboard.get("variation_id"),
            "scenes": scenes, "subtitles": subtitles}


def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("ffmpeg not found")
    return exe


def _music(ff: str, seconds: float, rd: Path) -> Path:
    out = rd / "music_bed.mp3"
    freqs = [110.0, 164.81, 220.0]
    inputs: list[str] = []
    for f in freqs:
        inputs += ["-f", "lavfi", "-i", f"sine=frequency={f}:duration={seconds}"]
    fc = ("[0]volume=0.09[a0];[1]volume=0.07[a1];[2]volume=0.06[a2];"
          "[a0][a1][a2]amix=inputs=3:normalize=0,aecho=0.8:0.85:55:0.18,"
          f"afade=t=in:d=0.8,afade=t=out:st={max(0, seconds - 1.2)}:d=1.2[m]")
    subprocess.run([ff, "-y", *inputs, "-filter_complex", fc, "-map", "[m]",
                    "-c:a", "mp3", "-b:a", "128k", str(out)], check=True, capture_output=True)
    return out


def _stage_assets(date: str) -> int:
    """Copy this run's background plates AND any Fresh Video Mode clips into
    remotion/public/run/ so the composition can load them via staticFile()."""
    rd = config.run_dir(date)
    dst = REMOTION_DIR / "public" / "run"
    if dst.exists():
        shutil.rmtree(dst, ignore_errors=True)
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    plates = rd / "assets"
    if plates.exists():
        for jpg in plates.glob("*.jpg"):
            shutil.copy2(jpg, dst / jpg.name); n += 1
    clips = rd / "fresh_video"
    if clips.exists():
        for mp4 in clips.glob("*.mp4"):
            shutil.copy2(mp4, dst / mp4.name); n += 1
    return n


def render_video(date: str, props: dict) -> Path:
    """Run the Remotion CLI to render a silent motion video."""
    rd = config.run_dir(date)
    rd.mkdir(parents=True, exist_ok=True)
    _stage_assets(date)
    props_path = rd / "_remotion_props.json"
    props_path.write_text(json.dumps(props), encoding="utf-8")
    out = rd / "_motion_silent.mp4"
    npx = shutil.which("npx") or "npx"
    subprocess.run(
        [npx, "remotion", "render", "src/index.ts", "MavenReel", str(out),
         f"--props={props_path}", "--log=error", "--concurrency=2"],
        check=True, capture_output=True, cwd=str(REMOTION_DIR), timeout=900)
    return out


def build_reel(date: str, storyboard: dict, subtitles: list[dict],
               voiceover_mp3: str | None = None) -> dict:
    rd = config.run_dir(date)
    ff = _ffmpeg()
    props = build_props(date, storyboard, subtitles)
    silent = render_video(date, props)

    seconds = props["durationSeconds"]
    # Sound Design Desk: music + SFX pre-mixed into one bed (falls back to plain music).
    try:
        bed = Path(step_sound_design.build_bed(date, storyboard, seconds)["sound_bed"])
    except Exception:
        bed = _music(ff, seconds, rd)
    vo = Path(voiceover_mp3) if voiceover_mp3 else (rd / "voiceover.mp3")
    out = rd / "reel.mp4"

    if vo.exists():
        # voiceover primary; sound bed ducked under it
        cmd = [ff, "-y", "-i", str(silent), "-i", str(vo), "-i", str(bed),
               "-filter_complex", "[2:a]volume=0.5[m];[1:a][m]amix=inputs=2:duration=first[a]",
               "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac",
               "-b:a", "160k", "-shortest", str(out)]
    else:
        cmd = [ff, "-y", "-i", str(silent), "-i", str(bed), "-map", "0:v",
               "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-shortest", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)

    # cover = a strong frame near the hook peak
    cover = rd / "cover.jpg"
    subprocess.run([ff, "-y", "-ss", "1.0", "-i", str(out), "-frames:v", "1",
                    "-q:v", "3", str(cover)], check=True, capture_output=True)

    silent.unlink(missing_ok=True)
    meta = {"date": date, "reel": str(out), "cover": str(cover), "renderer": "remotion",
            "width": W, "height": H, "fps": FPS, "seconds": round(seconds, 1),
            "scene_count": storyboard["scene_count"], "bytes": out.stat().st_size,
            "has_voiceover": vo.exists(), "has_subtitles": bool(subtitles)}
    state.save_artifact(date, "reel_video", meta)
    return meta
