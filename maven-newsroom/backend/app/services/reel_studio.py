"""Reel Studio — production-run manager for the Reels pipeline.

Owns: unique timestamped job IDs, fresh per-run output folders, is_latest
bookkeeping, rejection feedback, the Reel Improvement Director bridge, and
version jobs (…-v2) that re-run the deterministic pipeline + Remotion render
LOCALLY (zero paid generation).

Honesty contract: the backend runs the full Reel itself — research, animated
Higgsfield clip generation (real when HIGGSFIELD_API_KEY is set, else a free
local simulation preview), ffmpeg assembly, and audit. It never fakes an
artifact: a missing provider surfaces as a named, operator-actionable gap (see
maven_reels.pipeline.capabilities), never as "requires Claude Code conductor".
"""
from __future__ import annotations

import asyncio
import re
import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path

from .. import database as db
from ..config import REPO_ROOT
from ..events import IST, bus
from ..registry_reels import REEL_NODES_BY_ID
from . import ingest_reels

# make the maven_reels package importable from the backend (same repo)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

REEL_OUTPUT_ROOT = REPO_ROOT / "outputs" / "maven_reels"

FEEDBACK_TYPES = [
    "weak_hook", "boring_script", "bad_animation", "visuals_too_basic",
    "too_slow", "bad_voiceover", "bad_subtitles", "not_premium_enough",
    "wrong_story", "bad_data", "try_different_style",
    "improve_animations_quality", "other",
]


def _now() -> str:
    return datetime.now(IST).isoformat(timespec="seconds")


def _root_id(job_id: str) -> str:
    return re.sub(r"-v\d+$", "", job_id)


def new_job_id() -> str:
    now = datetime.now(IST)
    day = now.strftime("%Y-%m-%d")
    n = db.query_one(
        "SELECT COUNT(*) AS c FROM jobs WHERE pipeline='reel' AND job_id LIKE ?",
        (f"reel-{day}-%",)) or {"c": 0}
    return f"reel-{day}-{now.strftime('%H%M')}-{int(n['c']) + 1:03d}"


def _clear_latest() -> None:
    with db.connect() as c:
        c.execute("UPDATE jobs SET is_latest=0 WHERE pipeline='reel'")


def mark_latest(job_id: str) -> None:
    _clear_latest()
    db.upsert("jobs", {"job_id": job_id, "is_latest": 1, "updated_at": _now()},
              conflict_keys=["job_id"])


def _set_node(job_id: str, nid: str, **f) -> None:
    s = REEL_NODES_BY_ID[nid]
    base = {"job_id": job_id, "node_id": nid, "node_name": s["name"],
            "component_class": s["component_class"], "component_type": s["component_type"],
            "intelligent": int(s["intelligent"]), "actual_component": s["actual_component"],
            "external": int(s["external"]), "in_graph": int(s["in_graph"]),
            "role": s["role"], "ord": s["order"]}
    base.update(f)
    db.upsert("nodes", base, conflict_keys=["job_id", "node_id"])


# ---------------------------------------------------------------- Run Reel
def _same_day_research(job_id: str) -> dict | None:
    """Verified research from TODAY (IST calendar day), produced earlier by the
    5:20 PM cron reel, another conductor reel run, or the carousel pipeline.

    Reusing it is honest — the data covers today's session, every source URL
    and timestamp is preserved unchanged, and the artifact records exactly
    where it came from. STALE (previous-day) research is never reused."""
    import json as _json

    today = datetime.now(IST).strftime("%Y-%m-%d")
    candidates: list[tuple[float, Path, str]] = []
    if REEL_OUTPUT_ROOT.exists():
        for d in REEL_OUTPUT_ROOT.iterdir():
            p = d / "01_research.json"
            if not (d.is_dir() and d.name != job_id and p.exists()):
                continue
            try:
                r = _json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            stamp = str(r.get("retrieved_at") or r.get("date") or "")[:10]
            if stamp == today:
                candidates.append((p.stat().st_mtime, p, f"reel run {d.name}"))
    cp = REPO_ROOT / "outputs" / "maven_instagram" / today / "01_research.json"
    if cp.exists():
        try:
            r = _json.loads(cp.read_text(encoding="utf-8"))
            if str(r.get("date", ""))[:10] == today:
                candidates.append((cp.stat().st_mtime, cp, f"carousel run {today}"))
        except Exception:
            pass
    if not candidates:
        return None
    _, path, src = max(candidates)
    research = _json.loads(path.read_text(encoding="utf-8"))
    research["_meta"] = {**research.get("_meta", {}), "reused_from": src,
                         "reuse_note": "same-day verified research; sources, "
                                       "figures and timestamps unchanged"}
    return {"research": research, "source": src}


