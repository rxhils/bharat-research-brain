"""Step — Fresh Video Scenes (Premium, opt-in, PAID).

Generates fresh, unique Higgsfield motion video for EVERY storyboard scene,
image-seed -> animate: a clean text-free still (nano_banana_pro) is generated
first, then animated into a short clip (seedance1_5, image-to-video). This is
the PRIMARY background source when Fresh Video Mode is on; Remotion's own
procedural background (grid/glow/drift) becomes the last-resort fallback.

Honesty/architecture note: this module NEVER calls Higgsfield itself — the
Python backend cannot reach paid MCP tools (same boundary as Voice Studio /
Scene Studio today). It only:
  1. build_specs() — deterministic, FREE. Builds per-scene prompts + a cost
     guard decision. Called by orchestrator.prepare().
  2. record_results() — the Claude Code conductor calls this AFTER actually
     generating + downloading each clip, to persist the real, auditable
     outcome (cost spent, clip paths, any per-scene fallbacks).

No baked text/numbers/logos/arrows in any generated clip — same compliance
rule as the existing asset library (step7_asset_director.py).
"""
from __future__ import annotations

from pathlib import Path

from . import config, state, step_cost_guard

_STYLE = ("premium Indian market dashboard, clean dark navy/black, subtle "
          "teal/green/blue accents, soft grid lines, minimal chart lines, high-end "
          "editorial finance aesthetic, lots of negative space, NO readable text")
_BASE_NEG = ("cheap AI look, cartoon, meme, random candlestick spam, fake logos, "
            "fake numbers, clutter, unreadable text, gibberish text, watermark, "
            "bull/bear mascots, buy/sell arrows, 3D coins, overdesigned")
_MOTION = ("slow cinematic push-in, subtle parallax, smooth moving data glow, "
           "calm premium motion, no chaotic movement")


def _scene_prompt(scene: dict) -> str:
    visual = scene.get("visual", "premium finance motion background")
    return (f"Vertical 9:16 premium finance motion background plate for Maven, "
            f"an Indian stock market brand. Scene concept: {visual}. {_STYLE}.")


def build_specs(date: str, *, storyboard: dict) -> dict:
    """Deterministic + free. Returns the per-scene generation plan and the
    cost-guard decision. Never calls Higgsfield."""
    scenes = storyboard.get("scenes", [])
    requests = [{
        "scene": s["scene"], "kind": s["kind"],
        "seed_prompt": _scene_prompt(s), "seed_negative_prompt": _BASE_NEG,
        "seed_model": config.FRESH_VIDEO_SEED_MODEL,
        "video_model": config.FRESH_VIDEO_MODEL,
        "video_duration": config.FRESH_VIDEO_CLIP_DURATION,
        "video_motion_hint": _MOTION,
        "clip_path": f"fresh_video/scene_{s['scene']}.mp4",
    } for s in scenes]

    estimated_cost = len(requests) * (config.FRESH_VIDEO_SEED_COST_CREDITS +
                                      config.FRESH_VIDEO_CLIP_COST_CREDITS)
    # The existing cost guard's per-request caps (MAX_..._WITH_APPROVAL=1) were
    # tuned for "fill 0-3 missing library slots", not a whole reel's worth of
    # scenes. Treat the entire fresh-video batch as ONE approved decision
    # (requested=1); the real per-reel scene budget is enforced explicitly
    # below via FRESH_VIDEO_MAX_CREDITS_PER_REEL.
    guard = step_cost_guard.evaluate(date, requested=1,
                                     approved=config.FRESH_VIDEO_MODE_ENABLED)

    allowed = (config.FRESH_VIDEO_MODE_ENABLED and guard["allowed"] and
               estimated_cost <= config.FRESH_VIDEO_MAX_CREDITS_PER_REEL)
    status = ("ready_to_execute" if allowed else
              "over_budget" if estimated_cost > config.FRESH_VIDEO_MAX_CREDITS_PER_REEL else
              "disabled" if not config.FRESH_VIDEO_MODE_ENABLED else "requires_approval")

    payload = {
        "date": date, "mode": "fresh_video", "scene_count": len(requests),
        "requests": requests,
        "estimated_cost_credits": round(estimated_cost, 1),
        "max_credits_per_reel": config.FRESH_VIDEO_MAX_CREDITS_PER_REEL,
        "cost_guard": guard, "status": status, "allowed": allowed,
        "results": [],  # filled in by record_results() after real generation
        "note": ("Spec only — the conductor executes these via Higgsfield MCP "
                 "and calls record_results(). If blocked/over-budget, the WHOLE "
                 "reel falls back to the reusable-library system (consistent "
                 "look, not a mix)."),
    }
    state.save_artifact(date, "fresh_video_scenes", payload)
    return payload


def record_results(date: str, results: list[dict]) -> dict:
    """Called by the conductor after real generation. Each result:
    {scene, seed_image_ref, video_job_id, clip_path, cost_credits, status,
     fallback_reason (if status != 'completed')}. Persists the auditable record
     the Cost Efficiency score reads, and verifies clip files actually exist."""
    spec = state.load_artifact(date, "fresh_video_scenes")
    run_dir = config.run_dir(date)
    verified = []
    for r in results:
        p = run_dir / r.get("clip_path", "")
        r = dict(r)
        r["file_exists"] = p.exists()
        if r.get("status") == "completed" and not r["file_exists"]:
            r["status"] = "failed_fallback"
            r["fallback_reason"] = "clip file missing on disk after generation"
        verified.append(r)

    actual_cost = sum(r.get("cost_credits", 0) for r in verified)
    fallbacks = [r for r in verified if r.get("status") != "completed"]
    spec["results"] = verified
    spec["actual_cost_credits"] = round(actual_cost, 1)
    spec["completed_count"] = len(verified) - len(fallbacks)
    spec["fallback_count"] = len(fallbacks)
    spec["status"] = "completed" if not fallbacks else "partial_fallback"
    state.save_artifact(date, "fresh_video_scenes", spec)
    return spec
