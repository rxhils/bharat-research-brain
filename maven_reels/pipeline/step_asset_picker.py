"""Step — Asset Picker.

Picks 2-4 existing plates from the reusable library (instead of generating new
Higgsfield assets) and copies them into the run's assets/ dir under the canonical
slot names the Motion Graphics Engine already expects (asset_bg_dark/panel/end).
If a slot has no suitable library asset AND paid generation isn't allowed, it is
reported as missing + requires_approval — nothing is generated here.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from . import asset_library, config, state, step_cost_guard

# storyboard slot -> default library category + descriptive tags
SLOT_CATEGORY = {
    "asset_bg_dark": ("dark_dashboard", ["dark", "dashboard", "market"]),
    "asset_bg_panel": ("white_data_cards", ["panel", "cards", "data"]),
    "asset_bg_end": ("end_cards", ["end_card", "brand", "maven"]),
}


def run(date: str, *, storyboard: dict, template: dict | None = None,
        story: dict | None = None) -> dict:
    run_assets = config.run_dir(date) / "assets"
    run_assets.mkdir(parents=True, exist_ok=True)

    slots_used = sorted({s.get("asset") for s in storyboard.get("scenes", [])
                         if s.get("asset")})
    story_tags = []
    if story:
        story_tags = [str(t).lower() for t in (story.get("affected_sectors") or [])][:3]
    tmpl_cats = (template or {}).get("recommended_assets", {}) if template else {}

    selected, missing = [], []
    for slot in slots_used:
        category, tags = SLOT_CATEGORY.get(slot, ("dark_dashboard", []))
        category = tmpl_cats.get(slot, category)
        candidates = asset_library.find(category=category, tags=tags + story_tags) \
            or asset_library.find(category="dark_dashboard")
        if candidates:
            a = candidates[0]
            dst = run_assets / f"{slot}.jpg"
            try:
                shutil.copy2(a["file_path"], dst)
                asset_library.bump_reuse(a["asset_id"])
                selected.append({
                    "slot": slot, "asset_id": a["asset_id"], "category": a["category"],
                    "file_path": str(dst), "library_path": a["file_path"],
                    "used_in_scenes": [s["scene"] for s in storyboard["scenes"] if s.get("asset") == slot],
                    "reason": f"Best library match for '{slot}' ({a['category']}).",
                })
                continue
            except Exception as exc:  # pragma: no cover - defensive
                missing.append({"slot": slot, "category": category, "error": str(exc)})
        else:
            missing.append({"slot": slot, "category": category,
                            "reason": "No suitable asset in library."})

    # cost decision: any missing slot would need paid generation
    guard = step_cost_guard.evaluate(date, requested=len(missing))
    paid_required = len(missing) > 0

    payload = {
        "date": date,
        "use_existing_asset_library": config.USE_EXISTING_ASSET_LIBRARY,
        "slots_required": slots_used,
        "selected_assets": selected,
        "missing_assets": missing,
        "paid_generation_required": paid_required,
        "paid_generation_allowed": guard["allowed"] and paid_required,
        "requires_approval": paid_required and not guard["allowed"],
        "generation_request": None,   # step_higgsfield_asset_request builds this if needed
        "estimated_new_generations": len(missing),
        "estimated_cost": "0 (library reuse)" if not paid_required else f"{len(missing)} paid generation(s)",
        "cost_guard": guard,
    }
    state.save_artifact(date, "asset_picker", payload)
    return payload
