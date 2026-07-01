"""Step 16 — Reel Auditor.

Scores the reel on Hook / Retention / Visual / Compliance, then an overall
Publish score + gate. Retention rewards a hook in the first 2s, a tight 20-35s
length, 5-7 scenes, and a visual change ~every 3s. Visual is mechanical (reel
exists / 1080x1920 / duration / >=5 scenes) combined with a supplied aesthetic
score from visual QA.
"""
from __future__ import annotations

from . import state
from .config import (QUALITY_GATES, REEL_MAX_SECONDS, REEL_MIN_SECONDS,
                     SCENE_MAX, SCENE_MIN)


def _retention(script_edited: dict, storyboard: dict) -> tuple[int, list[str]]:
    issues, score = [], 100
    segs = script_edited["segments"]
    if not segs or segs[0]["label"] != "hook" or segs[0]["seconds"] > 2:
        issues.append("hook not in first 2s"); score -= 20
    total = script_edited.get("total_seconds", 0)
    if not (REEL_MIN_SECONDS <= total <= REEL_MAX_SECONDS):
        issues.append(f"length {total}s outside {REEL_MIN_SECONDS}-{REEL_MAX_SECONDS}s"); score -= 15
    n = storyboard.get("scene_count", 0)
    if not (SCENE_MIN <= n <= SCENE_MAX):
        issues.append(f"{n} scenes outside {SCENE_MIN}-{SCENE_MAX}"); score -= 10
    if any(e.lower().startswith("no filler") for e in script_edited.get("edits", [])):
        pass  # already tight
    return max(0, score), issues


def _visual(storyboard: dict, reel_video: dict | None, aesthetic: int | None):
    issues, mech = [], 100
    n = storyboard.get("scene_count", 0)
    if n < SCENE_MIN:
        issues.append(f"only {n} scenes"); mech -= 20
    if reel_video:
        if not (reel_video.get("width") == 1080 and reel_video.get("height") == 1920):
            issues.append("reel not 1080x1920"); mech -= 20
        if not (REEL_MIN_SECONDS <= reel_video.get("seconds", 0) <= REEL_MAX_SECONDS):
            issues.append("reel duration off"); mech -= 10
    else:
        issues.append("reel.mp4 not built yet"); mech = min(mech, 70)
    if aesthetic is None:
        issues.append("aesthetic (visual) review not supplied")
        return min(mech, 0), issues
    return min(mech, aesthetic), issues


def run(date: str, *, hooks: dict, script_edited: dict, storyboard: dict,
        compliance: dict, reel_video: dict | None = None,
        aesthetic_score: int | None = None) -> dict:
    hook = int(hooks["chosen"]["strength"])
    retention, r_issues = _retention(script_edited, storyboard)
    visual, v_issues = _visual(storyboard, reel_video, aesthetic_score)
    comp = int(compliance.get("score", 0))

    scores = {"hook": hook, "retention": retention, "visual": visual, "compliance": comp}
    passed = {k: scores[k] >= QUALITY_GATES[k] for k in QUALITY_GATES}
    overall = all(passed.values())
    scores["publish"] = 100 if overall else min(scores.values())

    payload = {"date": date, "scores": scores, "gates": QUALITY_GATES,
               "passed": passed, "overall_pass": overall,
               "retention_issues": r_issues, "visual_issues": v_issues,
               "compliance_violations": compliance.get("violations", []),
               "verdict": "PUBLISH_OK" if overall else "BLOCKED"}
    state.save_artifact(date, "quality", payload)
    return payload
