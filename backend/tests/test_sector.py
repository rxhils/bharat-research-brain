"""Tests for the Sector Agent (Chunk 3.5) — pure aggregation, no DB.

All sector signals are computed by aggregating stock-level data. The pure
functions (`pct_return`, `mean_or_none`, `pct_true`, `bull_pct`,
`classify_signal`, `build_sector_row`) are tested here with synthetic inputs.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from backend.agents.sector import (
    SectorRow,
    StockData,
    build_sector_row,
    bull_pct,
    classify_signal,
    mean_or_none,
    pct_return,
    pct_true,
)


# ---------------------------------------------------------------------------
# pct_return
# ---------------------------------------------------------------------------
def test_pct_return_positive() -> None:
    assert pct_return(Decimal("110"), Decimal("100")) == Decimal("10")


def test_pct_return_negative() -> None:
    assert pct_return(Decimal("90"), Decimal("100")) == Decimal("-10")


def test_pct_return_none_inputs() -> None:
    assert pct_return(None, Decimal("100")) is None
    assert pct_return(Decimal("100"), None) is None
    assert pct_return(Decimal("100"), Decimal("0")) is None


# ---------------------------------------------------------------------------
# mean_or_none / pct_true / bull_pct
# ---------------------------------------------------------------------------
def test_mean_or_none() -> None:
    assert mean_or_none([Decimal("1"), Decimal("2"), Decimal("3")]) == Decimal("2")
    assert mean_or_none([Decimal("1"), None, Decimal("3")]) == Decimal("2")
    assert mean_or_none([None, None]) is None
    assert mean_or_none([]) is None


def test_pct_true() -> None:
    assert pct_true([True, True, False, False]) == Decimal("50")
    assert pct_true([True, None, False]) == Decimal("50")  # None ignored
    assert pct_true([]) == Decimal("0")


def test_bull_pct() -> None:
    assert bull_pct(["bull", "bear", "bull", "neutral"]) == Decimal("50")
    assert bull_pct([]) is None


# ---------------------------------------------------------------------------
# classify_signal
# ---------------------------------------------------------------------------
def test_classify_leading() -> None:
    assert classify_signal(Decimal("60"), Decimal("70"), Decimal("1.5")) == "leading"


def test_classify_lagging_low_rsi() -> None:
    assert classify_signal(Decimal("40"), Decimal("70"), Decimal("1.0")) == "lagging"


def test_classify_lagging_low_pct() -> None:
    assert classify_signal(Decimal("60"), Decimal("35"), Decimal("1.0")) == "lagging"


def test_classify_lagging_neg_momentum() -> None:
    assert classify_signal(Decimal("60"), Decimal("70"), Decimal("-1.5")) == "lagging"


def test_classify_neutral() -> None:
    assert classify_signal(Decimal("50"), Decimal("50"), Decimal("0.5")) == "neutral"


def test_classify_neutral_when_none() -> None:
    assert classify_signal(None, None, None) == "neutral"


# ---------------------------------------------------------------------------
# build_sector_row — full aggregation
# ---------------------------------------------------------------------------
def test_build_sector_row() -> None:
    stocks = [
        StockData(Decimal("60"), True, Decimal("2"), Decimal("5")),
        StockData(Decimal("58"), True, Decimal("1"), Decimal("3")),
        StockData(Decimal("56"), False, Decimal("0.5"), Decimal("1")),
    ]
    row = build_sector_row(
        "IT",
        date(2026, 5, 22),
        stocks,
        sentiment_scores=[Decimal("0.5"), Decimal("-0.2")],
        sentiment_labels=["bull", "bear"],
    )
    assert isinstance(row, SectorRow)
    assert row.sector == "IT"
    assert row.computed_date == date(2026, 5, 22)
    assert row.stock_count == 3
    assert row.avg_rsi_14 == Decimal("58.0000")
    assert row.pct_above_ema200 == Decimal("66.6667")  # 2 of 3
    assert row.momentum_7d == Decimal("1.1667")  # (2+1+0.5)/3
    assert row.momentum_30d == Decimal("3.0000")  # (5+3+1)/3
    assert row.avg_sentiment_score == Decimal("0.1500")
    assert row.bull_article_pct == Decimal("50.0000")
    assert row.signal == "leading"
    assert row.source == "sector_agent"


def test_build_sector_row_empty_is_neutral() -> None:
    row = build_sector_row("Empty", date(2026, 5, 22), [], [], [])
    assert row.stock_count == 0
    assert row.avg_rsi_14 is None
    assert row.pct_above_ema200 == Decimal("0.0000")
    assert row.avg_sentiment_score is None
    assert row.bull_article_pct is None
    assert row.signal == "neutral"
