"""Tests for backend.agents.universe.build_plan — the Universe Agent's brain.

`build_plan` is pure: given fetched securities + per-index constituents and a
snapshot of current DB state, it computes the SCD-2 plan (stocks to insert /
update, memberships to open / close) without any I/O. The DB-touching apply
path is exercised by the live `--dry-run` / real run, not here.
"""
from __future__ import annotations

from datetime import date

from backend.agents.universe import (
    DesiredStock,
    StockFields,
    UniversePlan,
    build_plan,
)
from backend.data_sources.niftyindices import Constituent
from backend.data_sources.nse_archives import NSESecurity

EFF = date(2026, 5, 25)


def _sec(isin: str, symbol: str, name: str, listed: date | None = None) -> NSESecurity:
    return NSESecurity(
        nse_symbol=symbol,
        company_name=name,
        series="EQ",
        listed_on=listed,
        paid_up_value="10",
        market_lot=1,
        isin=isin,
        face_value="10",
    )


def _con(isin: str, symbol: str, name: str, industry: str | None) -> Constituent:
    return Constituent(
        company_name=name,
        industry=industry,
        nse_symbol=symbol,
        series="EQ",
        isin=isin,
    )


# ---------------------------------------------------------------------------
# 1. Fresh universe: every stock inserted, every membership opened.
# ---------------------------------------------------------------------------
def test_fresh_universe_inserts_all() -> None:
    plan = build_plan(
        securities=[_sec("INE001A01010", "AAA", "Alpha Ltd", date(2000, 1, 1))],
        constituents_by_index={
            "NIFTY50": [_con("INE001A01010", "AAA", "Alpha Ltd", "Information Technology")]
        },
        current_stocks={},
        current_memberships=set(),
        deferred_indices=[],
        failed_indices={},
        effective_date=EFF,
    )
    assert "INE001A01010" in plan.stocks_to_insert
    inserted = plan.stocks_to_insert["INE001A01010"]
    assert inserted.sector == "IT"  # harmonized from "Information Technology"
    assert inserted.industry == "Information Technology"
    assert inserted.listed_on == date(2000, 1, 1)
    assert plan.stocks_to_update == {}
    assert ("NIFTY50", "INE001A01010") in plan.memberships_to_open
    assert plan.memberships_to_close == []


# ---------------------------------------------------------------------------
# 2. Steady state: identical inputs produce no changes.
# ---------------------------------------------------------------------------
def test_steady_state_no_changes() -> None:
    current_stocks = {
        "INE001A01010": StockFields(
            nse_symbol="AAA",
            company_name="Alpha Ltd",
            industry="Information Technology",
            sector="IT",
        )
    }
    plan = build_plan(
        securities=[_sec("INE001A01010", "AAA", "Alpha Ltd")],
        constituents_by_index={
            "NIFTY50": [_con("INE001A01010", "AAA", "Alpha Ltd", "Information Technology")]
        },
        current_stocks=current_stocks,
        current_memberships={("NIFTY50", "INE001A01010")},
        deferred_indices=[],
        failed_indices={},
        effective_date=EFF,
    )
    assert plan.stocks_to_insert == {}
    assert plan.stocks_to_update == {}
    assert plan.memberships_to_open == []
    assert plan.memberships_to_close == []
    assert plan.has_changes() is False


# ---------------------------------------------------------------------------
# 3. A changed company name produces a field-level update delta.
# ---------------------------------------------------------------------------
def test_changed_field_produces_update() -> None:
    current_stocks = {
        "INE001A01010": StockFields(
            nse_symbol="AAA",
            company_name="Alpha Ltd",
            industry="Information Technology",
            sector="IT",
        )
    }
    plan = build_plan(
        securities=[_sec("INE001A01010", "AAA", "Alpha Industries Ltd")],
        constituents_by_index={
            "NIFTY50": [
                _con("INE001A01010", "AAA", "Alpha Industries Ltd", "Information Technology")
            ]
        },
        current_stocks=current_stocks,
        current_memberships={("NIFTY50", "INE001A01010")},
        deferred_indices=[],
        failed_indices={},
        effective_date=EFF,
    )
    assert plan.stocks_to_insert == {}
    deltas = plan.stocks_to_update["INE001A01010"]
    assert ("company_name", "Alpha Ltd", "Alpha Industries Ltd") in deltas


# ---------------------------------------------------------------------------
# 4. A dropped constituent closes the membership but never delists the stock.
# ---------------------------------------------------------------------------
def test_dropped_member_closes_membership_not_stock() -> None:
    current_stocks = {
        "INE001A01010": StockFields("AAA", "Alpha Ltd", "Information Technology", "IT"),
        "INE002A01018": StockFields("BBB", "Beta Ltd", "Information Technology", "IT"),
    }
    plan = build_plan(
        securities=[_sec("INE001A01010", "AAA", "Alpha Ltd")],
        constituents_by_index={
            "NIFTY50": [_con("INE001A01010", "AAA", "Alpha Ltd", "Information Technology")]
        },
        current_stocks=current_stocks,
        current_memberships={
            ("NIFTY50", "INE001A01010"),
            ("NIFTY50", "INE002A01018"),  # Beta dropped out
        },
        deferred_indices=[],
        failed_indices={},
        effective_date=EFF,
    )
    assert ("NIFTY50", "INE002A01018") in plan.memberships_to_close
    # Beta's stock row is untouched — leaving an index is not a delisting.
    assert "INE002A01018" not in plan.stocks_to_insert
    assert "INE002A01018" not in plan.stocks_to_update


