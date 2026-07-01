"""Step — Template Selector.

Chooses the best Remotion reel template for the story and returns its scene
structure + recommended library asset categories per slot. Deterministic: routes
on story type keywords. The Motion Storyboard then fills these scene slots.
"""
from __future__ import annotations

import re

from . import state

# template -> (scene purposes, recommended library category per slot, accent, motion)
TEMPLATES = {
    "market_move_explainer": {
        "reason": "Broad index/market reaction (Nifty/Sensex/Bank Nifty).",
        "scene_structure": ["hook", "index_card", "sector_chips", "reason_card",
                             "mini_chart", "takeaway", "cta"],
        "recommended_assets": {"asset_bg_dark": "index_move",
                               "asset_bg_panel": "white_data_cards",
                               "asset_bg_end": "end_cards"},
        "motion_style": "teal_terminal", "accent_color": "#22D3EE"},
    "sector_breakdown": {
        "reason": "One sector drove the move (banking/IT/energy/pharma/auto…).",
        "scene_structure": ["hook", "sector_card", "sector_chips", "what_moved",
                            "why_moved", "takeaway", "cta"],
        "recommended_assets": {"asset_bg_dark": "sector_heatmap",
                               "asset_bg_panel": "white_data_cards",
                               "asset_bg_end": "end_cards"},
        "motion_style": "green_pulse", "accent_color": "#27C281"},
    "policy_impact": {
        "reason": "RBI/SEBI/government/budget/tax/regulation event.",
        "scene_structure": ["hook", "policy_card", "affected_sectors",
                            "what_changes", "why_matters", "cta"],
        "recommended_assets": {"asset_bg_dark": "rbi_policy",
                               "asset_bg_panel": "white_data_cards",
                               "asset_bg_end": "end_cards"},
        "motion_style": "orange_alert", "accent_color": "#F59E0B"},
    "company_shock": {
        "reason": "Single company/earnings/M&A/order event (Reliance/HDFC/Adani…).",
        "scene_structure": ["hook", "company_card", "what_happened",
                            "market_reaction", "why_matters", "cta"],
        "recommended_assets": {"asset_bg_dark": "company_news",
                               "asset_bg_panel": "white_data_cards",
                               "asset_bg_end": "end_cards"},
        "motion_style": "blue_newsroom", "accent_color": "#38BDF8"},
    "what_investors_missed": {
        "reason": "Hidden/under-the-surface reason; educational explainer.",
        "scene_structure": ["hook", "misconception", "hidden_reason",
                            "simple_explanation", "takeaway", "cta"],
        "recommended_assets": {"asset_bg_dark": "dark_dashboard",
                               "asset_bg_panel": "white_data_cards",
                               "asset_bg_end": "end_cards"},
        "motion_style": "teal_terminal", "accent_color": "#22D3EE"},
}

_KEY = {
    "policy_impact": r"\b(rbi|sebi|budget|policy|tax|regulation|repo|government|cabinet)\b",
    "company_shock": r"\b(reliance|hdfc|infosys|tata|adani|tcs|earnings|results|merger|acquisition|order win|q[1-4] results)\b",
    "sector_breakdown": r"\b(sector|banking|bank nifty|it index|nifty it|pharma|auto|fmcg|metal|realty|energy|defence)\b",
    "what_investors_missed": r"\b(missed|hidden|misunderstood|under the surface|overlooked|actually)\b",
}


def _pick(story: dict, angle: dict) -> str:
    blob = " ".join(str(x) for x in [
        story.get("headline", ""), story.get("what_happened", ""),
        " ".join(story.get("affected_sectors") or []),
        (angle or {}).get("angle_type", ""), (angle or {}).get("selected_angle", ""),
    ]).lower()
    for tmpl, pat in _KEY.items():
        if re.search(pat, blob):
            return tmpl
    return "market_move_explainer"


def run(date: str, *, story: dict, angle: dict | None = None) -> dict:
    tmpl = _pick(story, angle or {})
    spec = TEMPLATES[tmpl]
    payload = {
        "date": date, "selected_template": tmpl, "template_reason": spec["reason"],
        "scene_structure": spec["scene_structure"],
        "recommended_assets": spec["recommended_assets"],
        "motion_style": spec["motion_style"], "accent_color": spec["accent_color"],
        "all_templates": list(TEMPLATES.keys()),
    }
    state.save_artifact(date, "template", payload)
    return payload
