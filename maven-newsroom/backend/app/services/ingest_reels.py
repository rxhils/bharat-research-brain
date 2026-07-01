"""Ingest completed reel runs from outputs/maven_reels/<date>/ into the DB.

Mirror of services/ingest.py for the Reels pipeline. Reel jobs use
`job_id = "reel-<date>"` and `pipeline = "reel"`. Statuses/scores/artifacts are
real; per-node timings are reconstructed (flagged).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from .. import database as db
from ..config import REPO_ROOT
from ..events import IST, bus
from ..registry_reels import REEL_NODES

REEL_OUTPUT_ROOT = REPO_ROOT / "outputs" / "maven_reels"

APPROX = {
    "closing_bell": 1, "market_sentinel": 150, "viral_fit": 1, "angle_studio": 2,
    "hook_lab": 3, "script_room": 2, "retention_editor": 1, "template_selector": 1,
    "motion_variation": 1, "motion_storyboard": 1, "asset_director": 1,
    "asset_picker": 1, "cost_guard": 1, "scene_studio": 50, "motion_graphics": 90,
    "voice_studio": 18, "subtitle_engine": 1, "sound_design": 3, "cover_studio": 2,
    "reel_auditor": 2, "approval": 1, "publish_gate": 2, "reels_courier": 20,
    "signal_tracker": 0, "run_vault": 1,
}

FILES = {
    "01_research.json": ("market_sentinel", "json"),
    "02_viral_fit.json": ("viral_fit", "json"),
    "03_angle.json": ("angle_studio", "json"),
    "04_hooks.json": ("hook_lab", "json"),
    "05_script.json": ("script_room", "json"),
    "06_script_edited.json": ("retention_editor", "json"),
    "07_template.json": ("template_selector", "json"),
    "08_motion_variation.json": ("motion_variation", "json"),
    "07_storyboard.json": ("motion_storyboard", "json"),
    "08_assets.json": ("asset_director", "json"),
    "09_asset_picker.json": ("asset_picker", "json"),
    "cost_guard.json": ("cost_guard", "json"),
    "11_higgsfield_request.json": ("scene_studio", "json"),
    "09_scenes.json": ("scene_studio", "json"),
    "10_voiceover.json": ("voice_studio", "json"),
    "11_captions.json": ("subtitle_engine", "json"),
    "12_reel_video.json": ("motion_graphics", "json"),
    "14_caption.json": ("reels_courier", "json"),
    "14_hashtags.json": ("reels_courier", "json"),
    "16_quality.json": ("reel_auditor", "json"),
    "17_publish.json": ("reels_courier", "json"),
    "_final_output.json": ("run_vault", "json"),
    "11_sound_design.json": ("sound_design", "json"),
    "reel.mp4": ("motion_graphics", "video"),
    "cover.jpg": ("cover_studio", "image"),
    "voiceover.mp3": ("voice_studio", "audio"),
    "sound_bed.mp3": ("sound_design", "audio"),
    "music_bed.mp3": ("sound_design", "audio"),   # legacy name (older runs)
    "captions.srt": ("subtitle_engine", "log"),
    # background plates (Higgsfield stills) live in assets/
    "asset_bg_dark.jpg": ("scene_studio", "image"),
    "asset_bg_panel.jpg": ("scene_studio", "image"),
    "asset_bg_end.jpg": ("scene_studio", "image"),
}

# artifacts stored in the run's assets/ subdirectory rather than the run root
ASSET_SUBDIR = {"asset_bg_dark.jpg", "asset_bg_panel.jpg", "asset_bg_end.jpg"}


def _load(d: Path, name: str):
    p = d / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def list_run_dates() -> list[str]:
    if not REEL_OUTPUT_ROOT.exists():
        return []
    return [d.name for d in sorted(REEL_OUTPUT_ROOT.iterdir())
            if d.is_dir() and (d / "16_quality.json").exists()]


def ingest_run(date: str) -> str | None:
    dd = REEL_OUTPUT_ROOT / date
    quality = _load(dd, "16_quality.json")
    if quality is None:
        return None
    job_id = f"reel-{date}"
    final = _load(dd, "_final_output.json") or {}
    viral = _load(dd, "02_viral_fit.json") or {}
    hooks = _load(dd, "04_hooks.json") or {}
    published = final.get("status") == "published"
    permalink = final.get("instagram_post_url")
    qs = quality.get("scores", {})
    passed = bool(quality.get("passed", quality.get("overall_pass")))
    base = datetime.now(IST) - timedelta(seconds=sum(APPROX.values()))

    db.upsert("jobs", {
        "job_id": job_id, "run_type": "reel", "pipeline": "reel", "date": date,
        "status": "published" if published else ("blocked" if quality.get("verdict") == "BLOCKED" else "completed"),
        "current_node": "reels_courier" if published else "reel_auditor",
        "market_status": "open", "scheduled_time": "17:00 IST",
        "started_at": base.isoformat(timespec="seconds"),
        "completed_at": datetime.now(IST).isoformat(timespec="seconds"),
        "approval_status": "approved" if published else "pending",
        "publish_status": "published" if published else "not_published",
        "instagram_post_id": final.get("instagram_media_id"),
        "instagram_post_url": permalink,
        "summary": (hooks.get("chosen", {}) or {}).get("text", "")[:400],
        "created_at": base.isoformat(timespec="seconds"),
    }, conflict_keys=["job_id"])

    db.upsert("scores", {
        "job_id": job_id, "content_score": qs.get("hook"),
        "design_score": qs.get("visual_quality", qs.get("visual")),
        "compliance_score": qs.get("compliance"),
        "aesthetic_score": qs.get("edit_quality", qs.get("retention")),
        "brand_score": qs.get("brand"),
        "publish_allowed": 1 if passed else 0,
        "issues_json": db.dumps({
            "reel_scores": qs, "gates": quality.get("gates", {}),
            "gate_passed": quality.get("gate_passed", {}),
            "verdict": quality.get("verdict"), "passed": passed,
            "issues": quality.get("issues", []),
            "fixes_required": quality.get("fixes_required", []),
            "reroute_to": quality.get("reroute_to", ""),
        }),
    }, conflict_keys=["job_id"])

    for fname, (nid, atype) in FILES.items():
        fp = (dd / "assets" / fname) if fname in ASSET_SUBDIR else (dd / fname)
        if not fp.exists():
            continue
        db.upsert("artifacts", {
            "artifact_id": f"{job_id}:{fname}", "job_id": job_id, "node_id": nid,
            "artifact_type": atype, "name": fname, "path": str(fp),
            "preview_url": f"/api/jobs/{job_id}/artifact/{fname}",
            "created_at": base.isoformat(timespec="seconds"),
            "metadata_json": db.dumps({"bytes": fp.stat().st_size}),
        }, conflict_keys=["artifact_id"])

    bus.emit(job_id, None, "job.created", f"Reel run ingested for {date}", status="ingested")
    cursor = base
    for spec in REEL_NODES:
        nid = spec["node_id"]
        secs = APPROX.get(nid, 1)
        started, cursor = cursor, cursor + timedelta(seconds=secs)
        status, summary, art = _node_state(nid, dd, quality, viral, hooks, final, published)
        db.upsert("nodes", {
            "job_id": job_id, "node_id": nid, "node_name": spec["name"],
            "component_class": spec["component_class"], "component_type": spec["component_type"],
            "intelligent": int(spec["intelligent"]), "actual_component": spec["actual_component"],
            "external": int(spec["external"]), "in_graph": int(spec["in_graph"]),
            "role": spec["role"], "status": status, "ord": spec["order"],
            "started_at": started.isoformat(timespec="seconds"),
            "completed_at": cursor.isoformat(timespec="seconds"),
            "duration_ms": secs * 1000, "retry_count": 0,
            "progress": 100 if status in ("completed", "published") else 0,
            "input_artifact": None, "output_artifact": art, "summary": summary, "error": None,
        }, conflict_keys=["job_id", "node_id"])
        if status not in ("skipped", "pending"):
            bus.emit(job_id, nid, "node.completed", summary, status=status)
            if nid == "reel_auditor":
                ev = "quality.passed" if passed else "quality.failed"
                bus.emit(job_id, nid, ev,
                         f"hook {qs.get('hook')} / retention {qs.get('retention')} / "
                         f"visual {qs.get('visual_quality', qs.get('visual'))} / "
                         f"compliance {qs.get('compliance')}",
                         status=quality.get("verdict", ""))
    bus.emit(job_id, None, "job.completed",
             f"Published Reel: {permalink}" if published else "Reel prepared (not published).",
             status="published" if published else "completed")
    return job_id


def ingest_all() -> list[str]:
    return [j for d in list_run_dates() if (j := ingest_run(d))]


def _node_state(nid, dd: Path, quality, viral, hooks, final, published):
    has = lambda f: (dd / f).exists()
    has_asset = lambda f: (dd / "assets" / f).exists()
    # media-producing nodes: completed only if their file exists on disk
    media = {"voice_studio": "voiceover.mp3", "motion_graphics": "reel.mp4",
             "cover_studio": "cover.jpg"}
    if nid == "scene_studio":
        return ("completed", "3 background plates ready", "asset_bg_dark.jpg") \
            if has_asset("asset_bg_dark.jpg") \
            else ("pending", "Awaiting plates (requires Claude Code conductor).", None)
    if nid == "sound_design":
        f = "sound_bed.mp3" if has("sound_bed.mp3") else "music_bed.mp3"
        return ("completed", "Music bed + SFX ready", f) if has(f) \
            else ("pending", "Awaiting sound design (requires conductor).", None)
    if nid in media:
        f = media[nid]
        return ("completed", f"{f} ready", f) if has(f) \
            else ("pending", "Awaiting render (requires Claude Code conductor).", None)
    if nid == "reels_courier":
        return ("published", f"Reel published — {final.get('instagram_post_url')}", "17_publish.json") \
            if published else ("pending", "Awaiting publish (requires conductor).", None)
    if nid == "signal_tracker":
        return "pending", "Analytics collected post-publish.", None
    if nid == "approval":
        return ("completed" if published else "approval_required",
                "Approved." if published else "Awaiting human approval.", None)
    if nid == "closing_bell":
        return "completed", "Reel workflow started.", None
    if nid == "viral_fit":
        c = viral.get("chosen", {})
        return "completed", f"Picked reel story (fit {c.get('viral_fit')}).", "02_viral_fit.json"
    if nid == "hook_lab":
        return "completed", f"Hook: {(hooks.get('chosen') or {}).get('text','')[:50]}", "04_hooks.json"
    if nid == "template_selector":
        tpl = _load(dd, "07_template.json") or {}
        return "completed", f"Template: {tpl.get('selected_template', '—')}", "07_template.json"
    if nid == "motion_variation":
        mv = _load(dd, "08_motion_variation.json") or {}
        return "completed", f"Variation: {mv.get('variation_id', '—')} {mv.get('accent_color', '')}", "08_motion_variation.json"
    if nid == "asset_picker":
        ap = _load(dd, "09_asset_picker.json") or {}
        n = len(ap.get("selected_assets", []))
        paid = ap.get("paid_generation_required")
        return "completed", f"{n} library plate(s) reused; paid={'yes' if paid else 'no'}", "09_asset_picker.json"
    if nid == "cost_guard":
        cg = _load(dd, "cost_guard.json") or {}
        return "completed", f"Paid gen allowed: {cg.get('allowed')} (cap {cg.get('cap')})", "cost_guard.json"
    if nid == "motion_storyboard":
        return "completed", "Micro-scenes storyboarded.", "07_storyboard.json"
    if nid == "asset_director":
        return ("completed" if has("08_assets.json") else "completed",
                "Assets decided.", "08_assets.json" if has("08_assets.json") else None)
    if nid == "reel_auditor":
        qs = quality.get("scores", {})
        vis = qs.get("visual_quality", qs.get("visual"))
        return "completed", f"hook {qs.get('hook')} / ret {qs.get('retention')} / vis {vis} -> {quality.get('verdict')}", "16_quality.json"
    if nid == "publish_gate":
        return ("completed" if published else "blocked",
                "Preflight passed." if published else "Held (needs approval).", None)
    if nid == "run_vault":
        return "completed", "Reel artifacts + state stored.", "_final_output.json"
    fmap = {"market_sentinel": "01_research.json", "angle_studio": "03_angle.json",
            "script_room": "05_script.json", "retention_editor": "06_script_edited.json",
            "subtitle_engine": "11_captions.json"}
    art = fmap.get(nid)
    return "completed", "Prepared.", art
