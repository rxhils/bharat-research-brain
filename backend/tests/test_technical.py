"""Tests for pure technical-indicator math (Chunk 3.1).

RSI (Wilder), EMA, MACD, ATR, and a delivery average — all pure functions on
synthetic series, no DB or network.
"""
from __future__ import annotations

import pytest

from backend.agents.technical_indicators import (
    atr,
    avg_last_n,
    ema,
    macd,
    rsi,
)


# ---------------------------------------------------------------------------
# RSI (Wilder, 14)
# ---------------------------------------------------------------------------
def test_rsi_all_gains_is_100() -> None:
    assert rsi([float(i) for i in range(1, 30)], 14) == pytest.approx(100.0)


def test_rsi_all_losses_is_0() -> None:
    assert rsi([float(i) for i in range(30, 1, -1)], 14) == pytest.approx(0.0)


def test_rsi_insufficient_is_none() -> None:
    assert rsi([1.0, 2.0, 3.0], 14) is None


def test_rsi_mixed_is_bounded() -> None:
    closes = [
        10, 11, 10.5, 11.5, 12, 11, 11.8, 12.5, 12.2, 13, 12.7, 13.5, 14, 13.6, 14.2, 15
    ]
    r = rsi([float(c) for c in closes], 14)
    assert r is not None and 0.0 <= r <= 100.0


# ---------------------------------------------------------------------------
# EMA
# ---------------------------------------------------------------------------
def test_ema_constant_equals_constant() -> None:
    assert ema([10.0] * 30, 20) == pytest.approx(10.0)


def test_ema_insufficient_is_none() -> None:
    assert ema([1.0, 2.0, 3.0], 20) is None


def test_ema_lags_uptrend() -> None:
    closes = [float(i) for i in range(1, 41)]
    e = ema(closes, 20)
    assert e is not None and e < closes[-1]  # EMA lags a rising series


# ---------------------------------------------------------------------------
# MACD (12, 26, 9)
# ---------------------------------------------------------------------------
def test_macd_constant_is_zero() -> None:
    line, signal, hist = macd([50.0] * 60)
    assert line == pytest.approx(0.0, abs=1e-9)
    assert signal == pytest.approx(0.0, abs=1e-9)
    assert hist == pytest.approx(0.0, abs=1e-9)


def test_macd_insufficient_is_none() -> None:
    assert macd([1.0, 2.0, 3.0]) == (None, None, None)


def test_macd_uptrend_line_positive() -> None:
    closes = [float(i) for i in range(1, 80)]
    line, _signal, _hist = macd(closes)
    assert line is not None and line > 0  # fast EMA above slow in an uptrend


# ---------------------------------------------------------------------------
# ATR (14)
# ---------------------------------------------------------------------------
def test_atr_constant_range() -> None:
    # each bar: low=100, high=110 (range 10), close=105; flat across bars
    highs = [110.0] * 20
    lows = [100.0] * 20
    closes = [105.0] * 20
    assert atr(highs, lows, closes, 14) == pytest.approx(10.0)


def test_atr_insufficient_is_none() -> None:
    assert atr([1.0], [1.0], [1.0], 14) is None


# ---------------------------------------------------------------------------
# Delivery average (last N, skipping nulls)
# ---------------------------------------------------------------------------
def test_avg_last_n() -> None:
    assert avg_last_n([1.0, 2.0, None, 4.0], 3) == pytest.approx(3.0)  # last3=[2,None,4]


def test_avg_last_n_all_none() -> None:
    assert avg_last_n([None, None], 5) is None
    assert avg_last_n([], 5) is None