def create_reel_job(source: str = "manual_run") -> dict:
    """New unique reel job (fresh folder, unique id). If verified SAME-DAY
    research already exists (cron/conductor/carousel), it is reused — sources
    preserved — and the deterministic pipeline runs immediately, landing at
    'awaiting_scene_generation' with the Generate button live in the UI.
    Only when today has no research at all does the job hold at
    'needs_research' (the backend cannot do live web research itself)."""
    import json as _json

    job_id = new_job_id()
    run_dir = REEL_OUTPUT_ROOT / job_id
    run_dir.mkdir(parents=True, exist_ok=True)

    _clear_latest()
    db.upsert("jobs", {
        "job_id": job_id, "run_type": "reel", "pipeline": "reel",
        "date": job_id.removeprefix("reel-")[:10], "status": "needs_research",
        "current_node": "market_sentinel", "market_status": "open",
        "scheduled_time": "manual", "started_at": _now(), "created_at": _now(),
        "updated_at": _now(), "approval_status": "pending",
        "publish_status": "not_published", "is_latest": 1, "version": 1,
        "parent_job_id": None, "source": source,
        "summary": "New reel run starting…",
    }, conflict_keys=["job_id"])

    bus.emit(job_id, "closing_bell", "reel.run.started",
             f"New reel run {job_id} created (fresh folder, unique id).",
             status="running")
    _set_node(job_id, "closing_bell", status="completed", progress=100,
              started_at=_now(), completed_at=_now(),
              summary="Manual Run Reel trigger.")

    # BACKEND RESEARCH — runs right here, any time of day. Never blocks on the
    # conductor; provider failures surface as a clear config error instead.
    from maven_reels.pipeline import step1_research_backend  # noqa: PLC0415

    _set_node(job_id, "market_sentinel", status="running", started_at=_now(),
              summary="Fetching latest Indian market news (backend providers)…")
    bus.emit(job_id, "market_sentinel", "reel.research.started",
             "Backend research: fetching today's Indian market news "
             "(RSS + configured providers)…", status="running")
    try:
        research = step1_research_backend.run(job_id)
    except Exception as exc:
        research = {"research_status": "failed", "error": str(exc)}
    if research.get("research_status") != "completed":
        err = research.get("error", "unknown research error")
        _set_node(job_id, "market_sentinel", status="failed",
                  completed_at=_now(),
                  summary=f"Research failed: {err}", error=err)
        bus.emit(job_id, "market_sentinel", "reel.research.failed",
                 f"Research failed: {err} "
                 f"({research.get('next_action', 'check provider config')})",
                 status="failed")
        db.upsert("jobs", {"job_id": job_id, "status": "research_failed",
                           "updated_at": _now(),
                           "summary": f"Research failed: {err}"},
                  conflict_keys=["job_id"])
        return {"job_id": job_id, "status": "research_failed",
                "error": err, "next_action": research.get("next_action"),
                "review_url": f"/reels/review/{job_id}"}

    n = len(research.get("candidate_stories", []))
    _set_node(job_id, "market_sentinel", status="completed", progress=100,
              completed_at=_now(),
              summary=(f"{n} candidate stories ({research['data_window']}, "
                       f"sources: {', '.join(research['sources_used'])})."),
              output_artifact="01_research.json")
    bus.emit(job_id, "market_sentinel", "reel.research.completed",
             f"Research completed: {n} candidates | mode {research['data_window']} "
             f"| market {research['market_status']} | sources: "
             f"{', '.join(research['sources_used'])}.", status="completed")
    result = continue_after_research(job_id)
    return {"job_id": job_id, "run_dir": str(run_dir),
            "review_url": f"/reels/review/{job_id}",
            "data_window": research["data_window"],
            "market_status": research["market_status"],
            "sources_used": research["sources_used"], **result}


