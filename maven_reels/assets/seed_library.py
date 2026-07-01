"""Seed the reusable asset library from plates we already generated (and paid for).

Run once: `python -m maven_reels.assets.seed_library`. Pure local file copy — it
never calls Higgsfield. Idempotent (re-running overwrites metadata in place).
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from maven_reels.pipeline import asset_library, config

# Source plates already on disk (from the 2026-06-30 run).
SRC_DIR = config.OUTPUT_ROOT / "2026-06-30" / "assets"

SEEDS = [
    {"asset_id": "dark_dashboard_001", "category": "dark_dashboard",
     "src": "asset_bg_dark.jpg", "file_name": "dark_dashboard_001.jpg",
     "style": "premium dark isometric market dashboard grid",
     "tags": ["nifty", "market_move", "dashboard", "dark", "teal", "index"],
     "motion_type": "slow push-in", "quality_score": 88},
    {"asset_id": "white_data_cards_001", "category": "white_data_cards",
     "src": "asset_bg_panel.jpg", "file_name": "white_data_cards_001.jpg",
     "style": "subtle translucent data-panel motif with soft grid lines",
     "tags": ["panel", "cards", "data", "sector", "dashboard", "teal"],
     "motion_type": "subtle parallax", "quality_score": 85},
    {"asset_id": "end_cards_001", "category": "end_cards",
     "src": "asset_bg_end.jpg", "file_name": "end_cards_001.jpg",
     "style": "calm radial teal glow end-card backdrop",
     "tags": ["end_card", "brand", "maven", "teal", "outro"],
     "motion_type": "slow glow", "quality_score": 86},
]


def main() -> None:
    if not SRC_DIR.exists():
        print(f"[seed] source plates not found at {SRC_DIR}; nothing to seed.")
        return
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    made = []
    for s in SEEDS:
        src = SRC_DIR / s["src"]
        if not src.exists():
            print(f"[seed] skip {s['asset_id']}: {src} missing")
            continue
        rec = asset_library.register(
            asset_id=s["asset_id"], category=s["category"],
            file_name=s["file_name"], src_path=src,
            meta={"style": s["style"], "tags": s["tags"],
                  "motion_type": s["motion_type"], "quality_score": s["quality_score"],
                  "resolution": "1080x1920", "duration": 0,
                  "source_model": "higgsfield/nano_banana_pro",
                  "generation_cost": "already paid (2026-06-30 run)",
                  "created_at": now, "reuse_count": 0}, )
        made.append(rec["asset_id"])
    print(f"[seed] library ready at {config.ASSET_LIBRARY_DIR}")
    print(f"[seed] assets: {made}")
    print(f"[seed] categories present: {asset_library.categories_present()}")


if __name__ == "__main__":
    main()
