"""Agent — Watch-Through Editor (Maven Reels Newsroom). Local, free.

Chunk 4: reviews the PLANNED reel second-by-second, as if watching it, BEFORE
generation. Answers the retention checkpoints (0/1/3/6/10/15s, save?, share?).
If a checkpoint fails, it flags the beat to rewrite. Reads the winning variant +
format_director + script_saveable. Writes 42_watch_through.json.
"""
from __future__ import annotations

from . import state


def _winner(date: str) -> dict:
    rv = _opt(date, "reel_variants") or {}
    for v in rv.get("variants", []):
        if v.get("variant") == rv.get("chosen_variant"):
            return v
    return {}


def _scene_at(scenes: list[dict], t: float) -> dict:
    clock = 0.0
    for s in scenes:
        clock += float(s.get("duration", 3.0))
        if t < clock:
            return s
    return scenes[-1] if scenes else {}


def run(date: str) -> dict:
    winner = _winner(date)
    fd = _opt(date, "format_director") or {}
    sc = _opt(date, "script_saveable") or {}
    scenes = winner.get("scene_plan", [])
    hook = winner.get("hook", "")
    lesson = sc.get("saveable_lesson", "")

    checks = []

    def chk(t, question, ok, detail):
        checks.append({"at_s": t, "question": question, "pass": bool(ok), "detail": detail})

    first = scenes[0] if scenes else {}
    chk(0.0, "Do I know what this is about?",
        first.get("requires_text_fidelity") and bool(hook),
        "First frame is a hook card" if first.get("requires_text_fidelity") else "First frame has no hook text")
    chk(1.0, "Is there a reason to keep watching?",
        len(hook.split()) <= 8 and hook, f"Hook is {len(hook.split())} words")
    s3 = _scene_at(scenes, 3.0)
    chk(3.0, "Did the story move forward?",
        s3.get("scene_type") != first.get("scene_type"),
        f"At 3s: {s3.get('scene_type')} ({s3.get('role')})")
    s6 = _scene_at(scenes, 6.0)
    chk(6.0, "Did I learn something?",
        s6.get("role") in ("mechanism", "cause", "reality", "mistake", "transmission"),
        f"At 6s: {s6.get('role')}")
    s10 = _scene_at(scenes, 10.0)
    chk(10.0, "Is there a visual change?",
        s10.get("scene_id") != s6.get("scene_id"),
        f"At 10s: {s10.get('scene_id')} {s10.get('scene_type')}")
    has_lesson = any(s.get("role") == "lesson" for s in scenes)
    chk(15.0, "Is the takeaway clear?", has_lesson and bool(lesson),
        f"Lesson: {lesson}" if lesson else "No takeaway scene")
    chk("save", "Would I save this?", bool(lesson) and bool(fd.get("save_reason")),
        fd.get("save_reason", ""))
    chk("share", "Would I share it?", bool(fd.get("share_reason")),
        fd.get("share_reason", ""))

    fails = [c for c in checks if not c["pass"]]
    rewrite = []
    for c in fails:
        if c["at_s"] in (0.0, 1.0):
            rewrite.append("hook_lab: sharpen the first-frame hook")
        elif c["at_s"] in (3.0, 6.0, 10.0):
            rewrite.append("blueprint: add a pattern-interrupt / learning beat")
        elif c["at_s"] == 15.0 or c["at_s"] == "save":
            rewrite.append("scriptroom: ensure a saveable lesson beat")

    payload = {
        "date": date, "checkpoints": checks,
        "passed": len(fails) == 0, "fail_count": len(fails),
        "rewrite_beatboard": sorted(set(rewrite)),
        "verdict": "watch-through OK" if not fails else
                   f"{len(fails)} retention gap(s) — rewrite before generation",
    }
    state.save_artifact(date, "watch_through", payload)
    return payload


def _opt(date: str, key: str):
    try:
        return state.load_artifact(date, key)
    except Exception:
        return None
