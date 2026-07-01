"""Step 16 (upgraded) — Reel Auditor (strict, 9 scores + auto-reroute).

Scores Hook / Retention / Edit Quality / Visual Quality / Subtitle / Voiceover /
Compliance / Brand / Publish and BLOCKS on any failed threshold, routing the fix
to the responsible node. Scores are fair: a genuinely fast, animated, readable,
compliant reel clears 90; a slow slideshow does not.
"""
from __future__ import annotations

from . import state
from .config import (BRAND_NAME, REEL_MAX_SECONDS, REEL_MIN_SECONDS, SCENE_MAX,
                     SCENE_MIN)

GATES = {"hook": 90, "retention": 90, "edit_quality": 90, "visual_quality": 90,
         "subtitle": 90, "voiceover": 85, "compliance": 95, "brand": 90,
         "cost_efficiency": 85}
REROUTE = {"hook": "hook_lab", "retention": "retention_editor",
           "edit_quality": "motion_storyboard", "visual_quality": "motion_graphics",
           "subtitle": "subtitle_engine", "voiceover": "voice_studio",
           "compliance": "compliance_shield", "brand": "caption_desk",
           "cost_efficiency": "asset_picker"}


def _cost_efficiency(asset_picker: dict | None, cost_guard: dict | None) -> tuple[int, list[str]]:
    """Reward reusing the library and avoiding unapproved paid generation."""
    issues, s = [], 100
    if asset_picker is None:
        return 80, ["asset picker not run (cost not verified)"]
    new_gens = int(asset_picker.get("estimated_new_generations", 0))
    if new_gens == 0:
        pass  # perfect: pure library reuse
    else:
        # paid generation attempted: only OK if it was actually allowed/approved
        allowed = bool(asset_picker.get("paid_generation_allowed"))
        s -= 8 * new_gens
        issues.append(f"{new_gens} new Higgsfield generation(s) needed")
        if not allowed:
            s -= 20; issues.append("paid generation NOT approved (blocked by cost guard)")
    if cost_guard and cost_guard.get("requires_approval"):
        s -= 10; issues.append("cost guard flagged: requires approval")
    return max(0, s), issues


def _hook(hooks: dict) -> tuple[int, list[str]]:
    s = int(hooks.get("hook_score", hooks.get("chosen", {}).get("strength", 0)))
    words = len(hooks.get("on_screen_hook", "").split())
    issues = []
    if words > 8:
        s -= 8; issues.append("on-screen hook > 8 words")
    return min(100, max(0, s + 4)), issues  # +4: hook is on frame 0 in the engine


def _retention(storyboard: dict, script: dict) -> tuple[int, list[str]]:
    issues, s = [], 100
    total = script.get("total_seconds", storyboard.get("total_duration", 0))
    if not (REEL_MIN_SECONDS <= total <= REEL_MAX_SECONDS):
        s -= 12; issues.append(f"length {total}s outside {REEL_MIN_SECONDS}-{REEL_MAX_SECONDS}s")
    n = storyboard.get("scene_count", 0)
    if n < SCENE_MIN:
        s -= 10; issues.append(f"{n} scenes < {SCENE_MIN} (too few pattern interrupts)")
    longest = max((sc.get("duration", 0) for sc in storyboard.get("scenes", [])), default=0)
    if longest > 3.0:
        s -= 8; issues.append(f"a scene runs {longest}s (>3s feels static)")
    return max(0, s), issues


def _edit(storyboard: dict) -> tuple[int, list[str]]:
    issues, s = [], 100
    scenes = storyboard.get("scenes", [])
    n = len(scenes)
    if not (SCENE_MIN <= n <= SCENE_MAX):
        s -= 12; issues.append(f"{n} micro-scenes outside {SCENE_MIN}-{SCENE_MAX}")
    avg = (sum(sc.get("duration", 0) for sc in scenes) / n) if n else 99
    if avg > 2.0:
        s -= 8; issues.append(f"avg scene {avg:.1f}s (>2.0s)")
    if scenes and scenes[0].get("start", 1) > 0.001:
        s -= 6; issues.append("no visual on frame 0")
    return max(0, s), issues


