"""Native Photo Reel Slides routes (/api/photo-reels/*).

The rebuilt Reels framework: 5 individual 1080x1920 images for Instagram's
NATIVE photo Reel flow (manual upload, default) with an optional, explicit
slideshow-MP4 path for automated publishing. Fully separate from the
carousel routes and from the legacy video-reel routes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import FileResponse

from ..config import REPO_ROOT

# same bootstrap as services/reel_studio.py — the server starts from
# maven-newsroom/backend, so the repo root must be importable first
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from maven_reels.photo_slides import config as ps_config  # noqa: E402
from maven_reels.photo_slides import orchestrator as ps
from maven_reels.photo_slides import state as ps_state

router = APIRouter(prefix="/api/photo-reels")

_BODY = Body(default={})      # module-level singletons (ruff B008)
_BODY_REQUIRED = Body(...)

_CRON_OVERRIDE = ps_config.OUTPUT_ROOT / "_cron.json"


def _cron_enabled() -> bool:
    if _CRON_OVERRIDE.exists():
        try:
            return bool(json.loads(_CRON_OVERRIDE.read_text(encoding="utf-8"))
                        .get("enabled", False))
        except (json.JSONDecodeError, OSError):
            return False
    return ps_config.REEL_IMAGE_SLIDES_CRON_ENABLED


@router.get("/config")
def get_config() -> dict[str, Any]:
    return {
        "module": "native_photo_reel_slides",
        "enabled": ps_config.REEL_IMAGE_SLIDES_ENABLED,
        "primary_reels_mode": ps_config.PRIMARY_REELS_MODE,
        "default_publish_mode": ps_config.DEFAULT_REEL_PUBLISH_MODE,
        "publish_modes": list(ps_config.PUBLISH_MODES),
        "allow_auto_reel_video_mode": ps_config.ALLOW_AUTO_REEL_VIDEO_MODE,
        "legacy_reels_ui_enabled": ps_config.LEGACY_REELS_UI_ENABLED,
        "legacy_reels_cron_enabled": ps_config.LEGACY_REELS_CRON_ENABLED,
        "reel_image_slides_cron_enabled": _cron_enabled(),
        "disable_remotion_for_reels": ps_config.DISABLE_REMOTION_FOR_REELS,
        "allow_local_text_fallback": ps_config.ALLOW_LOCAL_TEXT_FALLBACK,
        "require_higgsfield_credit_confirmation":
            ps_config.REQUIRE_HIGGSFIELD_CREDIT_CONFIRMATION,
        "slide_count": ps_config.SLIDE_COUNT,
        "slide_size": [ps_config.SLIDE_W, ps_config.SLIDE_H],
        "styles": list(ps_config.STYLE_VARIANTS),
        "pipeline_stages": [{"key": k, "name": n} for k, n in ps.PIPELINE_STAGES],
    }


@router.post("/cron/stop")
def cron_stop() -> dict[str, Any]:
    ps_config.OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    _CRON_OVERRIDE.write_text(json.dumps({"enabled": False}), encoding="utf-8")
    return {"reel_image_slides_cron_enabled": False,
            "legacy_reels_cron_enabled": ps_config.LEGACY_REELS_CRON_ENABLED,
            "note": "Photo-reel cron is OFF. The carousel cron is untouched."}


@router.post("/run")
def run(body: dict[str, Any] = _BODY) -> dict[str, Any]:
    """Full pipeline (default) or research-only. Zero credits unless the
    operator explicitly confirms Higgsfield generation."""
    if not ps_config.REEL_IMAGE_SLIDES_ENABLED:
        raise HTTPException(409, "REEL_IMAGE_SLIDES_ENABLED is off")
    allow_sim = bool(body.get("allow_simulation", False))
    if body.get("research_only"):
        return ps.run_research(allow_simulation=allow_sim)
    return ps.run_full(
        allow_simulation=allow_sim,
        style_name=body.get("style", ps_config.DEFAULT_STYLE),
        use_higgsfield=bool(body.get("use_higgsfield", False)),
        credit_confirmed=bool(body.get("credit_confirmed", False)))


@router.get("/packages")
def packages() -> dict[str, Any]:
    out = []
    for jid in ps_state.list_jobs():
        pkg = ps_state.get_package(jid)
        sel = ps_state.load_artifact(jid, "story_selector") or {}
        qa = ps_state.load_artifact(jid, "qa_gate") or {}
        out.append({"job_id": jid, "status": pkg.get("status"),
                    "headline": (sel.get("selected_story") or {}).get("headline"),
                    "qa_passed": qa.get("passed"),
                    "qa_score": qa.get("overall_score"),
                    "permalink": pkg.get("permalink"),
                    "created": jid.removeprefix("slides-")})
    return {"packages": out}


@router.get("/packages/latest")
def latest() -> dict[str, Any]:
    jobs = ps_state.list_jobs()
    if not jobs:
        raise HTTPException(404, "no photo-reel packages yet")
    return ps.package(jobs[0])


@router.get("/packages/{job_id}")
def package(job_id: str) -> dict[str, Any]:
    _require(job_id)
    return ps.package(job_id)


@router.post("/packages/{job_id}/generate-images")
def generate_images(job_id: str, body: dict[str, Any] = _BODY) -> dict[str, Any]:
    _require(job_id)
    return ps.generate_images(
        job_id, use_higgsfield=bool(body.get("use_higgsfield", False)),
        credit_confirmed=bool(body.get("credit_confirmed", False)),
        style_name=body.get("style"))


@router.post("/packages/{job_id}/slides/{n}/regenerate")
def regenerate_slide(job_id: str, n: int, body: dict[str, Any] = _BODY) -> dict[str, Any]:
    _require(job_id)
    try:
        return ps.regenerate_slide(job_id, n, title=body.get("title"),
                                   body=body.get("body"),
                                   style_name=body.get("style"))
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/packages/{job_id}/decision")
def decision(job_id: str, body: dict[str, Any] = _BODY_REQUIRED) -> dict[str, Any]:
    _require(job_id)
    try:
        return ps.decision(job_id, body.get("decision", ""), body.get("reason"))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/packages/{job_id}/export")
def export(job_id: str) -> dict[str, Any]:
    _require(job_id)
    try:
        return ps.mark_exported(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/packages/{job_id}/mark-posted")
def mark_posted(job_id: str, body: dict[str, Any] = _BODY) -> dict[str, Any]:
    """Manual mode: operator confirms they posted the native photo Reel."""
    _require(job_id)
    return ps.mark_posted_manually(job_id, body.get("permalink"))


@router.post("/packages/{job_id}/render-video")
def render_video(job_id: str) -> dict[str, Any]:
    """EXPLICIT opt-in: slideshow MP4 for the automated Reel publish mode."""
    _require(job_id)
    if not ps_config.ALLOW_AUTO_REEL_VIDEO_MODE:
        raise HTTPException(409, "ALLOW_AUTO_REEL_VIDEO_MODE is off")
    from maven_reels.photo_slides.step06b_video_renderer import VideoRenderError
    try:
        return ps.render_video(job_id)
    except (VideoRenderError, PermissionError) as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/packages/{job_id}/publish-confirm")
def publish_confirm(job_id: str, body: dict[str, Any] = _BODY) -> dict[str, Any]:
    """Auto (MP4) mode only — refuses without a REAL media id/permalink."""
    _require(job_id)
    try:
        return ps.confirm_video_published(job_id, body.get("media_id"),
                                          body.get("permalink"))
    except PermissionError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/packages/{job_id}/slides/{n}.png")
def slide_png(job_id: str, n: int) -> FileResponse:
    p = ps.slide_image_path(job_id, n)
    if not p.exists():
        raise HTTPException(404, f"slide {n} not rendered")
    return FileResponse(p, media_type="image/png")


@router.get("/packages/{job_id}/cover")
def cover(job_id: str) -> FileResponse:
    exp = ps_state.load_artifact(job_id, "export") or {}
    p = Path(exp.get("cover_image") or "")
    if not exp.get("cover_image") or not p.exists():
        raise HTTPException(404, "no cover exported")
    return FileResponse(p, media_type="image/png")


@router.get("/packages/{job_id}/zip")
def zip_download(job_id: str) -> FileResponse:
    exp = ps_state.load_artifact(job_id, "export") or {}
    p = Path(exp.get("zip_path") or "")
    if not exp.get("zip_path") or not p.exists():
        raise HTTPException(404, "no export ZIP — run export first")
    return FileResponse(p, media_type="application/zip", filename=p.name)


def _require(job_id: str) -> None:
    if not (ps_config.OUTPUT_ROOT / job_id).is_dir():
        raise HTTPException(404, f"package {job_id} not found")
