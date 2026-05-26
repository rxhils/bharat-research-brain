"""Tests for the FII/DII Agent (Chunk 3.6) — pure parse + rolling + signal.

Source is a locally-saved NSDL/SEBI FPI file (no automated NSE scraping — that
violates CLAUDE.md §2 rule 5). `fii_net_cr` carries FPI net equity (the FII
proxy); `dii_net_cr` is not published by NSDL/SEBI and may be None. All pure
functions are tested with synthetic data — no network, no file, no DB.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from backend.agents.fii_dii import (
    FlowRow,
    RawFlow,
    classify_fii_signal,
    compute_rolling,
    parse_flows_csv,
)


# ---------------------------------------------------------------------------
# classify_fii_signal — 5-day rolling sum thresholds (crores)
# ---------------------------------------------------------------------------
def test_signal_strong_buy() -> None:
    assert classify_fii_signal(Decimal("5001")) == "strong_buy"


def test_signal_buy() -> None:
    assert classify_fii_signal(Decimal("1500")) == "buy"
    assert classify_fii_signal(Decimal("5000")) == "buy"  # 5000 not > 5000


def test_signal_neutral_band() -> None:
    assert classify_fii_signal(Decimal("0")) == "neutral"
    assert classify_fii_signal(Decimal("1000")) == "neutral"  # not > 1000
    assert classify_fii_signal(Decimal("-1000")) == "neutral"  # not < -1000


def test_signal_sell() -> None:
    assert classify_fii_signal(Decimal("-1500")) == "sell"
    assert classify_fii_signal(Decimal("-5000")) == "sell"  # not < -5000


def test_signal_strong_sell() -> None:
    assert classify_fii_signal(Decimal("-6000")) == "strong_sell"


def test_signal_none_is_neutral() -> None:
    assert classify_fii_signal(None) == "neutral"


# ---------------------------------------------------------------------------
# parse_flows_csv — ISO + DD-MMM-YYYY dates, blank dii -> None
# ---------------------------------------------------------------------------
def test_parse_flows_csv() -> None:
    text = (
        "flow_date,fii_net_cr,dii_net_cr\n"
        "2026-05-22,1234.56,-567.89\n"
        "21-May-2026,-2345.67,\n"
    )
    rows = parse_flows_csv(text)
    assert rows == [
        RawFlow(date(2026, 5, 22), Decimal("1234.56"), Decimal("-567.89")),
        RawFlow(date(2026, 5, 21), Decimal("-2345.67"), None),
    ]


# ---------------------------------------------------------------------------
# compute_rolling — 5-row rolling sums + signal, ascending by date
# ---------------------------------------------------------------------------
def _flow(d: int, fii: str, dii: str | None) -> RawFlow:
    return RawFlow(
        date(2026, 5, d),
        Decimal(fii),
        Decimal(dii) if dii is not None else None,
    )


def test_compute_rolling() -> None:
    raw = [
        _flow(18, "100", "10"),
        _flow(19, "200", "20"),
        _flow(20, "300", "30"),
        _flow(21, "400", "40"),
        _flow(22, "500", "50"),
        _flow(25, "600", "60"),
    ]
    rows = compute_rolling(raw)
    assert all(isinstance(r, FlowRow) for r in rows)
    # First 4 rows: not enough history for a 5-row window.
    for r in rows[:4]:
        assert r.fii_5d_sum is None
        assert r.dii_5d_sum is None
        assert r.fii_signal == "neutral"
    # 5th row: sum of rows 1..5.
    assert rows[4].fii_5d_sum == Decimal("1500")  # 100+200+300+400+500
    assert rows[4].dii_5d_sum == Decimal("150")
    assert rows[4].fii_signal == "buy"
    # 6th row: sum of rows 2..6.
    assert rows[5].fii_5d_sum == Decimal("2000")  # 200+300+400+500+600
    assert rows[5].dii_5d_sum == Decimal("200")
    assert rows[5].fii_signal == "buy"
    assert rows[5].source == "nsdl_fpi"


def test_compute_rolling_sorts_input() -> None:
    raw = [_flow(22, "500", "50"), _flow(18, "100", "10")]
    rows = compute_rolling(raw)
    assert [r.flow_date for r in rows] == [date(2026, 5, 18), date(2026, 5, 22)]


def test_compute_rolling_dii_none_blocks_sum() -> None:
    raw = [
        _flow(18, "100", "10"),
        _flow(19, "200", None),  # missing dii in the window
        _flow(20, "300", "30"),
        _flow(21, "400", "40"),
        _flow(22, "500", "50"),
    ]
    rows = compute_rolling(raw)
    assert rows[4].fii_5d_sum == Decimal("1500")
    assert rows[4].dii_5d_sum is None  # one None in window -> None
