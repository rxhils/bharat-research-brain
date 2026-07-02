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

GATES = {"hook": 90, "story": 85, "scene_quality": 85, "animation_quality": 90,
         "retention": 90, "edit_quality": 90, "visual_quality": 90,
         "subtitle": 90, "voiceover": 85, "compliance": 95, "brand": 90,
         "cost_efficiency": 85, "visual_uniqueness": 85, "freshness": 95}
REROUTE = {"hook": "hook_lab", "story": "market_sentinel",
           "scene_quality": "higgsfield_scene_generator",
           "animation_quality": "higgsfield_creative_director",
           "retention": "retention_editor",
           "edit_quality": "motion_storyboard", "visual_quality": "motion_graphics",
           "subtitle": "subtitle_engine", "voiceover": "voice_studio",
           "compliance": "compliance_shield", "brand": "caption_desk",
           "cost_efficiency": "asset_picker", "visual_uniqueness": "motion_variation",
           "freshness": "market_sentinel"}
# which improvement button fixes which failed gate (surfaced in the UI)
SUGGEST_BUTTON = {
    "hook": "Rewrite Hook", "story": "Change Story (fresh research)",
    "scene_quality": "Regenerate Failed Scene",
    "animation_quality": "Improve Animation Quality",
    "retention": "Shorten Script / Improve Pacing",
    "edit_quality": "Improve Animations & Quality",
    "visual_quality": "Improve Animations & Quality / Regenerate Visuals",
    "subtitle": "Re-run Subtitle Engine", "voiceover": "Regenerate Voiceover",
    "compliance": "Fix wording (Compliance Shield)", "brand": "Rewrite Caption",
    "cost_efficiency": "Pick Different Assets", "visual_uniqueness": "Try Different Style",
    "freshness": "Change Story (fresh research)",
}


def _freshness(research: dict | None, run_key: str) -> tuple[int, list[str]]:
    """Data must be current + sourced. Stale/unsourced research blocks publish."""
    from datetime import datetime, timezone

    if not research:
        return 0, ["no research artifact (Needs Research)"]
    issues, s = [], 100
    stories = research.get("top_3_stories") or research.get("stories") or []
    if not stories:
        return 0, ["research has no stories (Needs Research)"]
    unsourced = [st.get("headline", "?") for st in stories
                 if not (st.get("sources") or st.get("source_urls") or st.get("source"))]
    if unsourced:
        s -= 30; issues.append(f"{len(unsourced)} story(ies) missing source URLs")
    stamp = str(research.get("retrieved_at") or research.get("generated_at")
                or research.get("date") or "")[:10]
    if not stamp:
        s -= 20; issues.append("research is not timestamped")
    else:
        # run_key is either 'YYYY-MM-DD' or 'reel-YYYY-MM-DD-HHMM-NNN[-vN]'
        run_date = run_key.removeprefix("reel-")[:10]
        today = datetime.now(timezone.utc).date().isoformat()
        if stamp not in (run_date, today):
            s -= 15; issues.append(f"research dated {stamp} does not match this run ({run_date})")
    return max(0, s), issues


def _cost_efficiency(asset_picker: dict | None, cost_guard: dict | None,
                     fresh_video: dict | None = None) -> tuple[int, list[str]]:
    """Reward efficient spend. Two modes:
    - Fresh Video Mode active: efficient = stayed within the per-reel budget
      ceiling, fallbacks were genuine failures (not carelessness) — "0
      generations = perfect" does NOT apply, since spend is the deliberate
      default in this mode.
    - Otherwise (cost-optimized default): reward pure library reuse, penalize
      any unapproved paid generation — unchanged from before.
    """
    active = {"ready_to_execute", "completed", "partial_fallback",   # legacy
              "requires_user_action", "approved_awaiting_conductor", "partial"}
    if fresh_video and (fresh_video.get("status") in active
                        or fresh_video.get("generation_status") in active):
        issues, s = [], 100
        from .config import HIGGSFIELD_MAX_CREDITS_PER_REEL
        est = float(fresh_video.get("estimated_cost_credits", 0))
        if est > HIGGSFIELD_MAX_CREDITS_PER_REEL:
            s -= 30; issues.append(f"estimated {est}cr exceeds ceiling {HIGGSFIELD_MAX_CREDITS_PER_REEL}cr")
        actual = fresh_video.get("actual_cost_credits")
        if actual is not None and actual > est * 1.15:
            s -= 15; issues.append(f"actual spend {actual}cr overran estimate {est}cr")
        failed_n = int(fresh_video.get("failed_clips",
                                       fresh_video.get("fallback_count", 0)) or 0)
        scene_n = max(1, int(fresh_video.get("total_clips",
                                             fresh_video.get("scene_count", 1)) or 1))
        if failed_n:
            ratio = failed_n / scene_n
            s -= min(25, int(ratio * 50))
            issues.append(f"{failed_n}/{scene_n} scene(s) failed (spend without full result)")
        return max(0, s), issues

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