# ---------------------------------------------------------------------------
# 5. A deferred index's existing memberships are NOT closed.
# ---------------------------------------------------------------------------
def test_deferred_index_memberships_preserved() -> None:
    plan = build_plan(
        securities=[_sec("INE001A01010", "AAA", "Alpha Ltd")],
        constituents_by_index={
            "NIFTY50": [_con("INE001A01010", "AAA", "Alpha Ltd", "Information Technology")]
        },
        current_stocks={
            "INE001A01010": StockFields("AAA", "Alpha Ltd", "Information Technology", "IT"),
            "INE002A01018": StockFields("BBB", "Beta Ltd", "Financial Services", "Financials"),
        },
        current_memberships={
            ("NIFTY50", "INE001A01010"),
            ("NIFTYFINSERVICE", "INE002A01018"),  # deferred index — leave alone
        },
        deferred_indices=["NIFTYFINSERVICE"],
        failed_indices={},
        effective_date=EFF,
    )
    assert ("NIFTYFINSERVICE", "INE002A01018") not in plan.memberships_to_close
    assert plan.memberships_to_close == []


# ---------------------------------------------------------------------------
# 6. An unrecognized industry is recorded as an unmapped-sector warning.
# ---------------------------------------------------------------------------
def test_unmapped_sector_recorded() -> None:
    plan = build_plan(
        securities=[_sec("INE001A01010", "AAA", "Alpha Ltd")],
        constituents_by_index={
            "NIFTY50": [_con("INE001A01010", "AAA", "Alpha Ltd", "Quantum Computing")]
        },
        current_stocks={},
        current_memberships=set(),
        deferred_indices=[],
        failed_indices={},
        effective_date=EFF,
    )
    assert "Quantum Computing" in plan.unmapped_sectors
    # Passthrough sector still stored (was_mapped=False).
    assert plan.stocks_to_insert["INE001A01010"].sector == "Quantum Computing"


# ---------------------------------------------------------------------------
# 7. A constituent missing from the security master is flagged but still planned.
# ---------------------------------------------------------------------------
def test_constituent_missing_master_flagged_but_inserted() -> None:
    plan = build_plan(
        securities=[],  # master empty
        constituents_by_index={
            "NIFTY50": [_con("INE001A01010", "AAA", "Alpha Ltd", "Information Technology")]
        },
        current_stocks={},
        current_memberships=set(),
        deferred_indices=[],
        failed_indices={},
        effective_date=EFF,
    )
    assert "INE001A01010" in plan.constituents_missing_master
    # Still inserted using constituent-provided fields.
    assert "INE001A01010" in plan.stocks_to_insert
    assert plan.stocks_to_insert["INE001A01010"].company_name == "Alpha Ltd"


# ---------------------------------------------------------------------------
# 8. build_plan returns a UniversePlan with usable counts().
# ---------------------------------------------------------------------------
def test_returns_universeplan_with_counts() -> None:
    plan = build_plan(
        securities=[_sec("INE001A01010", "AAA", "Alpha Ltd")],
        constituents_by_index={
            "NIFTY50": [_con("INE001A01010", "AAA", "Alpha Ltd", "Information Technology")]
        },
        current_stocks={},
        current_memberships=set(),
        deferred_indices=[],
        failed_indices={},
        effective_date=EFF,
    )
    assert isinstance(plan, UniversePlan)
    counts = plan.counts()
    assert counts["stocks_to_insert"] == 1
    assert counts["memberships_to_open"] == 1
    assert plan.has_changes() is True


# ---------------------------------------------------------------------------
# 9. DesiredStock carries the fields the apply path needs.
# ---------------------------------------------------------------------------
def test_desired_stock_shape() -> None:
    plan = build_plan(
        securities=[_sec("INE001A01010", "AAA", "Alpha Ltd", date(1999, 6, 1))],
        constituents_by_index={
            "NIFTY50": [_con("INE001A01010", "AAA", "Alpha Ltd", "Healthcare")]
        },
        current_stocks={},
        current_memberships=set(),
        deferred_indices=[],
        failed_indices={},
        effective_date=EFF,
    )
    ds = plan.stocks_to_insert["INE001A01010"]
    assert isinstance(ds, DesiredStock)
    assert ds.isin == "INE001A01010"
    assert ds.nse_symbol == "AAA"
    assert ds.sector == "Pharma"  # Healthcare → Pharma
    assert ds.listed_on == date(1999, 6, 1)