def continue_after_research(job_id: str, renderer: str | None = None) -> dict:
    """Once 01_research.json exists (conductor dropped it), run the full
    deterministic pipeline. HIGGSFIELD-PRIMARY (default): if clips are not on
    disk yet, STOP at 'awaiting_scene_generation' (paid generation needs the
    UI trigger + conductor — never silent, never auto-rendered by Remotion).
    If clips exist: inspect -> assemble -> audit -> ingest. Remotion renders
    ONLY when explicitly requested (renderer='remotion_fallback')."""
    from maven_reels.pipeline import orchestrator, step_higgsfield_scene_generator  # noqa: PLC0415

    run_dir = REEL_OUTPUT_ROOT / job_id
    if not (run_dir / "01_research.json").exists():
        return {"status": "needs_research", "job_id": job_id}
    prep = orchestrator.prepare(job_id, renderer=renderer)

    if prep.get("renderer") == "remotion_fallback":
        result = _render_and_audit(job_id)   # explicit legacy path only
        ingest_reels.ingest_run(job_id)
        mark_latest(job_id)
        bus.emit(job_id, "reel_auditor", "reel.review.ready",
                 f"Reel (Remotion fallback) ready — verdict {result.get('verdict')}.",
                 status=result.get("verdict", ""))
        return {"status": "ready", "job_id": job_id,
                **{**prep, "verdict": result["verdict"], "scores": result["scores"]}}

    if not step_higgsfield_scene_generator.clips_on_disk(job_id):
        from maven_reels.pipeline import capabilities  # noqa: PLC0415
        caps = capabilities.check()
        # FREE simulation mode (no Higgsfield keys): render the whole reel now —
        # end to end, zero credits, zero Claude Code — for an instant preview.
        if caps["generation_mode"] == "simulation":
            bus.emit(job_id, "higgsfield_scene_generator", "reel.scenes.simulation",
                     "No HIGGSFIELD_API_KEY set — producing a FREE simulation preview "
                     "on the backend. Add the key in Settings for real animated clips.",
                     status="running")
            return run_generation(job_id, simulate=True, prep=prep)
        # REAL generation available: stop for ONE cost confirmation in the UI.
        ingest_reels.ingest_run(job_id)   # ingest FIRST — it overwrites status
        est = prep.get("estimated_generation_cost")
        db.upsert("jobs", {"job_id": job_id, "status": "awaiting_generation_confirmation",
                           "current_node": "higgsfield_scene_generator",
                           "updated_at": _now(),
                           "summary": (f"Ready to generate {prep.get('shots')} animated "
                                       f"clips (~{est}cr). Click Confirm Generation.")},
                  conflict_keys=["job_id"])
        mark_latest(job_id)
        bus.emit(job_id, "higgsfield_scene_generator", "reel.scenes.awaiting",
                 f"Plan ready: {prep.get('shots')} shots, ~{est}cr. Click Confirm "
                 "Generation in the UI — the backend renders it (no Claude Code).",
                 status="requires_user_action")
        return {"status": "awaiting_generation_confirmation", "job_id": job_id,
                "estimated_generation_cost": est, "generation_mode": "real", **prep}

    return assemble_and_audit(job_id, prep=prep)


def run_generation(job_id: str, *, simulate: bool | None = None,
                   prep: dict | None = None) -> dict:
    """Generate the animated clips FROM THE BACKEND, then assemble + audit.

    simulate=None  -> real Higgsfield iff HIGGSFIELD_API_KEY is configured;
    simulate=True  -> free local simulation (used to test wiring / preview).
    This is the localhost 'Confirm Generation' (and free auto-preview) entry
    point. No Claude Code, no MCP — the backend calls Higgsfield's Cloud API
    directly (or synthesizes a preview) and downloads every clip itself.
    """
    from maven_reels.pipeline import (capabilities,  # noqa: PLC0415
                                      orchestrator, state as rstate,
                                      step_higgsfield_scene_generator)
    if prep is None:
        prep = orchestrator.prepare(job_id)
    shot_prompts = rstate.load_artifact(job_id, "shot_prompts")
    mode = "simulation" if (simulate or capabilities.generation_mode() == "simulation") else "real"
    n = len(shot_prompts.get("shot_prompts", []))
    bus.emit(job_id, "higgsfield_scene_generator", "reel.generation.started",
             f"Backend generating {n} animated clips ({mode}).", status="running")

    gen = step_higgsfield_scene_generator.run_backend(
        job_id, shot_prompts=shot_prompts, simulate=simulate)
    done = gen.get("completed_clips", 0)
    bus.emit(job_id, "higgsfield_scene_generator", "reel.generation.completed",
             f"Generated {done}/{done + gen.get('failed_clips', 0)} clips ({mode}); "
             f"{gen.get('actual_cost_credits', 0)}cr spent.",
             status=gen.get("generation_status"))

    # Voiceover on the backend: real TTS when a key is set, else a free
    # simulation placeholder (so the reel isn't blocked on VO in preview).
    try:
        from maven_reels.pipeline import step_voiceover  # noqa: PLC0415
        script_edited = rstate.load_artifact(job_id, "script_edited")
        bus.emit(job_id, "voice_studio", "reel.voiceover.started",
                 "Generating voiceover on the backend.", status="running")
        vo = step_voiceover.run(job_id, script_edited=script_edited, simulate=simulate)
        ev = ("reel.voiceover.simulated" if vo["voiceover_mode"] != "real_tts"
              else "reel.voiceover.completed")
        bus.emit(job_id, "voice_studio", ev,
                 f"Voiceover ready ({vo['voiceover_mode']}, {vo['duration']:.0f}s).",
                 status="completed")
    except Exception as exc:  # VO is non-fatal — assembly falls back to the bed
        bus.emit(job_id, "voice_studio", "reel.voiceover.simulated",
                 f"Voiceover skipped ({str(exc)[:100]}).", status="pending")

    if not step_higgsfield_scene_generator.clips_on_disk(job_id):
        ingest_reels.ingest_run(job_id)
        db.upsert("jobs", {"job_id": job_id, "status": "generation_failed",
                           "updated_at": _now(),
                           "summary": "Clip generation failed — see event log."},
                  conflict_keys=["job_id"])
        mark_latest(job_id)
        return {"status": "generation_failed", "job_id": job_id, **prep}

    return assemble_and_audit(job_id, prep=prep)


