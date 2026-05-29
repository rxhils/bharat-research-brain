"""Tests for market-breadth signals (Chunk 4.12) — pure classifiers + regime
override. All synthetic; no DB, no network.

The three breadth indicators (advance/decline ratio, % above EMA200, 52-week
high/low ratio) are derived from existing DB tables by `compute_breadth`, but the
scoring/threshold logic is pure and unit-tested here. The DB SQL itself is
exercised by the live `macro run` verification step, consistent with how the
other `fetch_*` I/O methods are not unit-tested.
"""
from __future__ import annotations

from decimal import Decimal

from backend.agents.macro import (
    NIFTY,
    PCT_EMA200,
    MacroReading,
    advance_decline_signal,
    compute_regime,
    new_high_low_signal,
    pct_above_ema200_signal,
)


def _r(indicator: str, value: Decimal | None, signal: str) -> MacroReading:
    return MacroReading(indicator, value, signal, Decimal("0"), "test")


# ---------------------------------------------------------------------------
# advance_decline_signal
# ---------------------------------------------------------------------------
def test_advance_decline_rising() -> None:
    ratio, signal = advance_decline_signal(300, 100)
    assert ratio == Decimal(3)
    assert signal == "rising"


def test_advance_decline_falling() -> None:
    ratio, signal = advance_decline_signal(80, 200)
    assert ratio == Decimal("0.4")
    assert signal == "falling"


def test_advance_decline_stable() -> None:
    ratio, signal = advance_decline_signal(150, 150)
    assert ratio == Decimal(1)
    assert signal == "stable"


def test_advance_decline_zero_declining() -> None:
    # all advancing, 0 declining -> ratio defaults to 1.0, no ZeroDivisionError
    ratio, signal = advance_decline_signal(300, 0)
    assert ratio == Decimal(1)
    assert signal == "stable"


# ---------------------------------------------------------------------------
# pct_above_ema200_signal
# ---------------------------------------------------------------------------
def test_pct_above_ema200_bullish() -> None:
    pct, signal = pct_above_ema200_signal(340, 507)  # 340 above, 167 below
    assert int(pct) == 67
    assert signal == "bullish"


def test_pct_above_ema200_bearish() -> None:
    pct, signal = pct_above_ema200_signal(150, 507)  # 150 above, 357 below
    assert int(pct) == 29
    assert signal == "bearish"


def test_pct_above_ema200_neutral() -> None:
    pct, signal = pct_above_ema200_signal(300, 507)  # 300 above, 207 below
    assert int(pct) == 59
    assert signal == "neutral"


# ---------------------------------------------------------------------------
# regime override on low breadth
# ---------------------------------------------------------------------------
def test_regime_override_low_breadth() -> None:
    # Nifty rising (above 200d MA) would normally lean risk-on, but breadth
    # under 30% above EMA200 forces risk-off.
    readings = {
        NIFTY: _r(NIFTY, Decimal("1"), "rising"),
        PCT_EMA200: _r(PCT_EMA200, Decimal("28"), "bearish"),
    }
    assert compute_regime(readings) == "risk-off"


# ---------------------------------------------------------------------------
# new_high_low_signal
# ---------------------------------------------------------------------------
def test_new_high_low_strong() -> None:
    ratio, signal = new_high_low_signal(40, 10)
    assert ratio == Decimal(4)
    assert signal == "strong"


def test_new_high_low_weak() -> None:
    ratio, signal = new_high_low_signal(10, 40)
    assert ratio == Decimal("0.25")
    assert signal == "weak"


def test_new_high_low_zero_lows() -> None:
    # 20 near high, 0 near low -> ratio defaults to 1.0, no ZeroDivisionError
    ratio, signal = new_high_low_signal(20, 0)
    assert ratio == Decimal(1)
    assert signal == "neutral"
