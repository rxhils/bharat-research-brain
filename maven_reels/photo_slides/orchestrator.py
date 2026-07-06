"""Agent 10 — Review + Export Queue orchestration.

Deterministic pipeline driver for the Native Photo Reel Slides framework.
Default output is 5 images for MANUAL Instagram upload; the MP4 path exists
only for the explicit auto-publish mode. Publishing is never marked without
a real Instagram media id/permalink (auto) or the operator's own
"posted manually" confirmation (manual).
"""
from __future__ import annotations

from pathlib import Path

from . import (
    config,
    state,
    step01_market_radar,
    step02_fact_check,
    step03_story_selector,
    step04_slide_script,
    step05_slide_design,
    step06_exporter,
    step06b_video_renderer,
    step07_music_scout,
    step08_qa_gate,
)

PIPELINE_STAGES = [
    ("market_radar", "Market Radar"),
    ("fact_check", "Fact Check Desk"),
    ("story_selector", "Story Selector"),
    ("slide_script", "5-Slide Scriptwriter"),
    ("slide_design", "Higgsfield Image Designer"),
    ("export", "Native Photo Reel Exporter"),
    ("music_scout", "Music Scout"),
    ("qa_gate", "QA Gate"),
    ("package", "Review + Export Queue"),
]


def run_research(job_id: str | None = None, *,
                 allow_simulation: bool = False) -> dict:
    job_id = job_id or config.new_job_id()
    state.update_package(job_id, status="draft",
                         publish_mode=config.DEFAULT_REEL_PUBLISH_MODE)
    radar = step01_market_radar.run(job_id, allow_simulation=allow_simulation)
    step02_fact_check.run(job_id)
    sel = step03_story_selector.run(job_id)
    if sel.get("status") != "selected":
        state.update_package(job_id, status="blocked",
                             block_reason=sel.get("note", "no verified story"))
    return {"job_id": job_id, "data_mode": radar.get("data_mode"),
            "candidates": len(radar.get("candidate_stories", [])),
            "selected": sel.get("selected_story", {}).get("headline"),
            "status": state.get_package(job_id)["status"]}


def run_full(job_id: str | None = None, *, allow_simulation: bool = False,
             style_name: str = config.DEFAULT_STYLE,
             use_higgsfield: bool = False,
             credit_confirmed: bool = False) -> dict:
    r = run_research(job_id, allow_simulation=allow_simulation)
    job_id = r["job_id"]
    if state.get_package(job_id)["status"] == "blocked":
        return {**r, "note": "run blocked before scripting — nothing fabricated"}

    step04_slide_script.run(job_id)
    step05_slide_design.run(job_id, use_higgsfield=use_higgsfield,
                            credit_confirmed=credit_confirmed,
                            style_name=style_name)
    step07_music_scout.run(job_id)
    step06_exporter.run(job_id)
    qa = step08_qa_gate.run(job_id)
    state.update_package(job_id, status="needs_review",
                         qa_passed=qa["passed"], qa_score=qa["overall_score"])
    return {**r, "qa": {"passed": qa["passed"], "overall": qa["overall_score"]},
            "status": "needs_review"}


def generate_images(job_id: str, *, use_higgsfield: bool = False,
                    credit_confirmed: bool = False,
                    style_name: str | None = None) -> dict:
    prev = state.load_artifact(job_id, "slide_design") or {}
    design = step05_slide_design.run(
        job_id, use_higgsfield=use_higgsfield, credit_confirmed=credit_confirmed,
        style_name=style_name or prev.get("style", config.DEFAULT_STYLE))
    step06_exporter.run(job_id)
    qa = step08_qa_gate.run(job_id)
    state.update_package(job_id, qa_passed=qa["passed"],
                         qa_score=qa["overall_score"])
    return {"job_id": job_id, "images": design.get("generated_images", []),
            "higgsfield_note": design.get("higgsfield_note"),
            "credits_spent": design.get("credits_spent", False),
            "qa": {"passed": qa["passed"], "overall": qa["overall_score"]}}


def regenerate_slide(job_id: str, slide_number: int, *,
                     title: str | None = None, body: str | None = None,
                     style_name: str | None = None) -> dict:
    """Edit text and/or re-render ONE slide (local compositor, zero credits)."""
    script = state.load_artifact(job_id, "slide_script")
    if not script or not script.get("slides"):
        raise FileNotFoundError("no slide script for this package")
    if not any(s["slide_number"] == slide_number for s in script["slides"]):
        raise ValueError(f"slide {slide_number} not in 1-{config.SLIDE_COUNT}")
    for s in script["slides"]:
        if s["slide_number"] == slide_number:
            if title is not None:
                s["title"] = " ".join(title.split()[:config.TITLE_MAX_WORDS])
            if body is not None:
                s["body"] = " ".join(body.split()[:config.BODY_MAX_WORDS])
    state.save_artifact(job_id, "slide_script", script)

    prev = state.load_artifact(job_id, "slide_design") or {}
    step05_slide_design.run(
        job_id, style_name=style_name or prev.get("style", config.DEFAULT_STYLE),
        only_slides=[slide_number])
    step06_exporter.run(job_id)
    qa = step08_qa_gate.run(job_id)
    state.update_package(job_id, qa_passed=qa["passed"],
                         qa_score=qa["overall_score"])
    return {"job_id": job_id, "slide_number": slide_number,
            "qa": {"passed": qa["passed"], "overall": qa["overall_score"]}}


