"""Tests for the Fundamentals Agent (Chunk 3.4) — pure mapping + fetch, offline.

yfinance is never hit. Pure functions (`info_to_row`, `mcap_to_category`) are
tested directly; `fetch_isin` is tested with a fake client; and one test patches
`yfinance.Ticker` to exercise the real client path with no network.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import patch

from backend.agents.fundamentals import (
    FundamentalRow,
    FundamentalsAgent,
    info_to_row,
    mcap_to_category,
)
from backend.data_sources.yfinance_client import FinancialData, YFinanceClient

_EMPTY_FINANCIALS = FinancialData(None, None, None, None, None, [], [])

# A representative yfinance .info dict (Reliance-like; values illustrative).
INFO: dict[str, Any] = {
    "trailingPE": 24.5,
    "priceToBook": 2.1,
    "returnOnEquity": 0.094,
    "returnOnAssets": 0.045,
    "debtToEquity": 38.2,
    "revenueGrowth": 0.12,
    "earningsGrowth": 0.08,
    "profitMargins": 0.078,
    "marketCap": 18_500_000_000_000,  # ~18.5 lakh cr in INR
    "dividendYield": 0.0035,
    "fiftyTwoWeekHigh": 1600.0,
    "fiftyTwoWeekLow": 1100.0,
    "averageVolume": 9_500_000,
}


class FakeYFClient:
    def __init__(self, info: dict[str, Any]) -> None:
        self._info = info

    async def fetch_info(self, yf_symbol: str) -> dict[str, Any]:
        return self._info

    async def fetch_financials(self, yf_symbol: str) -> FinancialData:
        return _EMPTY_FINANCIALS


# ---------------------------------------------------------------------------
# mcap_to_category — thresholds (market_cap in INR; 1 Cr = 1e7 INR)
# ---------------------------------------------------------------------------
def test_mcap_large() -> None:
    assert mcap_to_category(200_000_000_000) == "large"  # 20000 Cr exactly


def test_mcap_mid() -> None:
    assert mcap_to_category(199_999_999_999) == "mid"  # just under 20000 Cr
    assert mcap_to_category(50_000_000_000) == "mid"  # 5000 Cr exactly


def test_mcap_small() -> None:
    assert mcap_to_category(49_999_999_999) == "small"  # just under 5000 Cr


def test_mcap_none() -> None:
    assert mcap_to_category(None) is None


# ---------------------------------------------------------------------------
# info_to_row — field extraction, Decimal/int coercion, None handling
# ---------------------------------------------------------------------------
def test_info_to_row_maps_fields() -> None:
    row = info_to_row("INE002A01018", INFO)
    assert isinstance(row, FundamentalRow)
    assert row.isin == "INE002A01018"
    assert row.pe_ratio == Decimal("24.5")
    assert row.pb_ratio == Decimal("2.1")
    assert row.roe == Decimal("0.094")
    assert row.roce == Decimal("0.045")
    assert row.debt_to_equity == Decimal("38.2")
    assert row.revenue_growth == Decimal("0.12")
    assert row.earnings_growth == Decimal("0.08")
    assert row.profit_margin == Decimal("0.078")
    assert row.market_cap == 18_500_000_000_000
    assert row.dividend_yield == Decimal("0.0035")
    assert row.fifty_two_week_high == Decimal("1600.0")
    assert row.fifty_two_week_low == Decimal("1100.0")
    assert row.avg_volume_30d == 9_500_000
    assert row.promoter_holding is None  # yfinance gap — always NULL
    assert row.source == "yfinance"


def test_info_to_row_missing_keys_are_none() -> None:
    row = info_to_row("INEXXXXXXXXX", {})
    assert row.pe_ratio is None
    assert row.market_cap is None
    assert row.roe is None
    assert row.avg_volume_30d is None
    assert row.promoter_holding is None
    assert row.source == "yfinance"


def test_info_to_row_nan_is_none() -> None:
    row = info_to_row("INEXXXXXXXXX", {"trailingPE": float("nan"), "marketCap": 1234})
    assert row.pe_ratio is None
    assert row.market_cap == 1234


# ---------------------------------------------------------------------------
# fetch_isin — fake client (no network)
# ---------------------------------------------------------------------------
async def test_fetch_isin_returns_row() -> None:
    agent = FundamentalsAgent(client=FakeYFClient(INFO))
    row = await agent.fetch_isin("INE002A01018", "RELIANCE")
    assert row is not None
    assert row.pe_ratio == Decimal("24.5")
    assert row.market_cap == 18_500_000_000_000


async def test_fetch_isin_empty_returns_none() -> None:
    agent = FundamentalsAgent(client=FakeYFClient({}))
    assert await agent.fetch_isin("INEXXXXXXXXX", "GHOST") is None


# ---------------------------------------------------------------------------
# YFinanceClient.fetch_info — patch yfinance.Ticker, no network (spec literal)
# ---------------------------------------------------------------------------
async def test_client_fetch_info_patches_ticker() -> None:
    with patch("yfinance.Ticker") as mock_ticker:
        mock_ticker.return_value.info = INFO
        info = await YFinanceClient().fetch_info("RELIANCE.NS")
    assert info["trailingPE"] == 24.5
    mock_ticker.assert_called_once_with("RELIANCE.NS")
