"""Agent — Editor-in-Chief (Maven Reels Newsroom). Local, free.

The holistic executive review before Reel Review: not just technical validity,
but "does this feel like a real premium finance media Reel, or AI slop?" It reads
the artifacts already produced (story, footage world, scene/text/quality audits,
renderer) and returns a verdict + editor's note. Writes editor_in_chief_review.json.

Honest by design: signals it can measure from artifacts are scored; judgments a
file cannot prove (true photo-realism, footage-matches-news) are flagged for the
operator's eye in the note rather than faked as a green score.
"""
from __future__ import annotations

from . import state

GATE = 85


def _opt(date: str, key: str) -> dict | None:
    try:
        return state.load_artifact(date, key)
    except Exception:
        return None


def _clamp(v: int) -> int:
    return max(0, min(100, int(v)))


def run(date: str) -> dict:
    q = _opt(date, "quality") or {}
    qs = q.get("scores", {})
    tq = (_opt(date, "text_quality") or {}).get("scores", {})
    sq = _opt(date, "scene_quality") or {}
    scout = _opt(date, "location_scout")
    reel = _opt(date, "reel_video") or _opt(date, "final_reel") or {}
    viral = _opt(date, "viral_fit") or {}

    renderer = reel.get("renderer", "")
    is_sim = (_opt(date, "scene_generation") or {}).get("generation_mode") == "simulation" \
        or any("simulation" in str(c.get("mode", "")) for c in
               (_opt(date, "scene_generation") or {}).get("clips", []))

    issues, notes = [], []

    # realism — real Higgsfield clips + scene inspector; simulation is not realistic
    scene_score = int(sq.get("overall_scene_quality_score", 0))
    if is_sim or not scene_score:
        realism = 55; issues.append("footage is simulation/preview — not photoreal yet")
        notes.append("Realism unverified: this is a simulation preview, not real Higgsfield footage.")
    else:
        realism = _clamp(min(scene_score, int(qs.get("visual_quality", scene_score))))

    # story fit & save/share — from viral fit + freshness
    fit = float(viral.get("viral_fit_score", (viral.get("chosen") or {}).get("viral_fit", 0)))
    story_fit = _clamp(min(100, int(fit * 10) + 15)) if fit else 75
    save_share = _clamp((story_fit + int(tq.get("overall_text_quality_score", 80))) // 2)

    hook_strength = _clamp(max(int(qs.get("hook", 0)), int(tq.get("hook_typography_score", 0)), 60))

    # visual relevance — needs Location Scout world matched to the story; file can't
    # fully prove the footage matches the news, so cap + flag for the operator.
    if scout and scout.get("selected_footage_world"):
        visual_relevance = 88 if not is_sim else 70
        notes.append(f"Footage world: {scout['selected_footage_world']} — confirm the shots actually match the story.")
    else:
        visual_relevance = 60; issues.append("no Location Scout world chosen — footage may be generic")

    # ai-slop risk (0=none .. 100=high) → convert to a 'not-slop' score
    slop = 0
    if is_sim:
        slop += 40
    if not scout:
        slop += 20
    static = [r for r in sq.get("scene_quality", []) if any("static" in i for i in r.get("issues", []))]
    if static:
        slop += 15; issues.append(f"static/near-still scenes: {', '.join(r['shot_id'] for r in static)}")
    ai_slop_risk = _clamp(slop)

    teaching = _clamp(int(qs.get("teaching_clarity", tq.get("subtitle_readability_score", 85))))
    pacing = _clamp(min(int(qs.get("retention", 90)), int(qs.get("edit_quality", 90))))
    brand = _clamp(int(qs.get("brand", 90)))

    scores = {
        "realism": realism, "story_fit": story_fit, "hook_strength": hook_strength,
        "visual_relevance": visual_relevance, "ai_slop_risk": ai_slop_risk,
        "teaching_clarity": teaching, "pacing": pacing, "brand_quality": brand,
        "save_share_potential": save_share,
    }
    # overall = mean of the positive axes, penalised by slop risk
    positive = [realism, story_fit, hook_strength, visual_relevance, teaching, pacing, brand, save_share]
    overall = _clamp(round(sum(positive) / len(positive) - ai_slop_risk * 0.25))

    fails = []
    if hook_strength < 90:
        fails.append("hook not scroll-stopping enough")
    if ai_slop_risk > 35:
        fails.append("reads as AI slop (simulation/generic/static)")
    if visual_relevance < 85:
        fails.append("footage may not match the story")
    if teaching < 85:
        fails.append("teaching point unclear")
    if realism < 80:
        fails.append("footage not premium/realistic enough")

    passed = overall >= GATE and not fails
    reroute = ("location_scout" if visual_relevance < 85 or ai_slop_risk > 35
               else "hook_lab" if hook_strength < 90
               else "scriptroom" if teaching < 85 else "")
    editor_note = ("Premium finance-media quality — clears the desk." if passed else
                   "Holds: " + "; ".join(fails) + ". "
                   + ("Run real Higgsfield footage (this is a preview). " if is_sim else "")
                   + "; ".join(notes))

    payload = {
        "date": date, "passed": passed, "overall_score": overall, "scores": scores,
        "issues": issues, "required_fixes": fails, "reroute_to": reroute,
        "is_simulation_preview": bool(is_sim),
        "editor_note": editor_note.strip(),
    }
    state.save_artifact(date, "editor_in_chief", payload)
    return payload
