"""Agent — Visual Pack Scout (Maven Reels Newsroom). Local, free.

Chunk 3: upgrades "pick a footage world" into "pick a designed VISUAL PACK" — a
complete look (environment + camera + palette + popup + text treatment) so the
Reel feels like a media package, not stitched clips. Five packs. Reads
format_director + location_scout. Writes 40_visual_pack.json.
"""
from __future__ import annotations

from . import state

PACKS = {
    "premium_newsroom": {
        "name": "Premium Newsroom", "for": "broad market stories",
        "environment": "dark newsroom, large blurred market screens, analyst desk",
        "camera": "slow camera push", "palette": "navy + teal, cool premium",
        "text_treatment": "clean teal/white centered titles",
        "popup_treatment": "floating glass data cards",
        "worlds": ["finance_newsroom", "market_rally", "market_stress"]},
    "investor_pov": {
        "name": "Investor POV", "for": "beginner / retail topics",
        "environment": "phone in hand, market app blur, desk setup, lifestyle finance",
        "camera": "intimate handheld POV", "palette": "warm-to-cool, relatable",
        "text_treatment": "friendly centered titles",
        "popup_treatment": "simple rounded popups",
        "worlds": ["investor_phone_pov"]},
    "sector_machine": {
        "name": "Sector Machine", "for": "sector stories",
        "environment": "that sector's real world (grid / servers / line / lab)",
        "camera": "tracking with parallax", "palette": "sector-tinted + teal",
        "text_treatment": "bold sector-name highlight",
        "popup_treatment": "INDEX -> SECTOR motion chips",
        "worlds": ["sector_broll"]},
    "policy_signal": {
        "name": "Policy Signal", "for": "RBI / SEBI / government",
        "environment": "institutional office, document mood, signal pulse",
        "camera": "steady institutional", "palette": "blue/white/teal",
        "text_treatment": "official-but-clean centered titles",
        "popup_treatment": "POLICY -> SECTOR cards",
        "worlds": ["policy_institutional"]},
    "market_investigation": {
        "name": "Market Investigation", "for": "hidden-cause / risk stories",
        "environment": "dark cinematic lighting, reveals, magnified market layers",
        "camera": "cinematic reveal / magnify", "palette": "low-key + amber warning",
        "text_treatment": "underlined reveal titles",
        "popup_treatment": "magnified layer callouts",
        "worlds": ["market_stress"]},
}

# format → default pack when the footage world is ambiguous
_FORMAT_PACK = {
    "hidden_mechanism": "premium_newsroom",
    "one_sector": "sector_machine",
    "policy_signal": "policy_signal",
    "retail_mistake": "investor_pov",
    "market_myth": "premium_newsroom",
    "risk_explainer": "market_investigation",
}


def _pack_for_world(world: str) -> str | None:
    for pid, p in PACKS.items():
        if world in p["worlds"]:
            return pid
    return None


def run(date: str) -> dict:
    fd = _opt(date, "format_director") or {}
    ls = _opt(date, "location_scout") or {}
    fid = fd.get("format", "hidden_mechanism")
    world = ls.get("selected_footage_world", "")

    pack_id = _pack_for_world(world) or _FORMAT_PACK.get(fid, "premium_newsroom")
    pack = PACKS[pack_id]
    payload = {
        "date": date, "format": fid, "footage_world": world,
        "selected_pack": pack_id, "pack": pack,
        "why_this_pack": f"{pack['name']} — best for {pack['for']}; "
                         f"matches footage world '{world or fid}'.",
        "all_packs": {pid: p["name"] for pid, p in PACKS.items()},
    }
    state.save_artifact(date, "visual_pack", payload)
    return payload


def _opt(date: str, key: str):
    try:
        return state.load_artifact(date, key)
    except Exception:
        return None