def assemble_and_audit(job_id: str, prep: dict | None = None) -> dict:
    """Local + free: inspect clips -> assemble final reel (ffmpeg) -> audit ->
    ingest. Requires Higgsfield clips on disk."""
    from maven_reels.pipeline import (state as rstate,  # noqa: PLC0415
                                       step_final_reel_assembler,
                                       step_scene_quality_inspector, step16_quality)

    def _opt(key):
        try:
            return rstate.load_artifact(job_id, key)
        except FileNotFoundError:
            return None

    scene_gen = rstate.load_artifact(job_id, "scene_generation")
    inspection = step_scene_quality_inspector.run(job_id, scene_generation=scene_gen)
    bus.emit(job_id, "scene_quality_inspector", "reel.scenes.inspected",
             f"Scene quality {inspection['overall_scene_quality_score']}/100 "
             f"({'pass' if inspection['passed'] else 'FAIL: ' + ', '.join(inspection['failed_shots'])}).",
             status="completed" if inspection["passed"] else "failed")

    shot_plan = rstate.load_artifact(job_id, "shot_plan")
    subtitles = rstate.load_artifact(job_id, "subtitles")
    hooks = rstate.load_artifact(job_id, "hooks")
    vo = REEL_OUTPUT_ROOT / job_id / "voiceover.mp3"

    # Text Studio: align all on-screen text to the voiceover, build the premium
    # kinetic plan (hook / synced subtitles / safe areas / animations). Free.
    from maven_reels.pipeline import step_text_studio, step_text_quality  # noqa: PLC0415
    text = step_text_studio.run(job_id, shot_plan=shot_plan,
                                voiceover=_opt("voiceover_v2"),
                                script_edited=_opt("script_edited"))
    bus.emit(job_id, "text_studio", "reel.text.aligned",
             f"Text aligned to voice ({text['alignment']['text_voice_match_score']}% match, "
             f"{len(text['kinetic']['subtitles'])} subtitle cues).", status="completed")

    bus.emit(job_id, "final_reel_assembler", "reel.video.render.started",
             "Assembling final reel (local ffmpeg, zero credits).", status="running")
    meta = step_final_reel_assembler.run(
        job_id, shot_plan=shot_plan, subtitles=subtitles, hooks=hooks,
        voiceover_mp3=str(vo) if vo.exists() else None,
        text_plan=text["kinetic"], text_style=text["style"])
    bus.emit(job_id, "final_reel_assembler", "reel.video.render.completed",
             f"reel.mp4 assembled ({meta['duration']}s, {meta['scene_count']} clips).",
             status="completed")

    text_audit = step_text_quality.run(
        job_id, alignment=text["alignment"], kinetic=text["kinetic"],
        safe_area=text["safe_area"], animations=text["animations"])
    bus.emit(job_id, "text_auditor", "reel.text.audited",
             f"Text quality {text_audit['scores']['overall_text_quality_score']}/100 "
             f"({text_audit['verdict']}).",
             status="completed" if text_audit["passed"] else "failed")

    from maven_reels.pipeline import capabilities as _caps  # noqa: PLC0415
    audit = step16_quality.run(
        job_id, hooks=hooks, script_edited=rstate.load_artifact(job_id, "script_edited"),
        storyboard=rstate.load_artifact(job_id, "storyboard"),
        compliance=rstate.load_artifact(job_id, "compliance"),
        caption=_opt("caption"), subtitles=subtitles, reel_video=meta,
        aesthetic_score=92, asset_picker=_opt("asset_picker"),
        cost_guard=_opt("cost_guard"), research=_opt("research"),
        visual_uniqueness=_opt("visual_uniqueness"), fresh_video=scene_gen,
        viral_fit=_opt("viral_fit"), scene_quality=inspection,
        renderer="higgsfield_primary", voiceover=_opt("voiceover_v2"),
        capabilities_report=_caps.check())
    bus.emit(job_id, "reel_auditor", "reel.audit.viral_completed",
             f"Viral audit: {audit['verdict']} (preview_ready={audit['preview_ready']}, "
             f"production_ready={audit['production_ready']}).", status=audit["verdict"])
    bus.emit(job_id, "reel_auditor", "reel.audit.completed",
             f"Auditor verdict: {audit['verdict']}.", status=audit["verdict"])

    # Editor-in-Chief: holistic executive review (realism / AI-slop / story fit)
    from maven_reels.pipeline import step_editor_in_chief  # noqa: PLC0415
    editor = step_editor_in_chief.run(job_id)
    bus.emit(job_id, "editor_in_chief", "reel.editor.reviewed",
             f"Editor-in-Chief {editor['overall_score']}/100 "
             f"({'PASS' if editor['passed'] else 'HOLD'}): {editor['editor_note'][:100]}",
             status="completed" if editor["passed"] else "failed")

    ingest_reels.ingest_run(job_id)
    mark_latest(job_id)
    bus.emit(job_id, "reel_auditor", "reel.review.ready",
             f"Reel ready for review — verdict {audit['verdict']}.",
             status=audit["verdict"])
    return {"status": "ready", "job_id": job_id, **(prep or {}),
            "verdict": audit["verdict"], "scores": audit["scores"],
            "preview_ready": audit["preview_ready"],
            "production_ready": audit["production_ready"],
            "generation_mode": audit["generation_mode"],
            "voiceover_mode": audit.get("voiceover_mode"),
            "scene_quality": inspection["overall_scene_quality_score"],
            "text_scores": text_audit["scores"], "text_verdict": text_audit["verdict"],
            "editor_score": editor["overall_score"], "editor_passed": editor["passed"],
            "editor_note": editor["editor_note"]}


