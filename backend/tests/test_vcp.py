"""Tests for the VCP / Minervini screener scoring (Chunk 4.10).

All synthetic, in-memory series — no DB, no files. The scoring functions in
`backend.agents.vcp` are PURE: they take a PriceSeries (list of
(date, high, low, close, volume) tuples, oldest first) and return scores. The
agent's `run_all` exercises the DB path live.

VCP = Volatility Contraction Pattern (Minervini): progressively shrinking
pullbacks inside an established uptrend, with volume drying up, forming a base
before a breakout. The Trend Template is the uptrend gate; contraction analysis
detects the base; pivot proximity + relative strength time it.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from backend.agents.ranking import TechInputs, score_technical
from backend.agents.vcp import (
    compute_vcp_score,
    detect_volume_dryup,
    find_contractions,
    score_pivot_proximity,
    score_relative_strength,
    score_trend_template,
)

PriceRow = tuple[date, float, float, float, float]


def _ramp(start: float, end: float, n: int) -> list[float]:
    """n evenly spaced points from start to end inclusive."""
    if n == 1:
        return [start]
    step = (end - start) / (n - 1)
    return [start + step * i for i in range(n)]


def _zigzag(points: list[float], seg: int = 4) -> list[float]:
    """Ramp between successive corner points with `seg` new bars per leg.

    Only the corner closes become swing pivots; the linear legs between are
    monotonic, so no intermediate bar is a local extreme.
    """
    closes = [points[0]]
    for nxt in points[1:]:
        closes += _ramp(closes[-1], nxt, seg + 1)[1:]
    return closes


def _bars(closes: list[float], vols: list[float] | None = None) -> list[PriceRow]:
    """Build (date, high, low, close, volume); high=close+0.5, low=close-0.5."""
    if vols is None:
        vols = [1_000_000.0] * len(closes)
    base = date(2025, 1, 1)
    return [
        (base + timedelta(days=i), c + 0.5, c - 0.5, c, v)
        for i, (c, v) in enumerate(zip(closes, vols, strict=True))
    ]


# --- trend template (4 conditions x 25) ------------------------------------


def test_trend_all_conditions_met() -> None:
    # Clean monotonic uptrend: close > EMA50 > EMA200, close >> 52w low x1.25.
    prices = _bars(_ramp(100.0, 320.0, 240))
    assert score_trend_template(prices) == Decimal(100)


def test_trend_two_conditions() -> None:
    # Long downtrend then a recent recovery: only (close>EMA50) and
    # (close>52w_low x1.25) hold; close<EMA200 and EMA50<EMA200 fail.
    closes = _ramp(300.0, 120.0, 200) + _ramp(120.0, 180.0, 41)[1:]
    assert score_trend_template(_bars(closes)) == Decimal(50)


def test_trend_none_met() -> None:
    # Monotonic downtrend: every condition fails (close near 52w low).
    prices = _bars(_ramp(320.0, 100.0, 240))
    assert score_trend_template(prices) == Decimal(0)


# --- contractions (count, quality) -----------------------------------------


def test_three_valid_contractions() -> None:
    # Shrinking pullbacks: depths ~0.31 -> 0.21 -> 0.14 (each <= prev x0.9).
    closes = _zigzag([60.0, 100.0, 70.0, 95.0, 76.0, 90.0, 78.0, 84.0])
    count, quality = find_contractions(_bars(closes))
    assert count == 3
    assert quality == Decimal(75)


def test_one_contraction() -> None:
    closes = _zigzag([60.0, 100.0, 70.0, 85.0])
    count, quality = find_contractions(_bars(closes))
    assert count == 1
    assert quality == Decimal(25)


def test_no_contractions() -> None:
    # Straight ramp up: no interior swing pivots at all.
    count, quality = find_contractions(_bars(_ramp(70.0, 120.0, 30)))
    assert count == 0
    assert quality == Decimal(0)


def test_contractions_not_decreasing() -> None:
    # Two contractions but the second is DEEPER than the first -> invalid.
    closes = _zigzag([60.0, 100.0, 90.0, 95.0, 66.5, 72.0])
    count, _quality = find_contractions(_bars(closes))
    assert count == 0


# --- contractions on realistic (non-clean) shapes --------------------------
# Real Indian price series never give a perfect 10%-shallower staircase: legs
# tick up slightly inside an overall-tightening base, and intrabar chop spawns
# spurious 3-bar pivots. These guard the loosened detector (5-bar pivots, 3%
# min-depth, 20% per-leg tolerance, must contract overall).


def _jitter(closes: list[float], *, every: int, amp: float) -> list[float]:
    """Add alternating +/-amp to non-corner bars (corners are multiples of
    `every`). Models intrabar chop that fools a 3-bar pivot but not a 5-bar one.
    """
    return [
        c if i % every == 0 else c + (amp if i % 2 else -amp)
        for i, c in enumerate(closes)
    ]


def test_noisy_shrinking_contractions_detected() -> None:
    # Depths ~12% -> 13% -> 7%: the middle leg ticks UP slightly (within the
    # 20% tolerance) but the base still contracts overall. The old strict
    # ">=10% shallower every leg" rule rejected this; the loosened rule accepts.
    # Trailing corner (100) keeps the third trough interior so all 3 legs pair.
    closes = _zigzag([80.0, 100.0, 88.0, 101.0, 87.87, 102.0, 94.86, 100.0])
    count, quality = find_contractions(_bars(closes))
    assert count == 3
    assert quality == Decimal(75)


def test_flat_oscillation_not_detected() -> None:
    # Equal ~10% pullbacks that never tighten -> not a contracting base.
    closes = _zigzag([90.0, 100.0, 90.0, 100.0, 90.0, 100.0, 90.0])
    count, _quality = find_contractions(_bars(closes))
    assert count == 0


def test_five_bar_pivots_ignore_intrabar_noise() -> None:
    # A clean 3-leg tightening base with intrabar chop injected. 3-bar pivots
    # would shatter the depth sequence into noise; 5-bar pivots see only the
    # real corners, so the contraction count survives.
    base = _zigzag([80.0, 130.0, 110.0, 132.0, 116.0, 130.0, 120.0], seg=6)
    noisy = _jitter(base, every=6, amp=3.0)
    count, _quality = find_contractions(_bars(noisy))
    assert count >= 2


# --- volume dry-up ----------------------------------------------------------


def test_volume_dryup_true() -> None:
    vols = [1_000_000.0] * 50 + _ramp(600_000.0, 300_000.0, 10)
    closes = _ramp(100.0, 130.0, 60)
    assert detect_volume_dryup(_bars(closes, vols)) is True


def test_volume_dryup_false() -> None:
    vols = [1_000_000.0] * 60
    closes = _ramp(100.0, 130.0, 60)
    assert detect_volume_dryup(_bars(closes, vols)) is False


# --- pivot proximity --------------------------------------------------------


def test_within_2pct() -> None:
    # pivot (max close) = 100, current = 99 -> 1% away.
    closes = _zigzag([90.0, 100.0, 99.0])
    assert score_pivot_proximity(_bars(closes)) == Decimal(100)


def test_within_10pct() -> None:
    # pivot = 100, current = 92 -> 8% away.
    closes = _zigzag([90.0, 100.0, 92.0])
    assert score_pivot_proximity(_bars(closes)) == Decimal(50)


def test_beyond_20pct() -> None:
    # pivot = 100, current = 75 -> 25% away.
    closes = _zigzag([90.0, 100.0, 75.0])
    assert score_pivot_proximity(_bars(closes)) == Decimal(0)


# --- relative strength (vs Nifty) ------------------------------------------


def test_relative_strength_strong() -> None:
    stock = _bars(_ramp(100.0, 130.0, 63))  # +30%
    nifty = _bars(_ramp(100.0, 105.0, 63))  # +5% -> rs +0.25
    assert score_relative_strength(stock, nifty) == Decimal(100)


def test_relative_strength_weak() -> None:
    stock = _bars(_ramp(100.0, 95.0, 63))  # -5%
    nifty = _bars(_ramp(100.0, 110.0, 63))  # +10% -> rs -0.15
    assert score_relative_strength(stock, nifty) == Decimal(0)


# --- composite --------------------------------------------------------------


def test_strong_vcp_detected() -> None:
    detected, score = compute_vcp_score(
        trend=Decimal(100),
        contractions=3,
        quality=Decimal(75),
        volume_dryup=True,
        proximity=Decimal(100),
        rs=Decimal(100),
    )
    assert detected is True
    assert score >= Decimal(40)


def test_weak_setup_not_detected() -> None:
    # trend < 75 -> never detected, regardless of the other components.
    detected, _score = compute_vcp_score(
        trend=Decimal(50),
        contractions=3,
        quality=Decimal(75),
        volume_dryup=True,
        proximity=Decimal(100),
        rs=Decimal(100),
    )
    assert detected is False


# --- ranking integration (VCP bonus in score_technical) --------------------


def _neutral_tech(**kw: object) -> TechInputs:
    return TechInputs(
        rsi_14=Decimal(50),
        price_vs_ema200=None,
        ema_cross=None,
        macd_hist=None,
        **kw,  # type: ignore[arg-type]
    )


def test_vcp_bonus_strong() -> None:
    base = score_technical(_neutral_tech())
    strong = score_technical(
        _neutral_tech(vcp_detected=True, vcp_score=Decimal(70))
    )
    assert strong - base == Decimal(10)


def test_vcp_bonus_developing() -> None:
    base = score_technical(_neutral_tech())
    developing = score_technical(
        _neutral_tech(vcp_detected=True, vcp_score=Decimal(45))
    )
    assert developing - base == Decimal(5)


def test_vcp_no_bonus() -> None:
    base = score_technical(_neutral_tech())
    none = score_technical(
        _neutral_tech(vcp_detected=False, vcp_score=Decimal(95))
    )
    assert none - base == Decimal(0)