def _story(viral_fit: dict | None) -> tuple[int, list[str]]:
    """Story strength from the Viral Fit Gate (0-10 weighted -> 0-100)."""
    if not viral_fit:
        return 80, ["viral fit artifact missing (story not verified)"]
    fit = float(viral_fit.get("viral_fit_score",
                              (viral_fit.get("chosen") or {}).get("viral_fit", 0)))
    score = min(100, int(fit * 10) + 15)  # 7.0 fit -> 85 (gate); 8.5+ -> 100
    issues = [] if score >= 85 else [f"viral fit {fit}/10 is weak for a reel"]
    if viral_fit.get("selected_story_is_duplicate"):
        score -= 10; issues.append("story repeats a recent reel topic")
    return max(0, score), issues


def _scene_and_animation(scene_quality: dict | None,
                         renderer: str) -> tuple[int, int, list[str], list[str]]:
    """(scene_score, animation_score, scene_issues, animation_issues) —
    renderer-aware. Higgsfield-primary scores come from the Scene Quality
    Inspector; explicit Remotion fallback is judged by its own (lower) bar in
    run() via gate adjustment; missing clips block honestly."""
    if renderer == "remotion_fallback":
        return 85, 82, ["remotion fallback: no Higgsfield clips (explicitly selected)"], \
               ["procedural Remotion motion — below the premium Higgsfield bar"]
    if not scene_quality:
        return 0, 0, ["awaiting Higgsfield clip generation"], \
               ["awaiting Higgsfield clip generation"]
    overall = int(scene_quality.get("overall_scene_quality_score", 0))
    results = scene_quality.get("scene_quality", [])
    static = [r["shot_id"] for r in results
              if any("static" in i for i in r.get("issues", []))]
    dupes = [r["shot_id"] for r in results
             if any("duplicate" in i for i in r.get("issues", []))]
    anim = min(100, overall + 5)
    anim_issues = []
    if static:
        anim = min(anim, 85); anim_issues.append(f"static motion in {', '.join(static)}")
    if dupes:
        anim = min(anim, 85); anim_issues.append(f"near-duplicate scenes: {', '.join(dupes)}")
    scene_issues = [f"{r['shot_id']}: {i}" for r in results for i in r.get("issues", [])]
    return overall, anim, scene_issues, anim_issues


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


def _voiceover(reel_video: dict | None, vo: dict | None = None) -> tuple[int, list[str]]:
    mode = (vo or {}).get("voiceover_mode")
    if mode == "real_tts":
        return 92, []
    if mode == "local_simulation":
        # preview-OK: a simulated VO must NOT block the whole flow; production
        # readiness is tracked separately (needs a real TTS key).
        return 88, ["simulation voiceover (preview only — add a TTS key for production)"]
    if mode == "no_voice_preview":
        return 85, ["no-voice preview mode"]
    if not reel_video or not reel_video.get("has_voiceover"):
        return 70, ["no voiceover (captions-only)"]
    return 92, []


def _teaching_clarity(script_edited: dict) -> tuple[int, list[str]]:
    wc = int(script_edited.get("word_count", 0) or 0)
    if wc == 0:
        return 60, ["no script narration"]
    s, issues = 90, []
    if wc > 65:
        s -= 10; issues.append(f"{wc} words (>65) dilutes one clear teaching point")
    narr = (script_edited.get("narration") or "").lower()
    if any(w in narr for w in ("because", "why", "means", "driver", "sector", "reason", "reacted")):
        s = min(100, s + 5)
    else:
        issues.append("no explicit cause ('why/because/driver') — teaching point unclear")
    return max(0, s), issues


