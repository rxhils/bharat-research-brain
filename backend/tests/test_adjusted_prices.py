"""Tests for the pure back-adjustment engine (Chunk 2.1).

`adjust_series` is pure: given a raw OHLCV series + that stock's corporate
actions, it returns the back-adjusted series. Adjustments are applied
most-recent-first: a split on date D divides every price strictly before D by
the split factor (and multiplies volume by it); a dividend of X on ex_date D
subtracts X from every price strictly before D.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from backend.agents.adjusted_prices import (
    Action,
    AdjBar,
    RawBar,
    adjust_series,
)

D = Decimal


def _bar(d: date, close: str, *, volume: int = 1000) -> RawBar:
    c = D(close)
    return RawBar(trade_date=d, open=c, high=c, low=c, close=c, volume=volume)


def _split(d: date, factor: str) -> Action:
    return Action(d, "split", D(factor), D(1), None)


def _div(d: date, amount: str) -> Action:
    return Action(d, "dividend", None, None, D(amount))


def _by_date(bars: list[AdjBar]) -> dict[date, AdjBar]:
    return {b.trade_date: b for b in bars}


# ---------------------------------------------------------------------------
# 1. Split back-adjustment (the critical case)
# ---------------------------------------------------------------------------
def test_split_back_adjust() -> None:
    bars = [_bar(date(2024, 10, 27), "2700"), _bar(date(2024, 10, 28), "1354")]
    out = _by_date(adjust_series(bars, [_split(date(2024, 10, 28), "2")]))
    assert out[date(2024, 10, 27)].adj_close == D("1350.0000")
    assert out[date(2024, 10, 27)].adj_volume == 2000
    assert out[date(2024, 10, 28)].adj_close == D("1354.0000")
    assert out[date(2024, 10, 28)].adj_volume == 1000


# ---------------------------------------------------------------------------
# 2. Dividend back-adjustment (subtractive, before ex_date only)
# ---------------------------------------------------------------------------
def test_dividend_back_adjust() -> None:
    bars = [_bar(date(2024, 1, 1), "100"), _bar(date(2024, 6, 1), "110")]
    out = _by_date(adjust_series(bars, [_div(date(2024, 6, 1), "5")]))
    assert out[date(2024, 1, 1)].adj_close == D("95.0000")
    assert out[date(2024, 6, 1)].adj_close == D("110.0000")


# ---------------------------------------------------------------------------
# 3. Combined split + dividend, most-recent-first (Reliance shape)
# ---------------------------------------------------------------------------
def test_combined_most_recent_first() -> None:
    bars = [_bar(date(2024, 10, 27), "2700"), _bar(date(2024, 10, 28), "1354")]
    actions = [_split(date(2024, 10, 28), "2"), _div(date(2025, 8, 14), "5.5")]
    out = _by_date(adjust_series(bars, actions))
    # 2024-10-27: most recent (div 5.5) first -> 2694.5, then /2 -> 1347.25
    assert out[date(2024, 10, 27)].adj_close == D("1347.2500")
    # 2024-10-28: only the later dividend applies -> 1348.5
    assert out[date(2024, 10, 28)].adj_close == D("1348.5000")


# ---------------------------------------------------------------------------
# 4. No actions → adjusted equals raw
# ---------------------------------------------------------------------------
def test_no_actions_passthrough() -> None:
    bars = [_bar(date(2024, 1, 1), "100", volume=500)]
    out = _by_date(adjust_series(bars, []))
    assert out[date(2024, 1, 1)].adj_close == D("100.0000")
    assert out[date(2024, 1, 1)].adj_volume == 500
    assert out[date(2024, 1, 1)].adj_factor == D("1")


# ---------------------------------------------------------------------------
# 5. Reverse split (factor < 1) raises historical prices
# ---------------------------------------------------------------------------
def test_reverse_split() -> None:
    bars = [_bar(date(2023, 1, 1), "50"), _bar(date(2023, 6, 1), "100")]
    out = _by_date(adjust_series(bars, [_split(date(2023, 6, 1), "0.5")]))
    assert out[date(2023, 1, 1)].adj_close == D("100.0000")


# ---------------------------------------------------------------------------
# 6. None prices / volume survive untouched
# ---------------------------------------------------------------------------
def test_none_values() -> None:
    bars = [
        RawBar(date(2024, 1, 1), None, None, None, None, None),
        _bar(date(2024, 6, 1), "110"),
    ]
    out = _by_date(adjust_series(bars, [_split(date(2024, 6, 1), "2")]))
    b = out[date(2024, 1, 1)]
    assert b.adj_close is None
    assert b.adj_volume is None


# ---------------------------------------------------------------------------
# 7. adj_factor records the cumulative split divisor
# ---------------------------------------------------------------------------
def test_adj_factor_tracks_splits() -> None:
    bars = [_bar(date(2022, 1, 1), "400")]
    actions = [_split(date(2023, 1, 1), "2"), _split(date(2024, 1, 1), "2")]
    out = _by_date(adjust_series(bars, actions))
    assert out[date(2022, 1, 1)].adj_factor == D("4")
    assert out[date(2022, 1, 1)].adj_close == D("100.0000")
