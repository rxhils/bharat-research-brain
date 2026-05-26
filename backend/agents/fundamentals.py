"""Fundamentals Agent (Chunk 3.4) — weekly yfinance fundamentals snapshot.

Fetches the yfinance `.info` dict for every active NSE stock ({SYMBOL}.NS),
maps the slow-moving fundamental fields into `fundamental_signals` (one row per
(isin, fetched_date), upserted), and then classifies each stock into a market-
cap bucket on `stocks.mcap_category`.

yfinance is a permitted source (CLAUDE.md §2 rule 5) and is synchronous, so each
call is wrapped in `asyncio.to_thread` by the client; the agent fans out with an
`asyncio.Semaphore(10)` to stay polite. Values are stored raw as yfinance
returns them (ratios as fractions, e.g. ROE 0.094 = 9.4%); market_cap is INR.
`promoter_holding` is not exposed by yfinance — always NULL (documented gap).
"""
from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass, field, replace
from datetime import date
from decimal import Decimal
from typing import Any, Protocol

import structlog

from backend.data_sources.yfinance_client import FinancialData, YFinanceClient
from backend.db.repositories._helpers import today_ist

log = structlog.get_logger()

SOURCE = "yfinance"

# Market-cap thresholds in INR (1 Cr = 1e7 INR). Stored labels match the
# stocks.mcap_category CHECK ('large'/'mid'/'small'/'micro') and the vault
# writer, which renders the tag as f"{mcap_category}-cap".
_LARGE_CAP_INR = 200_000_000_000  # >= 20000 Cr
_MID_CAP_INR = 50_000_000_000  # >= 5000 Cr


@dataclass(frozen=True)
class FundamentalRow:
    isin: str
    pe_ratio: Decimal | None
    pb_ratio: Decimal | None
    roe: Decimal | None
    roce: Decimal | None
    debt_to_equity: Decimal | None
    revenue_growth: Decimal | None
    earnings_growth: Decimal | None
    profit_margin: Decimal | None
    market_cap: int | None
    dividend_yield: Decimal | None
    promoter_holding: Decimal | None
    fifty_two_week_high: Decimal | None
    fifty_two_week_low: Decimal | None
    avg_volume_30d: int | None
    free_cash_flow: int | None = None
    fcf_positive: bool | None = None
    interest_coverage: Decimal | None = None
    current_ratio: Decimal | None = None
    dividend_consecutive_years: int | None = None
    dividend_payout_ratio: Decimal | None = None
    quarterly_profit_trend: list[int] | None = None
    quarterly_revenue_trend: list[int] | None = None
    q_profit_direction: str | None = None
    q_revenue_direction: str | None = None
    source: str = SOURCE


class _InfoClient(Protocol):
    async def fetch_info(self, yf_symbol: str) -> dict[str, Any]: ...
    async def fetch_financials(self, yf_symbol: str) -> FinancialData: ...