def decision(job_id: str, verdict: str, reason: str | None = None) -> dict:
    if verdict not in ("approve", "reject", "revise"):
        raise ValueError("decision must be approve|reject|revise")
    qa = state.load_artifact(job_id, "qa_gate") or {}
    if verdict == "approve" and not qa.get("passed"):
        raise PermissionError("cannot approve a package that has not passed QA")
    status = {"approve": "approved", "reject": "rejected",
              "revise": "revise_requested"}[verdict]
    pkg = state.update_package(job_id, status=status, decision=verdict,
                               decision_reason=reason)
    return {"job_id": job_id, "status": pkg["status"]}


def mark_exported(job_id: str) -> dict:
    exp = state.load_artifact(job_id, "export") or {}
    if exp.get("status") != "exported":
        exp = step06_exporter.run(job_id)
    if exp.get("status") != "exported":
        raise FileNotFoundError(exp.get("note", "export failed"))
    pkg = state.update_package(job_id, status="exported")
    return {"job_id": job_id, "status": pkg["status"],
            "zip_path": exp["zip_path"]}


def mark_posted_manually(job_id: str, permalink: str | None = None) -> dict:
    """Operator confirms they uploaded the native photo Reel themselves."""
    pkg = state.update_package(job_id, status="posted_manually",
                               permalink=permalink or None)
    return {"job_id": job_id, "status": pkg["status"], "permalink": permalink}


def render_video(job_id: str) -> dict:
    """Explicit opt-in slideshow MP4 for the auto-publish mode."""
    if config.DEFAULT_REEL_PUBLISH_MODE == "native_photo_reel_manual" \
            and not config.ALLOW_AUTO_REEL_VIDEO_MODE:
        raise PermissionError("auto video mode is disabled")
    out = step06b_video_renderer.run(job_id)
    state.update_package(job_id, status="queued_for_auto_video",
                         video_path=out["video_path"])
    return out


def confirm_video_published(job_id: str, media_id: str | None,
                            permalink: str | None) -> dict:
    """Auto mode only — refuses without a REAL Instagram media id/permalink."""
    if not media_id and not permalink:
        raise PermissionError("publish not confirmed: a real Instagram media_id "
                              "or permalink is required")
    pkg = state.update_package(job_id, status="published_video_reel",
                               media_id=media_id, permalink=permalink)
    return {"job_id": job_id, "status": pkg["status"],
            "media_id": media_id, "permalink": permalink}


def package(job_id: str) -> dict:
    """Aggregate view for the UI: story, script, images, QA, export, music."""
    pkg = state.get_package(job_id)
    sel = state.load_artifact(job_id, "story_selector") or {}
    script = state.load_artifact(job_id, "slide_script") or {}
    design = state.load_artifact(job_id, "slide_design") or {}
    qa = state.load_artifact(job_id, "qa_gate") or {}
    exp = state.load_artifact(job_id, "export") or {}
    radar = state.load_artifact(job_id, "market_radar") or {}
    stages = {}
    for key, name in PIPELINE_STAGES:
        art = state.load_artifact(job_id, key)
        stages[key] = {"name": name,
                       "done": art is not None,
                       "status": (art or {}).get("status")}
    return {
        "job_id": job_id,
        "package": pkg,
        "data_mode": radar.get("data_mode"),
        "top_sectors_or_themes": radar.get("top_sectors_or_themes", []),
        "selected_story": sel.get("selected_story") or {},
        "why_selected": sel.get("why_selected", ""),
        "slides": script.get("slides", []),
        "caption": script.get("caption", ""),
        "hashtags": script.get("hashtags", []),
        "slide_prompts": design.get("slide_prompts", []),
        "generated_images": design.get("generated_images", []),
        "style": design.get("style"),
        "qa": qa,
        "export": {k: exp.get(k) for k in ("status", "zip_path", "image_paths",
                                           "cover_image", "recommended_order")},
        "music": state.load_artifact(job_id, "music_scout") or {},
        "instagram_manual_steps": config.INSTAGRAM_MANUAL_STEPS,
        "stages": stages,
        "video_render": state.load_artifact(job_id, "video_render"),
    }


def slide_image_path(job_id: str, slide_number: int) -> Path:
    return state.slides_dir(job_id) / f"slide_{slide_number}.png"
