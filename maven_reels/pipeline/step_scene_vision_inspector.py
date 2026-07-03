"""Agent — Scene Vision Inspector (Maven Reels Newsroom). Local, free.

Editor-in-Chief cannot tell abstract-vs-realistic footage from artifacts alone.
This step extracts REAL frames from every generated clip so a vision-capable
reviewer can actually look. The backend has no vision model, so it extracts the
frames and marks vision_review_required=true — it NEVER fakes a visual verdict.
A vision reviewer (a live Claude chat, or a configured vision API) fills in the
scores later via record_vision_review().

Writes scene_vision_inspection.json.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from . import config, state

FRAMES_DIR = "vision_frames"


def _ffmpeg() -> str | None:
    return shutil.which("ffmpeg")


def _extract(ff: str, clip: Path, out_dir: Path, shot_id: str, dur: float) -> list[str]:
    """1–3 representative frames (start / mid / near-end) as jpgs."""
    out_dir.mkdir(parents=True, exist_ok=True)
    stamps = [0.3] if dur < 2.0 else [0.3, dur / 2, max(0.3, dur - 0.4)]
    frames = []
    for i, t in enumerate(stamps):
        dst = out_dir / f"{shot_id}_f{i}.jpg"
        try:
            subprocess.run([ff, "-y", "-ss", f"{t:.2f}", "-i", str(clip),
                            "-frames:v", "1", "-q:v", "3", str(dst)],
                           check=True, capture_output=True, timeout=60)
            if dst.exists() and dst.stat().st_size > 0:
                frames.append(f"{FRAMES_DIR}/{dst.name}")
        except Exception:
            continue
    return frames


def run(date: str, *, scene_generation: dict | None = None) -> dict:
    rd = config.run_dir(date)
    ff = _ffmpeg()
    scene_generation = scene_generation or _opt(date, "scene_generation") or {}
    clips = scene_generation.get("clips") or scene_generation.get("planned") or []
    out_dir = rd / FRAMES_DIR

    reviews, all_frames = [], []
    for c in clips:
        shot_id = c.get("shot_id")
        clip = rd / c.get("clip_path", f"higgsfield_clips/{shot_id}.mp4")
        frames = _extract(ff, clip, out_dir, shot_id, float(c.get("duration") or 4.0)) if (ff and clip.exists()) else []
        all_frames += frames
        reviews.append({
            "scene_id": shot_id,
            "frames": frames,
            "footage_type": c.get("footage_type"),
            "clip_exists": clip.exists(),
            # honest: no backend vision model -> scores pending a real review
            "realism_score": None,
            "visual_relevance_score": None,
            "ai_slop_risk": None,
            "fake_text_detected": None,
            "issues": (["awaiting vision review"] if frames else
                       ["clip missing — nothing to inspect"]),
            "passed": None,
        })

    payload = {
        "date": date,
        "vision_review_available": False,  # backend has no vision model
        "vision_review_required": bool(all_frames),
        "frames_extracted": all_frames,
        "frames_dir": FRAMES_DIR,
        "scene_reviews": reviews,
        "overall_passed": None,   # pending real vision review
        "reroute_to": "",
        "note": ("Frames extracted for review. A vision-capable reviewer (a live "
                 "Claude Code chat or a configured vision API) must score realism / "
                 "fake-text / relevance via record_vision_review(); the backend never "
                 "fakes a visual verdict."),
    }
    state.save_artifact(date, "scene_vision", payload)
    return payload


def record_vision_review(date: str, scene_reviews: list[dict]) -> dict:
    """A vision reviewer fills in per-scene realism / relevance / fake-text /
    passed. Recomputes overall_passed + reroute. Each review:
    {scene_id, realism_score, visual_relevance_score, ai_slop_risk,
     fake_text_detected, issues, passed}."""
    cur = state.load_artifact(date, "scene_vision")
    by_id = {r["scene_id"]: r for r in cur.get("scene_reviews", [])}
    for rv in scene_reviews:
        by_id.get(rv.get("scene_id"), {}).update(rv)
    reviews = list(by_id.values())
    fake = [r["scene_id"] for r in reviews if r.get("fake_text_detected")]
    failed = [r["scene_id"] for r in reviews if r.get("passed") is False]
    cur.update(
        vision_review_available=True, vision_review_required=False,
        scene_reviews=reviews,
        fake_text_scenes=fake, failed_scenes=failed,
        overall_passed=(not failed and not fake),
        reroute_to=("scene_generator" if (failed or fake) else ""),
    )
    state.save_artifact(date, "scene_vision", cur)
    return cur


def _opt(date: str, key: str) -> dict | None:
    try:
        return state.load_artifact(date, key)
    except Exception:
        return None