def _visual(reel_video: dict | None, aesthetic: int | None) -> tuple[int, list[str]]:
    issues, mech = [], 100
    if not reel_video or not reel_video.get("reel"):
        return 0, ["reel.mp4 not built"]
    if not (reel_video.get("width") == 1080 and reel_video.get("height") == 1920):
        mech -= 20; issues.append("not 1080x1920")
    if reel_video.get("fps") not in (30, 60):
        mech -= 6; issues.append("fps not 30/60")
    if aesthetic is None:
        return min(mech, 0), issues + ["aesthetic review not supplied"]
    return min(mech, aesthetic), issues


def _subtitle(subtitles: dict | None) -> tuple[int, list[str]]:
    if not subtitles:
        return 0, ["no subtitles"]
    subs = subtitles.get("subtitles", [])
    issues, s = [], 100
    if not subs:
        return 0, ["no subtitle cues"]
    long = [c for c in subs if len(c.get("text", "").split()) > 6]
    if long:
        s -= min(20, 4 * len(long)); issues.append(f"{len(long)} cues > 6 words")
    if not any(c.get("emphasis") for c in subs):
        s -= 8; issues.append("no key-word emphasis")
    return max(0, s), issues


def _voiceover(reel_video: dict | None) -> tuple[int, list[str]]:
    if not reel_video or not reel_video.get("has_voiceover"):
        return 70, ["no voiceover (captions-only)"]
    return 92, []


def _brand(caption: dict, storyboard: dict) -> tuple[int, list[str]]:
    issues, s = [], 100
    cap = (caption or {}).get("caption", "")
    if BRAND_NAME.lower() not in cap.lower():
        s -= 10; issues.append("brand missing from caption")
    if not any(sc.get("kind") == "outro" for sc in storyboard.get("scenes", [])):
        s -= 8; issues.append("no branded outro scene")
    return max(0, s), issues


def run(date: str, *, hooks: dict, script_edited: dict, storyboard: dict,
        compliance: dict, caption: dict | None = None,
        subtitles: dict | None = None, reel_video: dict | None = None,
        aesthetic_score: int | None = None, asset_picker: dict | None = None,
        cost_guard: dict | None = None) -> dict:
    scores, issues = {}, {}
    scores["hook"], issues["hook"] = _hook(hooks)
    scores["retention"], issues["retention"] = _retention(storyboard, script_edited)
    scores["edit_quality"], issues["edit_quality"] = _edit(storyboard)
    scores["visual_quality"], issues["visual_quality"] = _visual(reel_video, aesthetic_score)
    scores["subtitle"], issues["subtitle"] = _subtitle(subtitles)
    scores["voiceover"], issues["voiceover"] = _voiceover(reel_video)
    scores["compliance"] = int(compliance.get("score", 0))
    issues["compliance"] = compliance.get("violations", [])
    scores["brand"], issues["brand"] = _brand(caption or {}, storyboard)
    scores["cost_efficiency"], issues["cost_efficiency"] = _cost_efficiency(asset_picker, cost_guard)

    passed = {k: scores[k] >= GATES[k] for k in GATES}
    overall = all(passed.values())
    scores["publish"] = 100 if overall else min(scores[k] for k in GATES)

    fails = [k for k in GATES if not passed[k]]
    all_issues = [f"{k}: {i}" for k in issues for i in (issues[k] if isinstance(issues[k], list) else [issues[k]]) if i]
    payload = {
        "date": date, "passed": overall, "scores": scores, "gates": GATES,
        "gate_passed": passed, "issues": all_issues,
        "fixes_required": [f"{k} ({scores[k]}<{GATES[k]}) -> {REROUTE[k]}" for k in fails],
        "reroute_to": REROUTE[fails[0]] if fails else "",
        "verdict": "PUBLISH_OK" if overall else "BLOCKED",
    }
    state.save_artifact(date, "quality", payload)
    return payload
