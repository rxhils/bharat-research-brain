"""Tests for the Macro Agent (Chunk 4.1) — pure regime/trend + mocked fetches.

Sources are public, no-auth, and permitted (Frankfurter FX; Yahoo Finance, which
yfinance wraps — CLAUDE.md §2 rule 5). All HTTP is mocked with respx; the
trend/regime logic is pure and tested with synthetic readings.
"""
from __future__ import annotations

import re
from decimal import Decimal

import httpx
import respx

from backend.agents.macro import (
    BOND,
    CRUDE,
    NIFTY,
    USD_INR,
    MacroAgent,
    MacroReading,
    classify_trend,
    compute_regime,
    parse_frankfurter_timeseries,
    parse_yahoo_chart,
)


def _r(indicator: str, signal: str) -> MacroReading:
    return MacroReading(indicator, Decimal("1"), signal, Decimal("0.1"), "test")


# ---------------------------------------------------------------------------
# classify_trend
# ---------------------------------------------------------------------------
def test_classify_trend_rising() -> None:
    assert classify_trend(Decimal("85"), Decimal("84")) == "rising"


def test_classify_trend_falling() -> None:
    assert classify_trend(Decimal("82"), Decimal("84")) == "falling"


def test_classify_trend_stable_within_band() -> None:
    # 0.12% move is inside the default 0.5% stable band
    assert classify_trend(Decimal("84.1"), Decimal("84")) == "stable"


def test_classify_trend_unknown_on_missing() -> None:
    assert classify_trend(None, Decimal("84")) == "unknown"
    assert classify_trend(Decimal("84"), None) == "unknown"


# ---------------------------------------------------------------------------
# compute_regime
# ---------------------------------------------------------------------------
def test_regime_risk_on() -> None:
    readings = {
        NIFTY: _r(NIFTY, "rising"),
        CRUDE: _r(CRUDE, "falling"),
        USD_INR: _r(USD_INR, "stable"),
    }
    assert compute_regime(readings) == "risk-on"


def test_regime_risk_off_nifty_below() -> None:
    readings = {
        NIFTY: _r(NIFTY, "falling"),
        CRUDE: _r(CRUDE, "falling"),
        USD_INR: _r(USD_INR, "stable"),
    }
    assert compute_regime(readings) == "risk-off"


def test_regime_risk_off_crude_rising() -> None:
    readings = {
        NIFTY: _r(NIFTY, "rising"),
        CRUDE: _r(CRUDE, "rising"),
        USD_INR: _r(USD_INR, "stable"),
    }
    assert compute_regime(readings) == "risk-off"


def test_regime_risk_off_usd_rising() -> None:
    readings = {
        NIFTY: _r(NIFTY, "rising"),
        CRUDE: _r(CRUDE, "stable"),
        USD_INR: _r(USD_INR, "rising"),
    }
    assert compute_regime(readings) == "risk-off"


def test_regime_neutral_on_unknown() -> None:
    readings = {
        NIFTY: _r(NIFTY, "unknown"),  # missing data -> can't confirm risk-on
        CRUDE: _r(CRUDE, "stable"),
        USD_INR: _r(USD_INR, "stable"),
    }
    assert compute_regime(readings) == "neutral"


# ---------------------------------------------------------------------------
# parsers
# ---------------------------------------------------------------------------
def test_parse_frankfurter_timeseries() -> None:
    text = (
        '{"amount":1.0,"base":"USD","rates":'
        '{"2026-04-26":{"INR":83.0},"2026-05-20":{"INR":84.0},'
        '"2026-05-25":{"INR":85.0}}}'
    )
    series = parse_frankfurter_timeseries(text)
    assert series == [Decimal("83.0"), Decimal("84.0"), Decimal("85.0")]


def test_parse_yahoo_chart() -> None:
    text = (
        '{"chart":{"result":[{"meta":{"regularMarketPrice":82.5},'
        '"indicators":{"quote":[{"close":[80.0,null,81.0,82.5]}]}}],"error":null}}'
    )
    latest, closes = parse_yahoo_chart(text)
    assert latest == Decimal("82.5")
    assert closes == [Decimal("80.0"), Decimal("81.0"), Decimal("82.5")]


def test_parse_yahoo_chart_empty() -> None:
    latest, closes = parse_yahoo_chart('{"chart":{"result":[],"error":"x"}}')
    assert latest is None
    assert closes == []


# ---------------------------------------------------------------------------
# fetch methods (respx-mocked HTTP)
# ---------------------------------------------------------------------------
@respx.mock
async def test_fetch_usd_inr_rising() -> None:
    body = (
        '{"base":"USD","rates":{"2026-04-26":{"INR":83.0},'
        '"2026-05-25":{"INR":85.0}}}'
    )
    respx.get(re.compile(r"https://api\.frankfurter\.app/.*")).mock(
        return_value=httpx.Response(200, content=body.encode())
    )
    reading = await MacroAgent().fetch_usd_inr()
    assert reading.indicator == USD_INR
    assert reading.value == Decimal("85.0")
    assert reading.signal == "rising"


@respx.mock
async def test_fetch_bond_fallback_on_error() -> None:
    respx.get(re.compile(r"https://query1\.finance\.yahoo\.com/.*")).mock(
        return_value=httpx.Response(404, content=b"not found")
    )
    reading = await MacroAgent().fetch_bond_yield()
    assert reading.indicator == BOND
    assert reading.value == Decimal("6.5")  # hardcoded RBI repo fallback
    assert reading.signal == "unknown"
