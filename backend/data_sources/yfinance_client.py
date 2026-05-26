"""yfinance data source — corporate actions, fundamentals info, financials.

Permitted source per CLAUDE.md §2 rule 5. yfinance is a synchronous library
(it uses requests + pandas), so the blocking call is wrapped in
`asyncio.to_thread` per CLAUDE.md §8. yfinance is imported lazily inside the
sync worker so this module imports cleanly without the dependency installed
(unit tests inject a fake client).

yfinance covers splits + dividends only — not rights issues or face-value
changes. Split values are the yfinance factor (new shares per old share):
2.0 = a 2-for-1 split, 0.5 = a 1-for-2 reverse split.

`fetch_financials` (Chunk 4.8) adds the richer cash-flow / quarterly /
dividend-history view used by the Fundamentals Agent. Quarterly data is often
sparse for Indian tickers, so every field degrades to None / [] rather than
raising.
"""
from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import structlog

log = structlog.get_logger()

# yfinance row labels vary across versions; try each in order.
_FCF_LABELS = ("Free Cash Flow", "FreeCashFlow")
_NET_INCOME_LABELS = (
    "Net Income",
    "NetIncome",
    "Net Income Common Stockholders",
    "Net Income Continuous Operations",
)
_REVENUE_LABELS = ("Total Revenue", "TotalRevenue", "Operating Revenue", "Revenue")


@dataclass(frozen=True)
class RawSplit:
    ex_date: date
    ratio: Decimal  # yfinance factor: new shares per old share


@dataclass(frozen=True)
class RawDividend:
    ex_date: date
    amount: Decimal  # cash per share, INR


@dataclass(frozen=True)
class FinancialData:
    """Richer fundamentals beyond `.info` (Chunk 4.8). Every field may be missing.

    `quarterly_net_income` / `quarterly_revenue` are the last <=4 quarters in INR,
    most recent first. Interest coverage is ebitda / |interestExpense|.
    """

    free_cash_flow: int | None
    interest_coverage: Decimal | None
    current_ratio: Decimal | None
    dividend_consecutive_years: int | None
    dividend_payout_ratio: Decimal | None
    quarterly_net_income: list[int]
    quarterly_revenue: list[int]


def _num(value: Any) -> Decimal | None:
    """Coerce a yfinance numeric to Decimal; None for missing / NaN / junk."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _row_series(df: Any, labels: tuple[str, ...]) -> Any:
    """First matching row of a yfinance statement DataFrame as a Series, else None."""
    if df is None or getattr(df, "empty", True):
        return None
    for label in labels:
        if label in df.index:
            row = df.loc[label]
            # Duplicate index labels yield a DataFrame; take the first row.
            if getattr(row, "ndim", 1) == 2:
                row = row.iloc[0]
            return row
    return None


def _quarterly_list(df: Any, labels: tuple[str, ...]) -> list[int]:
    """Last <=4 quarters for the first matching row, most recent first."""
    series = _row_series(df, labels)
    if series is None:
        return []
    series = series.dropna().sort_index(ascending=False)
    out: list[int] = []
    for value in series.tolist()[:4]:
        coerced = _int(value)
        if coerced is not None:
            out.append(coerced)
    return out


def _annual_free_cash_flow(cashflow: Any) -> int | None:
    series = _row_series(cashflow, _FCF_LABELS)
    if series is None:
        return None
    series = series.dropna().sort_index(ascending=False)
    if series.empty:
        return None
    return _int(series.iloc[0])


def _consecutive_dividend_years(dividends: Any) -> int | None:
    """Years (ending at the latest) with >=1 dividend, counted while consecutive."""
    if dividends is None or getattr(dividends, "empty", True):
        return None
    years = sorted({ts.year for ts in dividends.index})
    if not years:
        return None
    count = 1
    for i in range(len(years) - 1, 0, -1):
        if years[i] - years[i - 1] == 1:
            count += 1
        else:
            break
    return count


def _interest_coverage(info: dict[str, Any]) -> Decimal | None:
    ebitda = _num(info.get("ebitda"))
    interest = _num(info.get("interestExpense"))
    if ebitda is None or interest is None or interest == 0:
        return None
    return ebitda / abs(interest)


def _parse_financials(
    cashflow: Any, quarterly: Any, dividends: Any, info: dict[str, Any]
) -> FinancialData:
    """Pure projection of yfinance financial structures into FinancialData."""
    return FinancialData(
        free_cash_flow=_annual_free_cash_flow(cashflow),
        interest_coverage=_interest_coverage(info),
        current_ratio=_num(info.get("currentRatio")),
        dividend_consecutive_years=_consecutive_dividend_years(dividends),
        dividend_payout_ratio=_num(info.get("payoutRatio")),
        quarterly_net_income=_quarterly_list(quarterly, _NET_INCOME_LABELS),
        quarterly_revenue=_quarterly_list(quarterly, _REVENUE_LABELS),
    )


class YFinanceClient:
    """Async wrapper over yfinance for per-ticker splits + dividends."""

    async def fetch_corporate_actions(
        self, yf_symbol: str, *, start: date, end: date
    ) -> tuple[list[RawSplit], list[RawDividend]]:
        return await asyncio.to_thread(self._fetch_sync, yf_symbol, start, end)

    async def fetch_info(self, yf_symbol: str) -> dict[str, Any]:
        """The yfinance `.info` dict for one ticker (fundamentals snapshot)."""
        return await asyncio.to_thread(self._fetch_info_sync, yf_symbol)

    async def fetch_financials(self, yf_symbol: str) -> FinancialData:
        """Cash-flow / quarterly / dividend-history view for one ticker (Chunk 4.8)."""
        return await asyncio.to_thread(self._fetch_financials_sync, yf_symbol)

    @staticmethod
    def _fetch_info_sync(yf_symbol: str) -> dict[str, Any]:
        import yfinance as yf  # lazy: keeps module importable without the dep

        info = yf.Ticker(yf_symbol).info
        return dict(info) if info else {}

    @staticmethod
    def _fetch_financials_sync(yf_symbol: str) -> FinancialData:
        import yfinance as yf  # lazy: keeps module importable without the dep

        ticker = yf.Ticker(yf_symbol)

        def _safe(attr: str) -> Any:
            # yfinance lazily fetches each statement; any one may raise on a
            # thin ticker. Degrade that statement to None, keep the rest.
            try:
                return getattr(ticker, attr)
            except Exception as exc:  # noqa: BLE001 - external feed, best-effort
                log.warning("yfinance.financials.partial", attr=attr, error=str(exc))
                return None

        try:
            info = dict(ticker.info) if ticker.info else {}
        except Exception as exc:  # noqa: BLE001 - external feed, best-effort
            log.warning("yfinance.financials.info_failed", error=str(exc))
            info = {}

        return _parse_financials(
            _safe("cashflow"),
            _safe("quarterly_financials"),
            _safe("dividends"),
            info,
        )

    @staticmethod
    def _fetch_sync(
        yf_symbol: str, start: date, end: date
    ) -> tuple[list[RawSplit], list[RawDividend]]:
        import yfinance as yf  # lazy: keeps module importable without the dep

        ticker = yf.Ticker(yf_symbol)
        splits: list[RawSplit] = []
        dividends: list[RawDividend] = []

        for ts, value in ticker.splits.items():
            d = ts.date()
            if start <= d <= end and value and value > 0:
                splits.append(RawSplit(d, Decimal(str(value))))

        for ts, value in ticker.dividends.items():
            d = ts.date()
            if start <= d <= end and value and value > 0:
                dividends.append(RawDividend(d, Decimal(str(value))))

        return splits, dividends
