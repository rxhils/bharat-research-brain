"""Tests for scenario event patterns (Chunk 4.13) — pure event detection and
sector-sensitivity lookup. All synthetic; no DB, no network, no imports from
agents or repos.

The sector-event sensitivity matrix (8 macro events x 19 sectors) and the two
pure functions (`detect_active_event`, `get_sector_event_score`) are unit-tested
here. The MacroAgent/RankingAgent wiring that consumes them is I/O and exercised
by the live `macro run` / `ranking run` verification step.
"""
from __future__ import annotations

from backend.data.scenario_patterns import (
    SECTOR_EVENT_SENSITIVITY,
    detect_active_event,
    get_sector_event_score,
)

# The 19 real DB sector labels (confirmed via SELECT DISTINCT sector in 4.11b).
_DB_SECTORS = {
    "Financials",
    "Realty",
    "Auto",
    "Consumer Services",
    "Consumer Durables",
    "Construction",
    "FMCG",
    "IT",
    "Pharma",
    "Energy",
    "Power",
    "Metals",
    "Chemicals",
    "Capital Goods",
    "Telecom",
    "Media",
    "Textiles",
    "Services",
    "Diversified",
}


# ---------------------------------------------------------------------------
# detect_active_event
# ---------------------------------------------------------------------------
def test_detect_vix_spike() -> None:
    event = detect_active_event(
        india_vix=21.0,
        crude_30d_change_pct=None,
        usd_inr_30d_change_pct=None,
        rbi_action=None,
        us_fed_action=None,
    )
    assert event == "VIX_SPIKE"


def test_detect_rbi_cut() -> None:
    event = detect_active_event(
        india_vix=15.0,
        crude_30d_change_pct=None,
        usd_inr_30d_change_pct=None,
        rbi_action="cut",
        us_fed_action=None,
    )
    assert event == "RBI_RATE_CUT"


def test_detect_crude_spike() -> None:
    event = detect_active_event(
        india_vix=None,
        crude_30d_change_pct=12.0,
        usd_inr_30d_change_pct=None,
        rbi_action=None,
        us_fed_action=None,
    )
    assert event == "CRUDE_SPIKE"


def test_detect_crude_fall() -> None:
    event = detect_active_event(
        india_vix=None,
        crude_30d_change_pct=-11.0,
        usd_inr_30d_change_pct=None,
        rbi_action=None,
        us_fed_action=None,
    )
    assert event == "CRUDE_FALL"


def test_detect_inr_weakens() -> None:
    event = detect_active_event(
        india_vix=None,
        crude_30d_change_pct=None,
        usd_inr_30d_change_pct=4.0,
        rbi_action=None,
        us_fed_action=None,
    )
    assert event == "INR_WEAKENS"


def test_detect_inr_strengthens() -> None:
    event = detect_active_event(
        india_vix=None,
        crude_30d_change_pct=None,
        usd_inr_30d_change_pct=-4.0,
        rbi_action=None,
        us_fed_action=None,
    )
    assert event == "INR_STRENGTHENS"


def test_detect_no_event() -> None:
    event = detect_active_event(
        india_vix=None,
        crude_30d_change_pct=None,
        usd_inr_30d_change_pct=None,
        rbi_action=None,
        us_fed_action=None,
    )
    assert event is None


def test_vix_takes_priority() -> None:
    # VIX_SPIKE outranks RBI_RATE_CUT when both conditions hold.
    event = detect_active_event(
        india_vix=22.0,
        crude_30d_change_pct=None,
        usd_inr_30d_change_pct=None,
        rbi_action="cut",
        us_fed_action=None,
    )
    assert event == "VIX_SPIKE"


# ---------------------------------------------------------------------------
# matrix completeness
# ---------------------------------------------------------------------------
def test_all_sector_keys_present_for_each_event() -> None:
    assert len(SECTOR_EVENT_SENSITIVITY) == 8
    for event, sensitivities in SECTOR_EVENT_SENSITIVITY.items():
        assert set(sensitivities.keys()) == _DB_SECTORS, event


# ---------------------------------------------------------------------------
# get_sector_event_score
# ---------------------------------------------------------------------------
def test_get_sector_event_score_vix_pharma() -> None:
    assert get_sector_event_score("Pharma", "VIX_SPIKE") == 1


def test_get_sector_event_score_realty_rate_cut() -> None:
    assert get_sector_event_score("Realty", "RBI_RATE_CUT") == 3


def test_get_sector_event_score_none_event() -> None:
    assert get_sector_event_score("IT", None) == 0


def test_get_sector_event_score_unknown_sector() -> None:
    assert get_sector_event_score("Unknown", "VIX_SPIKE") == 0
