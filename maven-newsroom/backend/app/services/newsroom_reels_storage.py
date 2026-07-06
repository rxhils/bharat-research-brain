"""Storage Validation Agent for the Newsroom Reels module.

Every worker in the Reels pipeline must obtain output paths through this
module. It enforces the hard storage rules:

  - all generated files live under E:\\MavenReels (or NEWSROOM_REELS_STORAGE_ROOT)
  - if the drive is missing, the run is blocked
  - if free space is below 50 GB, rendering is blocked
  - any path on C:\\ (or under Desktop/Downloads/Documents/Videos) is rejected

Isolated from the existing Higgsfield reels services — nothing here imports
reel_studio, registry_reels, or the shared newsroom.db.
"""
from __future__ import annotations

import shutil
from datetime import date as date_t
from pathlib import Path

from ..newsroom_reels_config import MIN_FREE_GB, STORAGE_ROOT, STORAGE_SUBDIRS


class ReelsStorageError(Exception):
    """A storage rule was violated. Callers must block the job, not fall back."""


_FORBIDDEN_USER_DIRS = ("desktop", "downloads", "documents", "videos")


def guard_path(path: str | Path) -> Path:
    """Validate that *path* is a legal Reels output path. Returns it resolved.

    Raises ReelsStorageError for anything on C:\\, under a user profile
    folder (Desktop/Downloads/Documents/Videos), or outside STORAGE_ROOT.
    """
    p = Path(path).resolve()
    drive = p.drive.upper().rstrip(":")
    if drive == "C":
        raise ReelsStorageError(f"blocked: path is on C drive: {p}")
    lowered = {part.lower() for part in p.parts}
    if lowered & set(_FORBIDDEN_USER_DIRS):
        raise ReelsStorageError(f"blocked: path is under a user profile folder: {p}")
    root = STORAGE_ROOT.resolve()
    if root != p and root not in p.parents:
        raise ReelsStorageError(f"blocked: path is outside {root}: {p}")
    return p


def validate_storage(*, for_render: bool = False) -> dict:
    """Check the storage root; create required folders. Raises on violation.

    for_render=True additionally enforces the 50 GB free-space gate (renders
    are the expensive writes; status checks report but don't raise).
    """
    if str(STORAGE_ROOT).upper().startswith("C:"):
        raise ReelsStorageError(f"blocked: storage root is on C drive: {STORAGE_ROOT}")
    if not Path(STORAGE_ROOT.drive + "\\").exists():
        raise ReelsStorageError(f"blocked: drive {STORAGE_ROOT.drive} is missing")
    STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    for sub in STORAGE_SUBDIRS:
        (STORAGE_ROOT / sub).mkdir(parents=True, exist_ok=True)
    free_gb = round(shutil.disk_usage(STORAGE_ROOT).free / (1024 ** 3), 1)
    if for_render and free_gb < MIN_FREE_GB:
        raise ReelsStorageError(
            f"blocked: only {free_gb} GB free on {STORAGE_ROOT.drive}, "
            f"need {MIN_FREE_GB} GB to render")
    return {
        "storage_root": str(STORAGE_ROOT),
        "storage_ok": free_gb >= MIN_FREE_GB,
        "free_gb": free_gb,
        "min_free_gb": MIN_FREE_GB,
        "folders": STORAGE_SUBDIRS,
    }


def daily_run_dir(run_date: date_t | str) -> Path:
    """E:\\MavenReels\\daily-runs\\YYYY-MM-DD — created and guarded."""
    d = run_date.isoformat() if isinstance(run_date, date_t) else str(run_date)
    p = guard_path(STORAGE_ROOT / "daily-runs" / d)
    p.mkdir(parents=True, exist_ok=True)
    return p


def run_subdir(run_date: date_t | str, name: str) -> Path:
    """A named folder inside a daily run (candidate-clips, renders, ...)."""
    p = guard_path(daily_run_dir(run_date) / name)
    p.mkdir(parents=True, exist_ok=True)
    return p
