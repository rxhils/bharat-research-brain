"""Step — Scene Quality Inspector.

Checks every generated Higgsfield clip BEFORE final assembly: exists, playable,
vertical, sane duration, not frozen/static, not a duplicate of another shot.
All checks are local (ffprobe/ffmpeg) — free. A failed shot is marked for
single-scene regeneration; it never silently ships and never forces a full
pipeline rerun.

Gate: overall_scene_quality_score >= 85.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from . import config, state

GATE = 85


def _ffprobe(path: Path) -> dict | None:
    exe = shutil.which("ffprobe")
    if not exe:
        return None
    try:
        out = subprocess.run(
            [exe, "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=width,height,nb_frames,avg_frame_rate:format=duration",
             "-of", "json", str(path)],
            capture_output=True, text=True, timeout=60, check=True).stdout
        return json.loads(out)
    except Exception:
        return None


def _freeze_seconds(path: Path) -> float:
    """Total seconds of frozen (static) video detected by ffmpeg freezedetect."""
    exe = shutil.which("ffmpeg")
    if not exe:
        return 0.0
    try:
        err = subprocess.run(
            [exe, "-i", str(path), "-vf", "freezedetect=n=0.002:d=1",
             "-map", "0:v:0", "-f", "null", "-"],
            capture_output=True, text=True, timeout=120).stderr
        return sum(float(m) for m in re.findall(r"freeze_duration:\s*([\d.]+)", err))
    except Exception:
        return 0.0


def _first_frame_signature(path: Path) -> str:
    """Tiny grayscale thumbprint of the first frame (for duplicate detection)."""
    exe = shutil.which("ffmpeg")
    if not exe:
        return ""
    try:
        out = subprocess.run(
            [exe, "-i", str(path), "-frames:v", "1", "-vf", "scale=8:8,format=gray",
             "-f", "rawvideo", "-"],
            capture_output=True, timeout=60).stdout
        return out.hex()
    except Exception:
        return ""


def _hamming_close(a: str, b: str) -> bool:
    if not a or not b or len(a) != len(b):
        return False
    diff = sum(1 for x, y in zip(bytes.fromhex(a), bytes.fromhex(b)) if abs(x - y) > 16)
    return diff < 8  # near-identical first frames


def run(date: str, *, scene_generation: dict) -> dict:
    run_dir = config.run_dir(date)
    planned = scene_generation.get("planned", [])
    signatures: dict[str, str] = {}
    results = []

    for p in planned:
        shot_id = p["shot_id"]
        clip = run_dir / p["clip_path"]
        issues, score = [], 100

        if not clip.exists():
            results.append({"shot_id": shot_id, "passed": False, "score": 0,
                            "issues": ["clip file missing"],
                            "recommendation": "generate (or regenerate) this scene"})
            continue

        meta = _ffprobe(clip)
        if not meta or not meta.get("streams"):
            results.append({"shot_id": shot_id, "passed": False, "score": 0,
                            "issues": ["clip unreadable / failed generation"],
                            "recommendation": "regenerate this scene"})
            continue

        s = meta["streams"][0]
        w, h = int(s.get("width", 0)), int(s.get("height", 0))
        dur = float(meta.get("format", {}).get("duration", 0))
        if h <= w:
            score -= 30; issues.append(f"not vertical ({w}x{h})")
        if not (1.5 <= dur <= 13.0):
            score -= 20; issues.append(f"duration {dur:.1f}s outside sane range")

        frozen = _freeze_seconds(clip)
        if dur and frozen / dur > 0.6:
            score -= 25; issues.append(f"mostly static ({frozen:.1f}s of {dur:.1f}s frozen)")
        elif dur and frozen / dur > 0.3:
            score -= 10; issues.append("noticeably static movement")

        sig = _first_frame_signature(clip)
        for other_id, other_sig in signatures.items():
            if _hamming_close(sig, other_sig):
                score -= 20; issues.append(f"near-duplicate of {other_id}")
                break
        signatures[shot_id] = sig

        results.append({
            "shot_id": shot_id, "passed": score >= GATE, "score": max(0, score),
            "issues": issues,
            "recommendation": ("ok" if score >= GATE else
                               "regenerate with a stronger, more distinct motion prompt"),
        })

    overall = round(sum(r["score"] for r in results) / len(results)) if results else 0
    payload = {
        "date": date, "scene_quality": results,
        "overall_scene_quality_score": overall,
        "gate": GATE, "passed": overall >= GATE and all(r["passed"] for r in results),
        "failed_shots": [r["shot_id"] for r in results if not r["passed"]],
        "note": "Failed shots are regenerated individually — never a full pipeline rerun.",
    }
    state.save_artifact(date, "scene_quality", payload)
    return payload
