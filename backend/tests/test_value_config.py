"""Isolation + contract tests for the research-only VALUE config.

VALUE is the deep-value / "undervalued" engine: it keeps the Enhanced-F+ crash
chassis verbatim but swaps in value/cheapness-primary scoring (scoring_mode=
"value") and a buy-and-hold cadence. These tests pin that contract so the config
can never silently drift — and, critically, so a regression in Enhanced F+ /
Defensive (which VALUE must NEVER touch) trips a failure here.

NOTE: value() deliberately defaults to a DIFFERENT window (the fundamentals-
covered ~2024-06..2026-06 span) than enhanced_fplus() (CANONICAL_*), so the
field-by-field isolation test below aligns both factories to the SAME dates —
otherwise start_date/end_date would (correctly) show up as differences and mask
the real contract.
"""
from __future__ import annotations

from dataclasses import fields
from decimal import Decimal

from backend.backtest.configs import (
    ENHANCED_CASH_YIELD,
    ENHANCED_MOMENTUM_MODE,
    VALUE_END,
    VALUE_FLOOR,
    VALUE_START,
    defensive,
    enhanced_fplus,
    value,
)

# The ONLY fields VALUE is allowed to change vs Enhanced F+ (with dates aligned).
_VALUE_TILTS = {
    "scoring_mode",
    "momentum_mode",
    "top_n",
    "max_per_sector",
    "hold_buffer_rank",
    "hold_days",
    "rebalance_every",
}


def test_enhanced_fplus_unchanged() -> None:
    """Regression guard: Enhanced F+ must stay byte-identical to its frozen spec.
    If VALUE work ever perturbed the shared skeleton (or the new scoring_mode
    default), this fails first."""
    c = enhanced_fplus()
    assert c.momentum_mode == ENHANCED_MOMENTUM_MODE == "voladj"
    assert c.cash_yield_annual == ENHANCED_CASH_YIELD == Decimal("0.065")
    assert c.scoring_mode == "composite"  # the new field defaults off for Quant
    assert c.top_n == 25
    assert c.hold_days == 63 and c.rebalance_every == 63
    assert c.max_per_sector == 4
    assert c.hold_buffer_rank == 40
    assert c.quality_gate is True
    assert c.graded_exposure is True
    assert c.exposure_check_days == 5
    assert c.breakdown_exit_pct == Decimal("0.15")
    assert c.turnover_mode == "low"
    assert c.defensive_exposure is False


def test_defensive_unchanged() -> None:
    """Defensive must stay byte-identical — low-vol scoring on the composite path,
    sooner/harder de-risk ladder. VALUE never touches it."""
    c = defensive()
    assert c.momentum_mode == "lowvol"
    assert c.defensive_exposure is True
    assert c.scoring_mode == "composite"  # value scoring is NOT the defensive path


def test_value_keeps_the_crash_chassis() -> None:
    """Non-negotiable: VALUE retains every Enhanced-F+ crash protection. The only
    thing it relaxes is the SCORING gate — protection lives in the chassis."""
    c = value()
    assert c.graded_exposure is True
    assert c.quality_gate is True
    assert c.exposure_check_days == 5
    assert c.breakdown_exit_pct == Decimal("0.15")
    assert c.turnover_mode == "low"
    # standard ladder (NOT the defensive one) — same cash-sleeve code path as Quant
    assert c.defensive_exposure is False
    assert c.cash_yield_annual == Decimal("0.065")
    assert c.starting_capital == Decimal("1000000")


def test_value_is_value_primary() -> None:
    """The value tilts point the right way: value scoring path, momentum off, a
    buy-and-hold cadence, a touch more concentrated, slightly looser sector cap."""
    c = value()
    e = enhanced_fplus()
    assert c.scoring_mode == "value"  # the load-bearing switch
    assert c.momentum_mode == "off"  # no momentum primary (value, not trend)
    assert c.hold_days > e.hold_days  # long holds (126 vs 63)
    assert c.rebalance_every > e.rebalance_every
    assert c.hold_buffer_rank > e.hold_buffer_rank  # let value positions persist
    assert c.top_n < e.top_n  # a touch more concentrated (20 vs 25)
    assert c.max_per_sector > e.max_per_sector  # value clusters in cheap sectors
    # still CAPPED, not uncapped: a sector holds at most max_per_sector of top_n.
    assert c.max_per_sector is not None and c.max_per_sector < c.top_n


def test_value_default_window_is_fundamentals_covered() -> None:
    """VALUE defaults to the span where point-in-time fundamentals actually exist
    (the value scorer returns None elsewhere, so trading is restricted there)."""
    c = value()
    assert c.start_date == VALUE_START
    assert c.end_date == VALUE_END
    assert c.history_floor == VALUE_FLOOR


def test_value_restrict_isins_is_runtime() -> None:
    """restrict_isins is a run-time universe cut (None in the static config), so it
    is NOT part of the static isolation diff — same convention as core/core_balanced."""
    assert value().restrict_isins is None
    basket = ("INE002A01018", "INE467B01029")
    assert value(restrict_isins=basket).restrict_isins == basket


def test_value_differs_from_enhanced_only_in_tilts() -> None:
    """Field-by-field: VALUE == Enhanced F+ everywhere EXCEPT the declared tilts.
    Dates are aligned so start/end/history_floor do not mask the real contract."""
    c = value(VALUE_START, VALUE_END, VALUE_FLOOR)
    e = enhanced_fplus(VALUE_START, VALUE_END, VALUE_FLOOR)
    differing = {
        f.name
        for f in fields(c)
        if getattr(c, f.name) != getattr(e, f.name)
    }
    assert differing == _VALUE_TILTS, differing