def _text_overlay(hooks: dict, subtitles: dict | None, reel_video: dict | None) -> tuple[int, list[str]]:
    s, issues = 100, []
    if not (reel_video or {}).get("hook_overlay"):
        s -= 10; issues.append("no burned hook overlay")
    if not (subtitles or {}).get("subtitles"):
        s -= 15; issues.append("no subtitle overlay")
    if len((hooks.get("on_screen_hook", "") or "").split()) > 7:
        s -= 8; issues.append("on-screen hook > 7 words")
    return max(0, s), issues


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
        cost_guard: dict | None = None, research: dict | None = None,
        visual_uniqueness: dict | None = None, fresh_video: dict | None = None,
        viral_fit: dict | None = None, scene_quality: dict | None = None,
        renderer: str = "higgsfield_primary", voiceover: dict | None = None,
        capabilities_report: dict | None = None) -> dict:
    gates = dict(GATES)
    if renderer == "remotion_fallback":
        # explicitly-selected fallback is judged by its own (lower) animation bar
        gates["animation_quality"] = 80
    scores, issues = {}, {}
    scores["hook"], issues["hook"] = _hook(hooks)
    scores["story"], issues["story"] = _story(viral_fit)
    (scores["scene_quality"], scores["animation_quality"],
     issues["scene_quality"], issues["animation_quality"]) = \
        _scene_and_animation(scene_quality, renderer)
    scores["retention"], issues["retention"] = _retention(storyboard, script_edited)
    scores["edit_quality"], issues["edit_quality"] = _edit(storyboard)
    scores["visual_quality"], issues["visual_quality"] = _visual(reel_video, aesthetic_score)
    scores["subtitle"], issues["subtitle"] = _subtitle(subtitles)
    scores["voiceover"], issues["voiceover"] = _voiceover(reel_video, voiceover)
    scores["compliance"] = int(compliance.get("score", 0))
    issues["compliance"] = compliance.get("violations", [])
    scores["brand"], issues["brand"] = _brand(caption or {}, storyboard)
    scores["cost_efficiency"], issues["cost_efficiency"] = _cost_efficiency(asset_picker, cost_guard, fresh_video)
    scores["freshness"], issues["freshness"] = _freshness(research, date)
    if visual_uniqueness is not None:
        scores["visual_uniqueness"] = int(visual_uniqueness.get("visual_uniqueness_score", 0))
        issues["visual_uniqueness"] = (
            [f"too similar to {', '.join(visual_uniqueness.get('too_similar_to', []))} "
             f"({', '.join(visual_uniqueness.get('matched_dimensions', []))})"]
            if not visual_uniqueness.get("passed") else [])
    else:
        # first-ever run / legacy runs: nothing to compare against
        scores["visual_uniqueness"] = 100
        issues["visual_uniqueness"] = []

    # --- viral / creative axes (aliases + new) ---------------------------------
    scores["visual_appeal"] = scores["visual_quality"]
    scores["teaching_clarity"], issues["teaching_clarity"] = _teaching_clarity(script_edited)
    scores["text_overlay"], issues["text_overlay"] = _text_overlay(hooks, subtitles, reel_video)
    real_clips = (fresh_video or {}).get("execution_mode") == "real"
    scores["backend_autonomy"] = 100 if (fresh_video or {}).get("generated_by") == "backend" else 90

    gates["teaching_clarity"] = 85
    gates["visual_appeal"] = 90
    gates["backend_autonomy"] = 100

    passed = {k: scores[k] >= gates[k] for k in gates}
    overall = all(passed.values())
    scores["publish"] = 100 if overall else min(scores[k] for k in gates)
    scores["publish_readiness"] = scores["publish"]

    # --- preview vs production readiness --------------------------------------
    caps = capabilities_report or {}
    real_vo = (voiceover or {}).get("voiceover_mode") == "real_tts"
    composio_ok = caps.get("composio_available", False)
    # gates that only REAL Higgsfield/TTS output can satisfy — excluded from the
    # preview verdict so a free simulation isn't unfairly marked failed.
    REAL_ONLY = {"animation_quality", "visual_quality", "visual_appeal", "voiceover"} \
        if not real_clips else set()
    preview_ready = all(passed[k] for k in gates if k not in REAL_ONLY)
    production_ready = overall and real_clips and real_vo

    fails = [k for k in gates if not passed[k]]
    all_issues = [f"{k}: {i}" for k in issues for i in (issues[k] if isinstance(issues[k], list) else [issues[k]]) if i]
    # specific, actionable readiness reasons
    fixes = [f"{k} ({scores[k]}<{gates[k]}) -> {REROUTE.get(k, 'improvement_director')}" for k in fails]
    if not real_clips:
        fixes.append("missing real animated clips -> add HIGGSFIELD_API_KEY + confirm generation")
    if not real_vo:
        fixes.append("missing real voiceover -> add a TTS key (HIGGSFIELD_API_KEY) for production VO")
    if not composio_ok:
        fixes.append("Composio not connected -> connect Instagram publishing in Settings")

    verdict = "PUBLISH_OK" if production_ready else "PREVIEW_OK" if preview_ready else "BLOCKED"
    payload = {
        "date": date, "passed": overall,
        "preview_ready": preview_ready, "production_ready": production_ready,
        "generation_mode": "real" if real_clips else "simulation",
        "voiceover_mode": (voiceover or {}).get("voiceover_mode"),
        "scores": scores, "gates": gates, "renderer": renderer,
        "gate_passed": passed, "issues": all_issues,
        "fixes_required": fixes,
        "suggested_buttons": [{"gate": k, "score": scores[k], "min": gates[k],
                               "click": SUGGEST_BUTTON.get(k, "Improve Reel")} for k in fails],
        "reroute_to": REROUTE.get(fails[0], "") if fails else "",
        "suggested_action": ("Ready to publish." if production_ready else
                             "Preview ready — add real generation/TTS keys for production."
                             if preview_ready else "Blocked — see fixes_required."),
        "verdict": verdict,
    }
    state.save_artifact(date, "quality", payload)
    return payload
