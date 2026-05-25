"""yfinance data source — corporate actions (splits + dividends).

Permitted source per CLAUDE.md §2 rule 5. yfinance is a synchronous library
(it uses requests + pandas), so the blocking call is wrapped in
`asyncio.to_thread` per CLAUDE.md §8. yfinance is imported lazily inside the
sync worker so this module imports cleanly without the dependency installed
(unit tests inject a fake client).

yfinance covers splits + dividends only — not rights issues or face-value
changes. Split values are the yfinance factor (new shares per old share):
2.0 = a 2-for-1 split, 0.5 = a 1-for-2 reverse split.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import structlog

log = structlog.get_logger()


@dataclass(frozen=True)
class RawSplit:
    ex_date: date
    ratio: Decimal  # yfinance factor: new shares per old share


@dataclass(frozen=True)
class RawDividend:
    ex_date: date
    amount: Decimal  # cash per share, INR


class YFinanceClient:
    """Async wrapper over yfinance for per-ticker splits + dividends."""

    async def fetch_corporate_actions(
        self, yf_symbol: str, *, start: date, end: date
    ) -> tuple[list[RawSplit], list[RawDividend]]:
        return await asyncio.to_thread(self._fetch_sync, yf_symbol, start, end)

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