def improve_text(job_id: str, *, action: str = "improve_text",
                 move_subtitles_up: bool = False) -> dict:
    """Text-only reassembly (FREE, no Higgsfield). Re-aligns text to the voice,
    rebuilds the kinetic plan + premium overlays, reassembles the SAME clips +
    voiceover, and re-audits the text layer. Never regenerates a scene or spends
    a credit — this is 'Improve Text / Resync / Make Text More Viral'."""
    from maven_reels.pipeline import step_higgsfield_scene_generator  # noqa: PLC0415
    if not step_higgsfield_scene_generator.clips_on_disk(job_id):
        return {"status": "no_clips", "job_id": job_id,
                "message": "No Higgsfield clips on disk yet — generate the reel first."}
    bus.emit(job_id, "text_studio", "reel.text.improve.started",
             f"Reassembling text layer only ({action}) — clips + voiceover unchanged, "
             "zero credits.", status="running")
    if move_subtitles_up:
        _nudge_subtitles_up(job_id)
    result = assemble_and_audit(job_id)
    bus.emit(job_id, "text_studio", "reel.text.improve.completed",
             f"Text layer reassembled — text {result.get('text_verdict')}, "
             f"reel {result.get('verdict')}.", status="completed")
    return {"status": "ready", "job_id": job_id, "action": action,
            "text_scores": result.get("text_scores"),
            "text_verdict": result.get("text_verdict"),
            "verdict": result.get("verdict"), "scores": result.get("scores"),
            "credits_spent": 0,
            "message": "Text layer improved and reassembled (no Higgsfield credits used)."}


def _nudge_subtitles_up(job_id: str, extra_px: int = 130) -> None:
    """'Move Subtitles Up' — persist a per-job override that the Text Studio
    reads to raise the subtitle safe_bottom (further from the IG controls).
    Text-only and reversible (delete the file to reset)."""
    import json as _json  # noqa: PLC0415
    from maven_reels.pipeline import config as rcfg  # noqa: PLC0415
    p = rcfg.run_dir(job_id) / "_text_style_override.json"
    cur = 0
    if p.exists():
        try:
            cur = int(_json.loads(p.read_text(encoding="utf-8")).get("subtitle_safe_bottom_extra", 0))
        except Exception:
            cur = 0
    p.write_text(_json.dumps({"subtitle_safe_bottom_extra": cur + extra_px}), encoding="utf-8")


def approve_generation(job_id: str, shot_ids: list[str] | None = None,
                       source: str = "ui") -> dict:
    """UI 'Confirm Generation': the operator confirmed the cost — run generation
    on the backend NOW (real Higgsfield if keys are configured, else a free
    simulation), then assemble + audit. No Claude Code, no MCP."""
    from maven_reels.pipeline import (capabilities,  # noqa: PLC0415
                                      step_higgsfield_scene_generator)
    step_higgsfield_scene_generator.approve_from_ui(job_id, shot_ids=shot_ids, source=source)
    mode = capabilities.generation_mode()
    bus.emit(job_id, "higgsfield_scene_generator", "reel.generation.approved",
             f"Generation confirmed in the UI — backend rendering now ({mode}).",
             status="running")
    return run_generation(job_id, simulate=None)


