"""Step — Text Quality Auditor (local, free).

Judges the TEXT layer on its own axis, separate from the visual/animation
auditor: does the on-screen text match the voice, is it synced, is it readable
and premium (not an auto-caption dump). Writes 24_text_quality.json. Failing
gates route to text-only fixes — never a Higgsfield regeneration.
"""
from __future__ import annotations

from . import state

GATES = {
    "text_voice_match_score": 90,
    "subtitle_readability_score": 90,
    "subtitle_sync_score": 90,
    "overall_text_quality_score": 90,
}


def _readability(kinetic: dict) -> tuple[int, list[str]]:
    subs = kinetic.get("subtitles", [])
    if not subs:
        return 0, ["no subtitles"]
    issues, s = [], 100
    long_cue = [1 for c in subs if len(c["text"].split()) > 6]
    if long_cue:
        s -= min(20, 5 * len(long_cue)); issues.append(f"{len(long_cue)} cue(s) > 6 words")
    three_line = [1 for c in subs if len(c.get("lines", [])) > 2]
    if three_line:
        s -= 15; issues.append(f"{len(three_line)} cue(s) wrap to 3+ lines")
    wide = [1 for c in subs for ln in c.get("lines", []) if len(ln) > 28]
    if wide:
        s -= min(15, 3 * len(wide)); issues.append("a line exceeds mobile-safe width")
    if not any(c.get("emphasis_words") for c in subs):
        s -= 8; issues.append("no keyword emphasis")
    return max(0, s), issues


def _sync(kinetic: dict, align: dict) -> tuple[int, list[str]]:
    subs = kinetic.get("subtitles", [])
    if not subs:
        return 0, ["no subtitle cues to sync"]
    issues, s = [], 100
    vid = float(align.get("video_duration") or 0)
    prev_end = 0.0
    for c in subs:
        if c["start"] < prev_end - 0.05:
            s -= 6; issues.append("overlapping cues")
            break
        prev_end = c["end"]
    long_on = [1 for c in subs if (c["end"] - c["start"]) > 4.0]
    if long_on:
        s -= min(20, 6 * len(long_on)); issues.append(f"{len(long_on)} cue(s) on screen > 4s")
    if vid and subs[-1]["end"] > vid + 0.3:
        s -= 10; issues.append("subtitles run past the video end")
    return max(0, s), issues


def _hook_typo(kinetic: dict) -> tuple[int, list[str]]:
    h = kinetic.get("hook_text", {})
    if not h.get("text"):
        return 60, ["no hook overlay"]
    issues, s = [], 100
    words = len(h["text"].split())
    if words > 7:
        s -= 15; issues.append(f"hook is {words} words (>7)")
    if h.get("start", 0) > 0.35:
        s -= 8; issues.append("hook appears after 0.3s")
    if not h.get("emphasis_words"):
        s -= 6; issues.append("hook has no emphasis word")
    return max(0, s), issues


def run(date: str, *, alignment: dict, kinetic: dict, safe_area: dict,
        animations: dict) -> dict:
    scores, issues = {}, {}
    scores["text_voice_match_score"] = int(alignment.get("text_voice_match_score", 0))
    issues["text_voice_match"] = alignment.get("issues", [])
    scores["hook_typography_score"], issues["hook_typography"] = _hook_typo(kinetic)
    scores["subtitle_readability_score"], issues["subtitle_readability"] = _readability(kinetic)
    scores["subtitle_sync_score"], issues["subtitle_sync"] = _sync(kinetic, alignment)
    scores["text_animation_score"] = 92 if animations.get("text_animations") else 60
    scores["text_safe_area_score"] = 95 if safe_area.get("scene_safe_areas") else 70
    core = [scores["text_voice_match_score"], scores["subtitle_readability_score"],
            scores["subtitle_sync_score"], scores["hook_typography_score"],
            scores["text_animation_score"], scores["text_safe_area_score"]]
    scores["overall_text_quality_score"] = round(sum(core) / len(core))

    passed = {k: scores[k] >= GATES[k] for k in GATES}
    all_issues = [f"{k}: {i}" for k, lst in issues.items() for i in lst if i]
    fails = [k for k in GATES if not passed[k]]
    payload = {
        "date": date, "scores": scores, "gates": GATES,
        "gate_passed": passed, "passed": all(passed.values()),
        "issues": all_issues,
        "fixes_required": [f"{k} ({scores[k]}<{GATES[k]}) -> text-only reassemble" for k in fails],
        "reroute_to": "text_studio" if fails else "",
        "verdict": "TEXT_OK" if all(passed.values()) else "TEXT_BLOCKED",
    }
    state.save_artifact(date, "text_quality", payload)
    return payload
