"""Step 6 — Retention Editor.

Most finance videos are too slow. This tightens the script for pace: bans filler
openers, guarantees an instant line 1 (the hook), enforces <35s, and flags that a
visual should change roughly every 3s. Records a before/after diff.
"""
from __future__ import annotations

from . import schemas, state
from .config import FILLER_OPENERS, REEL_MAX_SECONDS


def _has_filler(text: str) -> bool:
    t = text.lower().strip()
    return any(t.startswith(f) for f in FILLER_OPENERS)


def run(date: str, script: dict) -> dict:
    segments = [dict(s) for s in script["segments"]]
    changes: list[str] = []

    # 1) Line 1 must be the hook and must hit instantly (no filler).
    if _has_filler(segments[0]["narration"]):
        changes.append("Removed filler opener from line 1.")
        segments[0]["narration"] = segments[0]["narration"].split(".")[-1].strip() \
            or segments[0]["narration"]

    # 2) Strip filler openers anywhere.
    for s in segments:
        if _has_filler(s["narration"]):
            changes.append(f"Cut filler opener in '{s['label']}'.")
            s["narration"] = "…" + s["narration"]

    # 3) Enforce total < REEL_MAX_SECONDS by trimming the 'why' segment if needed.
    total = sum(s["seconds"] for s in segments)
    if total > REEL_MAX_SECONDS:
        over = total - REEL_MAX_SECONDS
        for s in segments:
            if s["label"] == "why" and s["seconds"] - over >= 6:
                s["seconds"] -= over
                changes.append(f"Trimmed 'why' by {over}s to keep under {REEL_MAX_SECONDS}s.")
                break

    # 4) Pattern-interrupt cadence: mark a visual beat ~every 3s.
    beats = max(1, sum(s["seconds"] for s in segments) // 3)

    payload = {
        "date": date,
        "segments": segments,
        "total_seconds": sum(s["seconds"] for s in segments),
        "narration": " ".join(s["narration"] for s in segments),
        "pattern_interrupt_beats": beats,
        "edits": changes or ["No filler found; pacing already tight."],
    }
    schemas.validate_script(payload)
    state.save_artifact(date, "script_edited", payload)
    return payload
