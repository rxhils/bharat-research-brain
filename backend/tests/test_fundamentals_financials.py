"""Tests for the Chunk 4.8 fundamentals extension — offline, no network.

Covers:
- `compute_quarterly_direction` (pure, synthetic series),
- `_parse_financials` (pure, real pandas inputs),
- `YFinanceClient.fetch_financials` (patched `yfinance.Ticker`, no network),
- `FundamentalsAgent.fetch_isin` merging info + financials.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import patch

import pandas as pd

from backend.agents.fundamentals import (
    FundamentalsAgent,
    compute_quarterly_direction,
)
from backend.data_sources.yfinance_client import (
    FinancialData,
    YFinanceClient,
    _parse_financials,
)
from backend.tests.test_fundamentals import INFO


# ---------------------------------------------------------------------------
# compute_quarterly_direction — linear-trend classifier (most-recent-first)
# ---------------------------------------------------------------------------
def test_direction_improving() -> None:
    # most recent first; chronologically rising by ~10/qtr, > 5% of mean
    assert compute_quarterly_direction([140, 130, 120, 110]) == "improving"


def test_direction_declining() -> None:
    assert compute_quarterly_direction([110, 120, 130, 140]) == "declining"


def test_direction_stable() -> None:
    # tiny slope relative to mean -> stable
    assert compute_quarterly_direction([101, 100, 101, 100]) == "stable"


def test_direction_three_points_ok() -> None:
    assert compute_quarterly_direction([130, 120, 110]) == "improving"


def test_direction_unknown_few_points() -> None:
    assert compute_quarterly_direction([100, 110]) == "unknown"
    assert compute_quarterly_direction([]) == "unknown"


# ---------------------------------------------------------------------------
# Synthetic yfinance financial structures (pandas, as the real client sees them)
# ---------------------------------------------------------------------------
def _cashflow() -> pd.DataFrame:
    return pd.DataFrame(
        {
            pd.Timestamp("2024-03-31"): [1_500_000_000],
            pd.Timestamp("2023-03-31"): [1_200_000_000],
        },
        index=["Free Cash Flow"],
    )


def _quarterly() -> pd.DataFrame:
    cols = [
        pd.Timestamp("2024-12-31"),
        pd.Timestamp("2024-09-30"),
        pd.Timestamp("2024-06-30"),
        pd.Timestamp("2024-03-31"),
    ]
    return pd.DataFrame(
        [
            [1_400_000_000, 1_100_000_000, 1_350_000_000, 1_200_000_000],  # Net Income
            [5_400_000_000, 5_100_000_000, 5_350_000_000, 5_200_000_000],  # Total Rev
        ],
        index=["Net Income", "Total Revenue"],
        columns=cols,
    )


def _dividends() -> pd.Series:
    return pd.Series(
        [5.0, 6.0, 7.0, 8.0],
        index=pd.to_datetime(
            ["2021-06-01", "2022-06-01", "2023-06-01", "2024-06-01"]
        ),
    )


def _info() -> dict[str, Any]:
    return {
        "currentRatio": 1.3,
        "payoutRatio": 0.35,
        "ebitda": 1_000_000_000,
        "interestExpense": 200_000_000,
    }


# ---------------------------------------------------------------------------
# _parse_financials — extraction, ordering, None handling
# ---------------------------------------------------------------------------
def test_parse_financials_full() -> None:
    fin = _parse_financials(_cashflow(), _quarterly(), _dividends(), _info())
    assert fin.free_cash_flow == 1_500_000_000  # most recent annual
    assert fin.quarterly_net_income == [
        1_400_000_000,
        1_100_000_000,
        1_350_000_000,
        1_200_000_000,
    ]
    assert fin.quarterly_revenue == [
        5_400_000_000,
        5_100_000_000,
        5_350_000_000,
        5_200_000_000,
    ]
    assert fin.dividend_consecutive_years == 4
    assert fin.current_ratio == Decimal("1.3")
    assert fin.dividend_payout_ratio == Decimal("0.35")
    assert fin.interest_coverage == Decimal("5")  # 1e9 / 2e8


def test_parse_financials_empty() -> None:
    fin = _parse_financials(None, None, None, {})
    assert fin.free_cash_flow is None
    assert fin.quarterly_net_income == []
    assert fin.quarterly_revenue == []
    assert fin.dividend_consecutive_years is None
    assert fin.current_ratio is None
    assert fin.dividend_payout_ratio is None
    assert fin.interest_coverage is None


def test_parse_financials_no_interest_expense_is_none() -> None:
    fin = _parse_financials(None, None, None, {"ebitda": 1_000_000_000})
    assert fin.interest_coverage is None


def test_parse_financials_zero_interest_expense_is_none() -> None:
    fin = _parse_financials(
        None, None, None, {"ebitda": 1_000_000_000, "interestExpense": 0}
    )
    assert fin.interest_coverage is None


def test_parse_financials_non_consecutive_dividend_years() -> None:
    # gap year (2022 missing) -> only 2023,2024 are consecutive ending latest
    divs = pd.Series(
        [5.0, 7.0, 8.0],
        index=pd.to_datetime(["2021-06-01", "2023-06-01", "2024-06-01"]),
    )
    fin = _parse_financials(None, None, divs, {})
    assert fin.dividend_consecutive_years == 2


# ---------------------------------------------------------------------------
# YFinanceClient.fetch_financials — patch yfinance.Ticker, no network
# ---------------------------------------------------------------------------
async def test_client_fetch_financials_patches_ticker() -> None:
    with patch("yfinance.Ticker") as mock_ticker:
        t = mock_ticker.return_value
        t.cashflow = _cashflow()
        t.quarterly_financials = _quarterly()
        t.dividends = _dividends()
        t.info = _info()
        fin = await YFinanceClient().fetch_financials("RELIANCE.NS")
    assert fin.free_cash_flow == 1_500_000_000
    assert fin.interest_coverage == Decimal("5")
    assert fin.dividend_consecutive_years == 4
    mock_ticker.assert_called_once_with("RELIANCE.NS")


# ---------------------------------------------------------------------------
# FundamentalsAgent.fetch_isin — merges fetch_info + fetch_financials
# ---------------------------------------------------------------------------
class FakeFullClient:
    def __init__(self, info: dict[str, Any], fin: FinancialData) -> None:
        self._info = info
        self._fin = fin

    async def fetch_info(self, yf_symbol: str) -> dict[str, Any]:
        return self._info

    async def fetch_financials(self, yf_symbol: str) -> FinancialData:
        return self._fin


async def test_fetch_isin_merges_financials() -> None:
    fin = FinancialData(
        free_cash_flow=1_500_000_000,
        interest_coverage=Decimal("5"),
        current_ratio=Decimal("1.3"),
        dividend_consecutive_years=6,
        dividend_payout_ratio=Decimal("0.35"),
        quarterly_net_income=[140, 130, 120, 110],  # improving (chrono rising)
        quarterly_revenue=[540, 530, 520, 510],  # slope small vs mean -> stable
    )
    agent = FundamentalsAgent(client=FakeFullClient(INFO, fin))
    row = await agent.fetch_isin("INE002A01018", "RELIANCE")
    assert row is not None
    # info still merged
    assert row.pe_ratio == Decimal("24.5")
    assert row.market_cap == 18_500_000_000_000
    # financials merged
    assert row.free_cash_flow == 1_500_000_000
    assert row.fcf_positive is True
    assert row.interest_coverage == Decimal("5")
    assert row.current_ratio == Decimal("1.3")
    assert row.dividend_consecutive_years == 6
    assert row.dividend_payout_ratio == Decimal("0.35")
    assert row.quarterly_profit_trend == [140, 130, 120, 110]
    assert row.quarterly_revenue_trend == [540, 530, 520, 510]
    assert row.q_profit_direction == "improving"
    assert row.q_revenue_direction == "stable"


async def test_fetch_isin_fcf_negative_sets_flag_false() -> None:
    fin = FinancialData(
        free_cash_flow=-50_000_000,
        interest_coverage=None,
        current_ratio=None,
        dividend_consecutive_years=None,
        dividend_payout_ratio=None,
        quarterly_net_income=[],
        quarterly_revenue=[],
    )
    agent = FundamentalsAgent(client=FakeFullClient(INFO, fin))
    row = await agent.fetch_isin("INE002A01018", "RELIANCE")
    assert row is not None
    assert row.fcf_positive is False
    assert row.q_profit_direction == "unknown"  # empty series
