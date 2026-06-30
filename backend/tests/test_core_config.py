"""Isolation + contract tests for the research-only CORE config.

Core is "the dependable all-weather anchor": the SAME Enhanced-F+ crash chassis
with steadiness knobs dialed (momentum OFF, more diversified, tighter sector
caps, lower turnover) and the universe restricted to a large-cap basket at run
time. These tests pin that contract so the config can never silently drift — and,
critically, so a regression in Enhanced F+ (Quant) or Defensive (which Core must
NEVER touch) trips a failure here.
"""
from __future__ import annotations

from dataclasses import fields
from decimal import Decimal

from backend.backtest.configs import (
    ENHANCED_CASH_YIELD,
    ENHANCED_MOMENTUM_MODE,
    concentrated,
    core,
    core_balanced,
    defensive,
    enhanced_fplus,
)


def test_concentrated_is_enhanced_plus_top10() -> None:
    """LIVE-candidate isolation contract: Concentrated == Enhanced F+ (Quant) with
    ONLY top_n changed (25 -> 10). Every other field byte-identical to Quant."""
    c = concentrated()
    e = enhanced_fplus()
    assert c.top_n == 10
    assert c.momentum_mode == "voladj"  # same as Quant (NOT off/lowvol/raw)
    assert c.cash_yield_annual == Decimal("0.065")
    assert c.quality_gate is True
    assert c.breakdown_exit_pct == Decimal("0.15")
    assert c.exposure_check_days == 5
    assert c.defensive_exposure is False  # standard ladder, same as Quant
    # the ONLY difference vs Quant is top_n
    differing = {f.name for f in fields(c) if getattr(c, f.name) != getattr(e, f.name)}
    assert differing == {"top_n"}, differing


def test_concentrated_has_brakes_on_not_allin() -> None:
    """NON-NEGOTIABLE: Concentrated keeps the brakes — it is NOT the no-brakes
    ALL-IN (Config-C) variant, and NOT top-8/top-15."""
    c = concentrated()
    assert c.graded_exposure is True  # BRAKES ON (ALL-IN would be False)
    assert c.top_n == 10  # not 8, not 15

# The ONLY fields New Core (core_balanced) may change vs Enhanced F+ (Quant).
# restrict_isins is run-time (None in the static config), so not a static diff.
_CORE_BAL_TILTS = {
    "momentum_mode",
    "top_n",
    "max_per_sector",
    "hold_buffer_rank",
    "hold_days",
    "rebalance_every",
}

# The ONLY fields Core is allowed to change vs Enhanced F+ (Quant). restrict_isins
# is injected at RUN TIME (None in the static config), so it is not a static diff.
_CORE_TILTS = {
    "momentum_mode",
    "top_n",
    "max_per_sector",
    "hold_buffer_rank",
    "hold_days",
    "rebalance_every",
}


def test_enhanced_fplus_unchanged() -> None:
    """Regression guard: Quant (Enhanced F+) must stay byte-identical to its frozen
    spec. If Core work ever perturbed the shared skeleton, this fails first."""
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
    assert c.defensive_exposure is False
    assert c.restrict_isins is None


def test_defensive_unchanged() -> None:
    """Regression guard: Defensive must stay byte-identical to its frozen spec."""
    c = defensive()
    assert c.momentum_mode == "lowvol"
    assert c.cash_yield_annual == Decimal("0.065")
    assert c.defensive_exposure is True  # the sooner/harder ladder — Core never uses
    assert c.top_n == 25
    assert c.hold_days == 63 and c.rebalance_every == 63
    assert c.max_per_sector == 4
    assert c.hold_buffer_rank == 40
    assert c.restrict_isins is None


def test_core_keeps_the_crash_chassis() -> None:
    """Non-negotiable: Core retains every Enhanced-F+ crash protection."""
    c = core()
    assert c.graded_exposure is True
    assert c.quality_gate is True
    assert c.exposure_check_days == 5
    assert c.breakdown_exit_pct == Decimal("0.15")
    assert c.turnover_mode == "low"
    # standard ladder (NOT the defensive one) — same code path as Enhanced F+
    assert c.defensive_exposure is False
    # honest accounting kept
    assert c.cash_yield_annual == Decimal("0.065")
    assert c.starting_capital == Decimal("1000000")