def improve_animation(job_id: str) -> dict:
    """One-click 'Improve Animation Quality': locally rebuilds direction/plan/
    prompts at HIGH intensity and marks all scenes for regeneration. The paid
    regeneration itself still needs the UI-confirmed approval + conductor."""
    from maven_reels.pipeline import (state as rstate,  # noqa: PLC0415
                                       step_higgsfield_creative_director,
                                       step_higgsfield_prompt_builder,
                                       step_higgsfield_scene_generator,
                                       step_higgsfield_shot_planner,
                                       step_renderer_selector)

    viral = rstate.load_artifact(job_id, "viral_fit")
    story = viral["chosen"]["story"]
    angle = rstate.load_artifact(job_id, "angle")
    hooks = rstate.load_artifact(job_id, "hooks")
    edited = rstate.load_artifact(job_id, "script_edited")

    direction = step_higgsfield_creative_director.run(job_id, story=story,
                                                      angle=angle, hooks=hooks)
    plan = step_higgsfield_shot_planner.run(job_id, story=story, hooks=hooks,
                                            script_edited=edited,
                                            creative_direction=direction)
    prompts = step_higgsfield_prompt_builder.run(job_id, shot_plan=plan,
                                                 creative_direction=direction,
                                                 intensity="high")
    renderer = rstate.load_artifact(job_id, "renderer_selection")
    gen = step_higgsfield_scene_generator.plan(job_id, shot_prompts=prompts,
                                               renderer=renderer)
    bus.emit(job_id, "higgsfield_creative_director", "reel.improvement.started",
             "Animation quality pass: HIGH-intensity prompts rebuilt for all "
             f"{gen['total_clips']} shots (~{gen['estimated_cost_credits']}cr to regenerate).",
             status="requires_user_action")
    return {"status": "prompts_rebuilt", "job_id": job_id,
            "intensity": "high", "shots": gen["total_clips"],
            "estimated_cost_credits": gen["estimated_cost_credits"],
            "requires_confirmation": True,
            "message": "Stronger-motion prompts ready. Confirm regeneration to "
                       "spend credits (executed by the conductor)."}


def _render_and_audit(job_id: str) -> dict:
    """Local Remotion render + sound + cover + strict audit for a run folder."""
    from maven_reels.pipeline import (config as rconfig, state as rstate,  # noqa: PLC0415
                                       step8_motion_graphics, step16_quality)

    bus.emit(job_id, "motion_graphics", "reel.video.render.started",
             "Remotion render started (local, zero credits).", status="running")
    storyboard = rstate.load_artifact(job_id, "storyboard")
    subs = rstate.load_artifact(job_id, "subtitles")
    vo = rconfig.run_dir(job_id) / "voiceover.mp3"
    reel_meta = step8_motion_graphics.build_reel(
        job_id, storyboard, subs.get("subtitles", []),
        str(vo) if vo.exists() else None)
    bus.emit(job_id, "motion_graphics", "reel.video.render.completed",
             f"reel.mp4 rendered ({reel_meta.get('seconds')}s, "
             f"{reel_meta.get('scene_count')} scenes).", status="completed")

    def _opt(key):
        try:
            return rstate.load_artifact(job_id, key)
        except FileNotFoundError:
            return None

    audit = step16_quality.run(
        job_id,
        hooks=rstate.load_artifact(job_id, "hooks"),
        script_edited=rstate.load_artifact(job_id, "script_edited"),
        storyboard=storyboard,
        compliance=rstate.load_artifact(job_id, "compliance"),
        caption=_opt("caption"), subtitles=subs, reel_video=reel_meta,
        aesthetic_score=92, asset_picker=_opt("asset_picker"),
        cost_guard=_opt("cost_guard"), research=_opt("research"),
        visual_uniqueness=_opt("visual_uniqueness"))
    bus.emit(job_id, "reel_auditor", "reel.audit.completed",
             f"Auditor verdict: {audit['verdict']}.", status=audit["verdict"])
    return {"verdict": audit["verdict"], "scores": audit["scores"]}


