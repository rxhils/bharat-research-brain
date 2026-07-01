"""Scan recent reel run folders (date- or job-id-named) for learning checks.

Used by the Duplicate Topic Check and the Visual Uniqueness Check. Read-only.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import config


def _load(d: Path, name: str) -> dict | None:
    p = d / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def recent_runs(exclude: str | None = None, limit: int = 10) -> list[dict]:
    """Most-recent-first list of {run_key, dir, viral_fit, template, variation,
    asset_picker, storyboard} for completed-ish runs (have a chosen story)."""
    root = config.OUTPUT_ROOT
    if not root.exists():
        return []
    dirs = [d for d in root.iterdir() if d.is_dir() and d.name != exclude]
    dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    out = []
    for d in dirs[: limit * 2]:
        vf = _load(d, "02_viral_fit.json")
        if not vf:
            continue
        out.append({
            "run_key": d.name, "dir": str(d), "viral_fit": vf,
            "template": _load(d, "07_template.json"),
            "variation": _load(d, "08_motion_variation.json"),
            "asset_picker": _load(d, "09_asset_picker.json"),
            "storyboard": _load(d, "07_storyboard.json"),
        })
        if len(out) >= limit:
            break
    return out


def chosen_headline(vf: dict) -> str:
    c = vf.get("chosen") or {}
    story = c.get("story") or vf.get("selected_story") or {}
    return str(story.get("headline", ""))
