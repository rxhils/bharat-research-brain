"""Scenario event patterns (Chunk 4.13).

Pure reference data + detection logic mapping macro events (RBI rate moves,
crude moves, INR moves, US Fed hikes, volatility spikes) to per-sector
sensitivity scores. No DB, no network, no imports from agents or repositories —
this module is deliberately importable in isolation and fully unit-testable.

`SECTOR_EVENT_SENSITIVITY` covers 8 events x the 19 real DB sector labels
(confirmed via `SELECT DISTINCT sector` from the `stocks` table). Scores range
-3..+3 and are added on top of the existing macro regime score, never replacing
it.
"""
from __future__ import annotations

# The 8 macro events, each scored across all 19 real DB sector labels.
# Scores: positive => sector tailwind under that event, negative => headwind.
SECTOR_EVENT_SENSITIVITY: dict[str, dict[str, int]] = {
    "RBI_RATE_CUT": {
        "Financials": 1,
        "Realty": 3,
        "Auto": 2,
        "Consumer Services": 2,
        "Consumer Durables": 2,
        "Construction": 2,
        "FMCG": 1,
        "IT": 0,
        "Pharma": 0,
        "Energy": 0,
        "Power": 1,
        "Metals": 1,
        "Chemicals": 0,
        "Capital Goods": 1,
        "Telecom": 1,
        "Media": 1,
        "Textiles": 1,
        "Services": 1,
        "Diversified": 1,
    },
    "RBI_RATE_HIKE": {
        "Financials": -1,
        "Realty": -3,
        "Auto": -2,
        "Consumer Services": -2,
        "Consumer Durables": -2,
        "Construction": -2,
        "FMCG": -1,
        "IT": 0,
        "Pharma": 0,
        "Energy": 0,
        "Power": -1,
        "Metals": -1,
        "Chemicals": -1,
        "Capital Goods": -1,
        "Telecom": -1,
        "Media": -1,
        "Textiles": -1,
        "Services": -1,
        "Diversified": -1,
    },
    "CRUDE_SPIKE": {
        "Energy": 3,
        "Financials": -1,
        "Auto": -2,
        "FMCG": -2,
        "Consumer Services": -1,
        "Consumer Durables": -1,
        "Construction": -1,
        "IT": 0,
        "Pharma": -1,
        "Power": -2,
        "Metals": -1,
        "Chemicals": -2,
        "Capital Goods": 0,
        "Telecom": 0,
        "Media": 0,
        "Textiles": -1,
        "Services": 0,
        "Realty": -1,
        "Diversified": -1,
    },
    "CRUDE_FALL": {
        "Energy": -2,
        "Financials": 1,
        "Auto": 2,
        "FMCG": 2,
        "Consumer Services": 1,
        "Consumer Durables": 1,
        "Construction": 1,
        "IT": 0,
        "Pharma": 1,
        "Power": 2,
        "Metals": 1,
        "Chemicals": 2,
        "Capital Goods": 1,
        "Telecom": 0,
        "Media": 0,
        "Textiles": 1,
        "Services": 1,
        "Realty": 1,
        "Diversified": 1,
    },
    "INR_WEAKENS": {
        "IT": 2,
        "Pharma": 2,
        "Metals": 1,
        "Textiles": 2,
        "Energy": -1,
        "Financials": -1,
        "Auto": -1,
        "FMCG": -1,
        "Consumer Services": -1,
        "Consumer Durables": -1,
        "Construction": -1,
        "Power": -1,
        "Chemicals": -1,
        "Capital Goods": -1,
        "Telecom": 0,
        "Media": 0,
        "Services": 1,
        "Realty": -1,
        "Diversified": 0,
    },
    "INR_STRENGTHENS": {
        "IT": -2,
        "Pharma": -1,
        "Metals": -1,
        "Textiles": -1,
        "Energy": 1,
        "Financials": 1,
        "Auto": 1,
        "FMCG": 1,
        "Consumer Services": 1,
        "Consumer Durables": 1,
        "Construction": 0,
        "Power": 1,
        "Chemicals": 1,
        "Capital Goods": 0,
        "Telecom": 0,
        "Media": 0,
        "Services": 0,
        "Realty": 0,
        "Diversified": 0,
    },
    "US_FED_HIKE": {
        "IT": -2,
        "Financials": -1,
        "Metals": -1,
        "Energy": -1,
        "Pharma": 0,
        "Auto": -1,
        "FMCG": 0,
        "Consumer Services": -1,
        "Consumer Durables": -1,
        "Construction": -1,
        "Power": 0,
        "Chemicals": -1,
        "Capital Goods": -1,
        "Telecom": 0,
        "Media": -1,
        "Textiles": -1,
        "Services": -1,
        "Realty": -2,
        "Diversified": -1,
    },
    "VIX_SPIKE": {
        "Financials": -2,
        "IT": -1,
        "Metals": -2,
        "Energy": -1,
        "Pharma": 1,
        "Auto": -2,
        "FMCG": 1,
        "Consumer Services": -1,
        "Consumer Durables": -2,
        "Construction": -2,
        "Power": 0,
        "Chemicals": -1,
        "Capital Goods": -2,
        "Telecom": 0,
        "Media": -1,
        "Textiles": -2,
        "Services": -1,
        "Realty": -2,
        "Diversified": -1,
    },
}


def detect_active_event(
    india_vix: float | None,
    crude_30d_change_pct: float | None,
    usd_inr_30d_change_pct: float | None,
    rbi_action: str | None,
    us_fed_action: str | None,
) -> str | None:
    """Return the single active macro event, or None.

    Priority is strict (first match wins): a volatility spike outranks central-
    bank actions, which outrank commodity/currency moves. Every input is
    optional; missing inputs simply skip their checks (no crash).
    """
    if india_vix is not None and india_vix > 20:
        return "VIX_SPIKE"
    if rbi_action == "cut":
        return "RBI_RATE_CUT"
    if rbi_action == "hike":
        return "RBI_RATE_HIKE"
    if us_fed_action == "hike":
        return "US_FED_HIKE"
    if crude_30d_change_pct is not None and crude_30d_change_pct > 10:
        return "CRUDE_SPIKE"
    if crude_30d_change_pct is not None and crude_30d_change_pct < -10:
        return "CRUDE_FALL"
    if usd_inr_30d_change_pct is not None and usd_inr_30d_change_pct > 3:
        return "INR_WEAKENS"
    if usd_inr_30d_change_pct is not None and usd_inr_30d_change_pct < -3:
        return "INR_STRENGTHENS"
    return None


def get_sector_event_score(sector: str, event: str | None) -> int:
    """Return the sensitivity score for a sector under an event.

    Returns 0 when no event is active or the sector is not in the matrix.
    Never raises.
    """
    if event is None:
        return 0
    return SECTOR_EVENT_SENSITIVITY.get(event, {}).get(sector, 0)