def test_core_steadiness_tilts() -> None:
    """The steadiness tilts point the right way: less momentum, more diversified,
    tighter caps, lower turnover, anchors held longer."""
    c = core()
    e = enhanced_fplus()
    assert c.momentum_mode == "off"  # less momentum than Quant's "voladj"
    assert c.momentum_mode != "lowvol"  # and NOT Defensive's low-vol tilt
    assert c.top_n > e.top_n  # more diversified (40 vs 25)
    assert c.max_per_sector < e.max_per_sector  # tighter sector caps (3 vs 4)
    assert c.hold_days > e.hold_days  # lower turnover (126 vs 63)
    assert c.rebalance_every > e.rebalance_every
    assert c.hold_buffer_rank > e.hold_buffer_rank  # anchors persist (60 vs 40)
    # still CAPPED, not concentrated: a sector can hold at most max_per_sector of top_n
    assert c.max_per_sector is not None and c.max_per_sector < c.top_n


def test_core_differs_from_enhanced_only_in_tilts() -> None:
    """Field-by-field: Core == Enhanced F+ everywhere EXCEPT the steadiness tilts
    (restrict_isins is run-time, None in the static config). This is the isolation
    contract — it catches any accidental extra divergence."""
    c = core()
    e = enhanced_fplus()
    differing = {
        f.name
        for f in fields(c)
        if getattr(c, f.name) != getattr(e, f.name)
    }
    assert differing == _CORE_TILTS, differing


def test_core_restrict_isins_is_runtime() -> None:
    """The large-cap universe is injected at run time; default is the full universe.
    A passed basket must land on the config verbatim (the Nifty-100 differentiator)."""
    assert core().restrict_isins is None
    basket = ("INE001A01001", "INE002A01018")
    assert core(restrict_isins=basket).restrict_isins == basket


# ---- New Core (core_balanced) — redesigned flagship -----------------------
def test_core_balanced_keeps_the_crash_chassis() -> None:
    """New Core retains every Enhanced-F+ crash protection (standard ladder)."""
    c = core_balanced()
    assert c.graded_exposure is True
    assert c.quality_gate is True
    assert c.exposure_check_days == 5
    assert c.breakdown_exit_pct == Decimal("0.15")
    assert c.turnover_mode == "low"
    assert c.defensive_exposure is False  # standard ladder, NOT Defensive's
    assert c.cash_yield_annual == Decimal("0.065")
    assert c.starting_capital == Decimal("1000000")


def test_core_balanced_is_a_balanced_redesign() -> None:
    """New Core: momentum ON but RAW (≠ Quant's voladj, ≠ old Core's off),
    diversified (top-40), tighter caps (3), moderate turnover (84-day)."""
    c = core_balanced()
    e = enhanced_fplus()
    assert c.momentum_mode == "raw"  # ON, but different from Quant's voladj
    assert c.momentum_mode != e.momentum_mode == "voladj"  # not full-Quant momentum
    assert c.momentum_mode != "off"  # not old Core's switched-off momentum
    assert c.top_n > e.top_n  # more diversified (40 vs 25)
    assert c.max_per_sector < e.max_per_sector  # tighter caps (3 vs 4)
    assert e.rebalance_every < c.rebalance_every  # moderate, calmer than Quant (84 vs 63)
    assert c.rebalance_every == 84 and c.hold_days == 84


def test_core_balanced_differs_from_old_core() -> None:
    """It is a genuinely different design, NOT old core() with knobs tweaked:
    momentum ON (not off) and a faster (84 vs 126) cadence."""
    nc = core_balanced()
    oc = core()
    assert nc.momentum_mode == "raw" and oc.momentum_mode == "off"
    assert nc.rebalance_every == 84 and oc.rebalance_every == 126


def test_core_balanced_differs_from_enhanced_only_in_tilts() -> None:
    """Isolation contract: New Core == Enhanced F+ everywhere EXCEPT its tilts
    (restrict_isins is run-time). Catches any accidental extra divergence and any
    drift in the shared Quant skeleton."""
    c = core_balanced()
    e = enhanced_fplus()
    differing = {f.name for f in fields(c) if getattr(c, f.name) != getattr(e, f.name)}
    assert differing == _CORE_BAL_TILTS, differing
