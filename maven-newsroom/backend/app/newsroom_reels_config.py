"""Config for the isolated Newsroom Reels module.

Storage lives entirely on E:\\MavenReels, never under this repo and never on
C:\\. Never imported by, or imported into, the existing Higgsfield reels
module (registry_reels.py / reel_studio.py / routes/reels.py).
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

STORAGE_ROOT = Path(os.environ.get("NEWSROOM_REELS_STORAGE_ROOT", r"E:\MavenReels"))
MIN_FREE_GB = 50

# Remotion render package (code lives in the repo; media stays on E:)
REPO_ROOT_RENDER_APP = Path(__file__).resolve().parents[2] / "reels-render"

STORAGE_SUBDIRS = [
    "daily-runs", "source-videos", "transcripts", "candidate-clips",
    "renders", "thumbnails", "captions", "watch-reports", "qa-reports",
    "logs", "cache", "temp",
]


def storage_status() -> dict:
    """Never falls back to Desktop/Downloads/Documents/Videos or C:\\."""
    if str(STORAGE_ROOT).upper().startswith("C:"):
        return {"storage_root": str(STORAGE_ROOT), "storage_ok": False, "free_gb": 0.0, "min_free_gb": MIN_FREE_GB}
    if not STORAGE_ROOT.exists():
        return {"storage_root": str(STORAGE_ROOT), "storage_ok": False, "free_gb": 0.0, "min_free_gb": MIN_FREE_GB}
    for sub in STORAGE_SUBDIRS:
        (STORAGE_ROOT / sub).mkdir(parents=True, exist_ok=True)
    free_gb = round(shutil.disk_usage(STORAGE_ROOT).free / (1024 ** 3), 1)
    return {
        "storage_root": str(STORAGE_ROOT),
        "storage_ok": free_gb >= MIN_FREE_GB,
        "free_gb": free_gb,
        "min_free_gb": MIN_FREE_GB,
    }
