"""Reusable Higgsfield motion-asset library.

The library lives at maven_reels/assets/library/<category>/ and is checked into
the repo. Each asset is a clean 9:16 visual/motion plate (NO readable text) with a
sidecar `<asset_id>.json` metadata file. Daily reels PICK from this library
instead of generating new Higgsfield assets — so marginal cost is ~zero.

This module only reads/writes local files; it never calls Higgsfield.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import config

LIBRARY_DIR = config.ASSET_LIBRARY_DIR


def _meta_files() -> list[Path]:
    if not LIBRARY_DIR.exists():
        return []
    return sorted(LIBRARY_DIR.glob("*/*.json"))


def load_index() -> list[dict]:
    """Return every asset's metadata (resolving file paths to absolute)."""
    out: list[dict] = []
    for mf in _meta_files():
        try:
            m = json.loads(mf.read_text(encoding="utf-8"))
        except Exception:
            continue
        fp = mf.parent / m.get("file_name", "")
        m["_meta_path"] = str(mf)
        m["file_path"] = str(fp) if fp.exists() else m.get("file_path", "")
        m["_available"] = fp.exists()
        out.append(m)
    return out


def find(*, category: str | None = None, tags: list[str] | None = None,
         type_: str | None = None, available_only: bool = True) -> list[dict]:
    """Rank library assets by relevance to category + tags. Best match first."""
    tags = [t.lower() for t in (tags or [])]
    scored: list[tuple[int, dict]] = []
    for a in load_index():
        if available_only and not a.get("_available"):
            continue
        if type_ and a.get("type") != type_:
            continue
        score = 0
        if category and a.get("category") == category:
            score += 10
        atags = [str(t).lower() for t in a.get("tags", [])]
        score += sum(2 for t in tags if t in atags)
        # quality + reuse as gentle tiebreakers (prefer good, less-overused assets)
        score += int(a.get("quality_score", 0)) // 20
        score -= min(3, int(a.get("reuse_count", 0)))
        if score > 0 or (category and a.get("category") == category):
            scored.append((score, a))
    scored.sort(key=lambda s: s[0], reverse=True)
    return [a for _, a in scored]


def categories_present() -> list[str]:
    return sorted({a.get("category", "") for a in load_index() if a.get("_available")})


def register(*, asset_id: str, category: str, file_name: str, src_path: Path,
             preview_name: str | None = None, meta: dict[str, Any] | None = None) -> dict:
    """Copy an asset file into the library under `category` and write metadata.

    Used by the seed script and (later) by an approved Higgsfield generation to
    persist a new reusable asset. Local file copy only — no network calls.
    """
    import shutil

    cat_dir = LIBRARY_DIR / category
    cat_dir.mkdir(parents=True, exist_ok=True)
    dst = cat_dir / file_name
    if Path(src_path).resolve() != dst.resolve():
        shutil.copy2(src_path, dst)
    record = {
        "asset_id": asset_id, "category": category, "type": "motion_plate",
        "file_name": file_name, "file_path": str(dst),
        "preview_name": preview_name or file_name,
        "duration": 0, "resolution": "1080x1920",
        "style": "premium dark finance dashboard", "tags": [], "motion_type": "static plate",
        "text_safe_areas": ["center", "upper_third", "lower_third"],
        "avoid_uses": [], "source_model": "higgsfield/nano_banana_pro",
        "generation_cost": None, "quality_score": 80, "reuse_count": 0,
        "created_at": None,
    }
    record.update(meta or {})
    (cat_dir / f"{asset_id}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def bump_reuse(asset_id: str) -> None:
    for a in load_index():
        if a.get("asset_id") == asset_id and a.get("_meta_path"):
            a.pop("_available", None); a.pop("_meta_path", None)
            a["reuse_count"] = int(a.get("reuse_count", 0)) + 1
            p = LIBRARY_DIR / a["category"] / f"{asset_id}.json"
            p.write_text(json.dumps(a, ensure_ascii=False, indent=2), encoding="utf-8")
            return
