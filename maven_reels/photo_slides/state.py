"""Artifact + package state I/O for the Photo Reel Slides framework.

One folder per package under outputs/maven_photo_reels/<job_id>/, one JSON
per agent, images under slides/, export bundle under export/.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import config


def job_dir(job_id: str) -> Path:
    d = config.OUTPUT_ROOT / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def slides_dir(job_id: str) -> Path:
    d = job_dir(job_id) / "slides"
    d.mkdir(parents=True, exist_ok=True)
    return d


def export_dir(job_id: str) -> Path:
    d = job_dir(job_id) / "export"
    d.mkdir(parents=True, exist_ok=True)
    return d


def artifact_path(job_id: str, key: str) -> Path:
    return job_dir(job_id) / config.ARTIFACTS[key]


def save_artifact(job_id: str, key: str, payload: dict[str, Any]) -> Path:
    p = artifact_path(job_id, key)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                 encoding="utf-8")
    return p


def load_artifact(job_id: str, key: str) -> dict[str, Any] | None:
    p = artifact_path(job_id, key)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def list_jobs() -> list[str]:
    """Package ids, newest first (ids are datetime-sortable)."""
    if not config.OUTPUT_ROOT.exists():
        return []
    return sorted((p.name for p in config.OUTPUT_ROOT.iterdir()
                   if p.is_dir() and p.name.startswith("slides-")), reverse=True)


def get_package(job_id: str) -> dict[str, Any]:
    return load_artifact(job_id, "package") or {
        "job_id": job_id, "status": "draft", "publish_mode":
        config.DEFAULT_REEL_PUBLISH_MODE, "history": [],
    }


def update_package(job_id: str, **fields: Any) -> dict[str, Any]:
    pkg = get_package(job_id)
    if "status" in fields and fields["status"] not in config.PACKAGE_STATUSES:
        raise ValueError(f"unknown package status: {fields['status']}")
    entry = {"at": config.now_ist().isoformat(timespec="seconds"), **fields}
    pkg.update(fields)
    pkg.setdefault("history", []).append(entry)
    pkg["job_id"] = job_id
    save_artifact(job_id, "package", pkg)
    return pkg
