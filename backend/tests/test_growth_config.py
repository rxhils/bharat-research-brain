"""Isolation + contract tests for the research-only GROWTH config.

Growth is "Enhanced F+ turned up": the SAME crash chassis with three aggression
knobs dialed up. These tests pin that contract so the config can never silently
drift — and, critically, so a regression in Enhanced F+/F+ CLASSIC (which Growth
must NEVER touch) trips a failure here.
"""
from __future__ import annotations

from dataclasses import fields
from decimal import Decimal

from backend.backtest.configs import (
    ENHANCED_CASH_YIELD,
    ENHANCED_MOMENTUM_MODE,
    enhanced_fplus,
    fplus_classic,
    growth,
)

# The ONLY fields Growth is allowed to change vs Enhanced F+.
_GROWTH_TILTS = {"top_n", "max_per_sector", "hold_buffer_rank"}


def test_enhanced_fplus_unchanged() -> None:
    """Regression guard: Enhanced F+ must stay byte-identical to its frozen spec.
    If Growth work ever perturbed the shared skeleton, this fails first."""
    c = enhanced_fplus()
    assert c.momentum_mode == ENHANCED_MOMENTUM_MODE == "voladj"
    assert c.cash_yield_annual == ENHANCED_CASH_YIELD == Decimal("0.065")
    assert c.top_n == 25
    assert c.hold_days == 63 and c.rebalance_every == 63
    assert c.max_per_sector == 4
    assert c.hold_buffer_rank == 40
    assert c.quality_gate is True
    assert c.graded_exposure is True
    assert c.exposure_check_days == 5
    assert c.breakdown_exit_pct == Decimal("0.15")
    assert c.turnover_mode == "low"
    assert c.defensive_exposure is False  # never the defensive ladder


def test_fplus_classic_unchanged() -> None:
    """F+ CLASSIC (the preserved fallback) stays frozen — momentum + cash off."""
    c = fplus_classic()
    assert c.momentum_mode == "off"
    assert c.cash_yield_annual == Decimal("0")
    assert c.top_n == 25
    assert c.defensive_exposure is False


def test_growth_keeps_the_crash_chassis() -> None:
    """Non-negotiable: Growth retains every Enhanced-F+ crash protection."""
    c = growth()
    # cash lever + stops + quality gate kept verbatim
    assert c.graded_exposure is True
    assert c.quality_gate is True
    assert c.exposure_check_days == 5
    assert c.breakdown_exit_pct == Decimal("0.15")
    assert c.turnover_mode == "low"
    # standard ladder (NOT the defensive one) — same code path as Enhanced F+
    assert c.defensive_exposure is False
    # the kept tilts: vol-adj momentum + 6.5% cash yield
    assert c.momentum_mode == "voladj"
    assert c.cash_yield_annual == Decimal("0.065")
    # same hold/rebalance cadence and capital as Enhanced F+
    assert c.hold_days == 63 and c.rebalance_every == 63
    assert c.starting_capital == Decimal("1000000")


def test_growth_is_more_aggressive() -> None:
    """The aggression tilts point the right way (more concentrated, looser sector
    cap, winners held longer) — i.e. it really is 'turned up', not turned down."""
    c = growth()
    e = enhanced_fplus()
    assert c.top_n < e.top_n  # more concentrated
    assert c.max_per_sector > e.max_per_sector  # leaders may cluster
    assert c.hold_buffer_rank > e.hold_buffer_rank  # let winners run
    # still CAPPED, not Config C: a sector can hold at most max_per_sector of top_n.
    assert c.max_per_sector is not None and c.max_per_sector < c.top_n


def test_growth_differs_from_enhanced_only_in_tilts() -> None:
    """Field-by-field: Growth == Enhanced F+ everywhere EXCEPT the three tilts.
    This is the isolation contract — it catches any accidental extra divergence."""
    c = growth()
    e = enhanced_fplus()
    differing = {
        f.name
        for f in fields(c)
        if getattr(c, f.name) != getattr(e, f.name)
    }
    assert differing == _GROWTH_TILTS, differing