def _dec(value: Any) -> Decimal | None:
    """Coerce a yfinance numeric to Decimal; None for missing / NaN."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return Decimal(str(value))


def _bigint(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return int(value)


def compute_quarterly_direction(values: list[int]) -> str:
    """Classify the trend of the last <=4 quarters (input is most-recent-first).

    Least-squares slope over chronological order, compared to 5% of the mean
    magnitude: improving (slope above), declining (below), else stable. Fewer
    than 3 data points -> 'unknown' (yfinance quarterly data is often sparse for
    Indian tickers).
    """
    if len(values) < 3:
        return "unknown"
    chrono = list(reversed(values))  # oldest -> newest
    n = len(chrono)
    xs = range(n)
    mean_x = sum(xs) / n
    mean_y = sum(chrono) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, chrono, strict=True))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    if var_x == 0:
        return "stable"
    slope = cov / var_x
    threshold = 0.05 * abs(mean_y)
    if slope > threshold:
        return "improving"
    if slope < -threshold:
        return "declining"
    return "stable"


def mcap_to_category(market_cap_inr: int | None) -> str | None:
    """Bucket a market cap (INR) into large / mid / small. None passes through."""
    if market_cap_inr is None:
        return None
    if market_cap_inr >= _LARGE_CAP_INR:
        return "large"
    if market_cap_inr >= _MID_CAP_INR:
        return "mid"
    return "small"


def info_to_row(isin: str, info: dict[str, Any]) -> FundamentalRow:
    """Map a yfinance `.info` dict to a FundamentalRow (raw yfinance units)."""
    return FundamentalRow(
        isin=isin,
        pe_ratio=_dec(info.get("trailingPE")),
        pb_ratio=_dec(info.get("priceToBook")),
        roe=_dec(info.get("returnOnEquity")),
        roce=_dec(info.get("returnOnAssets")),  # ROA proxy for ROCE
        debt_to_equity=_dec(info.get("debtToEquity")),
        revenue_growth=_dec(info.get("revenueGrowth")),
        earnings_growth=_dec(info.get("earningsGrowth")),
        profit_margin=_dec(info.get("profitMargins")),
        market_cap=_bigint(info.get("marketCap")),
        dividend_yield=_dec(info.get("dividendYield")),
        promoter_holding=None,  # yfinance gap — never populated
        fifty_two_week_high=_dec(info.get("fiftyTwoWeekHigh")),
        fifty_two_week_low=_dec(info.get("fiftyTwoWeekLow")),
        avg_volume_30d=_bigint(info.get("averageVolume")),
        source=SOURCE,
    )


def _merge_row(isin: str, info: dict[str, Any], fin: FinancialData) -> FundamentalRow:
    """Combine the `.info` snapshot with the financials view into one row."""
    base = info_to_row(isin, info)
    fcf = fin.free_cash_flow
    return replace(
        base,
        free_cash_flow=fcf,
        fcf_positive=(fcf > 0) if fcf is not None else None,
        interest_coverage=fin.interest_coverage,
        current_ratio=fin.current_ratio,
        dividend_consecutive_years=fin.dividend_consecutive_years,
        dividend_payout_ratio=fin.dividend_payout_ratio,
        quarterly_profit_trend=fin.quarterly_net_income or None,
        quarterly_revenue_trend=fin.quarterly_revenue or None,
        q_profit_direction=compute_quarterly_direction(fin.quarterly_net_income),
        q_revenue_direction=compute_quarterly_direction(fin.quarterly_revenue),
    )


@dataclass
class FundamentalsResult:
    stocks_attempted: int = 0
    stocks_succeeded: int = 0
    stocks_failed: int = 0
    rows_ready: int = 0
    rows_upserted: int = 0
    categories_updated: int = 0
    failed_symbols: list[str] = field(default_factory=list)
    samples: list[FundamentalRow] = field(default_factory=list)


class FundamentalsAgent:
    name = "fundamentals"

    def __init__(self, *, client: _InfoClient | None = None) -> None:
        self.client = client or YFinanceClient()

    async def fetch_isin(self, isin: str, nse_symbol: str) -> FundamentalRow | None:
        """Fetch + map one stock's fundamentals. None if yfinance has nothing."""
        yf_symbol = f"{nse_symbol}.NS"
        info = await self.client.fetch_info(yf_symbol)
        if not info:
            return None
        fin = await self.client.fetch_financials(yf_symbol)
        return _merge_row(isin, info, fin)

    async def run_all(
        self,
        *,
        batch_size: int = 50,
        isin: str | None = None,
        dry_run: bool = False,
        max_concurrency: int = 10,
    ) -> FundamentalsResult:
        from backend.db.repositories import fundamentals as fund_repo
        from backend.db.session import SessionLocal

        async with SessionLocal() as session:
            symbols = await fund_repo.fetch_active_symbols(session, isin=isin)

        sem = asyncio.Semaphore(max_concurrency)
        fetched = await asyncio.gather(
            *(self._fetch_one(i, sym, sem) for i, sym in symbols)
        )

        result = FundamentalsResult(stocks_attempted=len(symbols))
        rows: list[FundamentalRow] = []
        for ok, sym, row in fetched:
            if ok and row is not None:
                result.stocks_succeeded += 1
                rows.append(row)
            else:
                result.stocks_failed += 1
                result.failed_symbols.append(sym)
        result.rows_ready = len(rows)

        if dry_run:
            result.samples = rows[:10]
            log.info(
                "fundamentals.run.dry_run",
                attempted=result.stocks_attempted,
                ready=result.rows_ready,
            )
            return result

        fetched_date = today_ist()
        if rows:
            payload = [_row_to_dict(r, fetched_date) for r in rows]
            async with SessionLocal() as session:
                result.rows_upserted = await fund_repo.bulk_upsert(session, payload)
                await session.commit()
        result.categories_updated = await self.update_mcap_categories()

        log.info(
            "fundamentals.run.done",
            attempted=result.stocks_attempted,
            succeeded=result.stocks_succeeded,
            failed=result.stocks_failed,
            upserted=result.rows_upserted,
            categories_updated=result.categories_updated,
        )
        return result

    async def update_mcap_categories(self) -> int:
        """Classify each stock by its latest fundamental_signals market_cap."""
        from backend.db.repositories import fundamentals as fund_repo
        from backend.db.session import SessionLocal

        async with SessionLocal() as session:
            latest = await fund_repo.latest_market_caps(session)
            pairs = [
                (isin, cat)
                for isin, mc in latest
                if (cat := mcap_to_category(mc)) is not None
            ]
            updated = await fund_repo.set_mcap_categories(session, pairs)
            await session.commit()
        return updated

    async def _fetch_one(
        self, isin: str, nse_symbol: str, sem: asyncio.Semaphore
    ) -> tuple[bool, str, FundamentalRow | None]:
        async with sem:
            try:
                row = await self.fetch_isin(isin, nse_symbol)
            except Exception as exc:  # yfinance raises many types; record, continue
                log.warning(
                    "fundamentals.fetch_failed",
                    isin=isin,
                    symbol=f"{nse_symbol}.NS",
                    error=str(exc),
                )
                return (False, nse_symbol, None)
        return (row is not None, nse_symbol, row)