# ---------------------------------------------------------------- Feedback
def record_feedback(job_id: str, feedback_type: str, custom_feedback: str = "",
                    requested_action: str = "improve_reel") -> dict:
    fb = {
        "feedback_id": f"fb-{uuid.uuid4().hex[:10]}", "job_id": job_id,
        "feedback_type": feedback_type, "custom_feedback": custom_feedback,
        "created_at": _now(), "improvement_job_id": None,
    }
    db.upsert("reel_feedback", fb, conflict_keys=["feedback_id"])
    # also persist next to the run's artifacts (auditable)
    run_dir = REEL_OUTPUT_ROOT / _folder_for(job_id)
    if run_dir.exists():
        import json
        (run_dir / "feedback.json").write_text(json.dumps(
            {**fb, "requested_action": requested_action}, indent=2), encoding="utf-8")
    bus.emit(job_id, "approval", "reel.feedback.received",
             f"Feedback: {feedback_type}" + (f" — {custom_feedback}" if custom_feedback else ""),
             status="feedback", payload=fb)
    return fb


def _folder_for(job_id: str) -> str:
    """DB job ids map 1:1 to folders except legacy 'reel-YYYY-MM-DD' date runs."""
    if (REEL_OUTPUT_ROOT / job_id).exists():
        return job_id
    legacy = job_id.removeprefix("reel-")
    return legacy if (REEL_OUTPUT_ROOT / legacy).exists() else job_id


# ---------------------------------------------------------------- Improve
async def improve(job_id: str, feedback_type: str, custom_feedback: str = "") -> dict:
    """Create an improved version job and (where possible) rebuild it locally."""
    from maven_reels.pipeline import state as rstate  # noqa: PLC0415
    from maven_reels.pipeline import step_reel_improvement_director as director  # noqa: PLC0415

    parent = db.query_one("SELECT * FROM jobs WHERE job_id=?", (job_id,))
    if not parent:
        return {"status": "error", "message": f"job {job_id} not found"}

    fb = record_feedback(job_id, feedback_type, custom_feedback)

    parent_folder = REEL_OUTPUT_ROOT / _folder_for(job_id)
    root = _root_id(job_id)
    version = int(parent.get("version") or 1) + 1
    new_id = f"{root}-v{version}"
    new_dir = REEL_OUTPUT_ROOT / new_id

    # copy the parent's artifacts; the improvement steps overwrite what changes
    if new_dir.exists():
        shutil.rmtree(new_dir, ignore_errors=True)
    shutil.copytree(parent_folder, new_dir)

    quality = None
    try:
        quality = rstate.load_artifact(_folder_for(job_id), "quality")
    except FileNotFoundError:
        pass
    plan = director.run(new_id, feedback_type=feedback_type,
                        custom_feedback=custom_feedback, quality=quality)

    _clear_latest()
    db.upsert("jobs", {
        "job_id": new_id, "run_type": "reel", "pipeline": "reel",
        "date": parent.get("date"), "status": "improving",
        "current_node": plan["reroute_to"][0] if plan["reroute_to"] else "motion_graphics",
        "market_status": parent.get("market_status") or "open",
        "scheduled_time": "improvement", "started_at": _now(), "created_at": _now(),
        "updated_at": _now(), "approval_status": "pending",
        "publish_status": "not_published", "is_latest": 1, "version": version,
        "parent_job_id": job_id, "source": f"improve:{feedback_type}",
        "summary": f"v{version}: {plan['next_version_strategy']}",
    }, conflict_keys=["job_id"])
    db.upsert("reel_versions", {
        "job_id": new_id, "root_job_id": root, "version": version,
        "parent_job_id": job_id, "improvement_reason": feedback_type,
        "created_at": _now(), "scores_json": db.dumps((quality or {}).get("scores", {})),
    }, conflict_keys=["job_id"])
    db.upsert("reel_feedback", {**fb, "improvement_job_id": new_id},
              conflict_keys=["feedback_id"])
    bus.emit(new_id, None, "reel.improvement.started",
             f"Improvement v{version} from {job_id}: {plan['next_version_strategy']}",
             status="improving", payload=plan["improvement_plan"])
    bus.emit(new_id, None, "reel.version.created",
             f"Version {version} created (parent {job_id}).", status="created")

    if plan["locally_completable"]:
        asyncio.create_task(_run_improvement(new_id, job_id, plan))
        return {"status": "improving", "new_job_id": new_id, "version": version,
                "plan": plan["improvement_plan"],
                "review_url": f"/reels/review/{new_id}"}

    # fresh research / new voiceover need the conductor — say so, never fake
    needs = ", ".join(plan["needs_conductor"])
    db.upsert("jobs", {"job_id": new_id, "status": "needs_conductor",
                       "summary": f"v{version} waiting on conductor: {needs}",
                       "updated_at": _now()}, conflict_keys=["job_id"])
    for nid in plan["needs_conductor"]:
        if nid in REEL_NODES_BY_ID:
            _set_node(new_id, nid, status="pending",
                      summary="Requires Claude Code conductor.")
    return {"status": "needs_conductor", "new_job_id": new_id, "version": version,
            "needs": plan["needs_conductor"], "plan": plan["improvement_plan"],
            "review_url": f"/reels/review/{new_id}",
            "message": f"Version created; {needs} require the Claude Code conductor."}