def _row_to_dict(row: FundamentalRow, fetched_date: date) -> dict[str, Any]:
    return {
        "isin": row.isin,
        "fetched_date": fetched_date,
        "pe_ratio": row.pe_ratio,
        "pb_ratio": row.pb_ratio,
        "roe": row.roe,
        "roce": row.roce,
        "debt_to_equity": row.debt_to_equity,
        "revenue_growth": row.revenue_growth,
        "earnings_growth": row.earnings_growth,
        "profit_margin": row.profit_margin,
        "market_cap": row.market_cap,
        "dividend_yield": row.dividend_yield,
        "promoter_holding": row.promoter_holding,
        "fifty_two_week_high": row.fifty_two_week_high,
        "fifty_two_week_low": row.fifty_two_week_low,
        "avg_volume_30d": row.avg_volume_30d,
        "free_cash_flow": row.free_cash_flow,
        "fcf_positive": row.fcf_positive,
        "interest_coverage": row.interest_coverage,
        "current_ratio": row.current_ratio,
        "dividend_consecutive_years": row.dividend_consecutive_years,
        "dividend_payout_ratio": row.dividend_payout_ratio,
        "quarterly_profit_trend": row.quarterly_profit_trend,
        "quarterly_revenue_trend": row.quarterly_revenue_trend,
        "q_profit_direction": row.q_profit_direction,
        "q_revenue_direction": row.q_revenue_direction,
        "source": row.source,
    }