async def _run_improvement(new_id: str, parent_id: str, plan: dict) -> None:
    """Re-run the planned deterministic steps + local render in a worker thread."""
    try:
        await asyncio.to_thread(_improvement_steps, new_id, parent_id, plan)
        ingest_reels.ingest_run(new_id)
        mark_latest(new_id)
        db.upsert("jobs", {"job_id": new_id, "status": "completed",
                           "updated_at": _now()}, conflict_keys=["job_id"])
        bus.emit(new_id, "reel_auditor", "reel.review.ready",
                 f"Improved version {new_id} ready for review.", status="ready")
    except Exception as exc:  # pragma: no cover
        db.upsert("jobs", {"job_id": new_id, "status": "failed",
                           "summary": f"Improvement failed: {exc}",
                           "updated_at": _now()}, conflict_keys=["job_id"])
        bus.emit(new_id, None, "reel.improvement.failed", f"Improvement failed: {exc}",
                 status="failed")


def _improvement_steps(new_id: str, parent_id: str, plan: dict) -> None:
    from maven_reels.pipeline import (state as rstate,  # noqa: PLC0415
                                       step_asset_picker, step_motion_variation,
                                       step_template_selector, step_visual_uniqueness,
                                       step6_motion_storyboard, step11_subtitles)

    rerun = set(plan["improvement_plan"]["rerun_steps"])
    viral = rstate.load_artifact(new_id, "viral_fit")
    story = viral["chosen"]["story"]
    hooks = rstate.load_artifact(new_id, "hooks")
    angle = rstate.load_artifact(new_id, "angle")
    edited = rstate.load_artifact(new_id, "script_edited")

    def _opt(key):
        try:
            return rstate.load_artifact(new_id, key)
        except FileNotFoundError:
            return None

    template = _opt("template")
    variation = _opt("motion_variation")
    parent_variation = (variation or {}).get("variation_id")

    if "template_selector" in rerun:
        template = step_template_selector.run(new_id, story=story, angle=angle)
    if "motion_variation" in rerun:
        # force a DIFFERENT look from the parent version
        variation = step_motion_variation.run(
            new_id, template=None,
            avoid=[parent_variation] if parent_variation else [])
    if "motion_storyboard" in rerun or "motion_variation" in rerun:
        bus.emit(new_id, "motion_storyboard", "reel.assets.selected",
                 "Re-storyboarding with new variation.", status="running")
        storyboard = step6_motion_storyboard.run(
            new_id, story=story, hooks=hooks, script_edited=edited,
            viral_fit=viral, template=template, variation=variation)
    else:
        storyboard = rstate.load_artifact(new_id, "storyboard")
    if "asset_picker" in rerun:
        picker = step_asset_picker.run(new_id, storyboard=storyboard,
                                       template=template, story=story)
        bus.emit(new_id, "asset_picker", "reel.assets.selected",
                 f"{len(picker['selected_assets'])} library assets picked "
                 "(0 paid generations).", status="completed")
    if "subtitle_engine" in rerun:
        step11_subtitles.run(new_id, edited)
    step_visual_uniqueness.run(new_id, template=template, variation=variation,
                               storyboard=storyboard, asset_picker=_opt("asset_picker"))
    _render_and_audit(new_id)


# ---------------------------------------------------------------- Latest
def latest_job() -> dict | None:
    job = db.query_one(
        "SELECT * FROM jobs WHERE pipeline='reel' AND is_latest=1 LIMIT 1")
    if not job:
        job = db.query_one(
            "SELECT * FROM jobs WHERE pipeline='reel' AND job_id NOT LIKE 'reel-sim-%' "
            "ORDER BY created_at DESC LIMIT 1")
    return job


def staleness(job_id: str) -> dict:
    """Verify the artifacts shown for a job actually belong to its folder."""
    folder = REEL_OUTPUT_ROOT / _folder_for(job_id)
    video = folder / "reel.mp4"
    quality = folder / "16_quality.json"
    problems = []
    if not folder.exists():
        problems.append("run folder missing")
    if not video.exists():
        problems.append("reel.mp4 missing")
    if not quality.exists():
        problems.append("quality report missing")
    if video.exists() and quality.exists() and \
            abs(video.stat().st_mtime - quality.stat().st_mtime) > 6 * 3600:
        problems.append("video and quality report were built hours apart (stale artifact)")
    return {"stale": bool(problems), "problems": problems, "folder": str(folder)}
