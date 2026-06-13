#!/usr/bin/env python
"""Backfill historical quarterly fundamentals (Chunk 5.2b Task 1).

For each active stock, pull quarterly income / balance-sheet / cash-flow history
from yfinance and write one row per quarter to `fundamental_signals_historical`
(NOT the live `fundamental_signals` table). Each row's `publication_date` is
quarter_end + 45 days — the realistic Indian reporting lag — so the backtest can
enforce no-lookahead via `trade_date >= publication_date`.

Factors (Decimal, raw units like the live fundamentals):
  pe_ratio           = adj_close(as-of publication_date) / TTM EPS
  roe                = TTM net income / stockholders' equity (fraction)
  debt_to_equity     = total debt / stockholders' equity (ratio)
  fcf                = operating cash flow + capex (quarter, INR; capex is negative)
  revenue_growth_yoy = revenue[q] / revenue[q-4] - 1 (fraction)

HONEST LIMITS (verification prints actual coverage):
  * yfinance typically returns ~4-5 quarters for NSE tickers, not a full 8.
  * Survivorship bias: the universe is today's active stocks (delisted_on IS
    NULL); names delisted in-window are absent. Documented, not hidden.
  * A factor is written NULL when its inputs are missing — never fabricated.

Resilient: a thin/failing ticker is logged and skipped, never crashes the run.
ON CONFLICT (isin, quarter_end_date) DO NOTHING — never overwrites real data.

Usage:
    python -m scripts.backfill_fundamentals_historical [--limit N] [--quarters 8]
"""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

import structlog
from sqlalchemy import select, text

from backend.db.models import Stock
from backend.db.session import SessionLocal

log = structlog.get_logger()

_PUB_LAG_DAYS = 45
_BATCH = 50
_BATCH_DELAY_S = 2.0

# Tolerant line-item label candidates (yfinance labels vary by version/ticker).
_REVENUE = ("Total Revenue", "Operating Revenue", "TotalRevenue")
_NET_INCOME = ("Net Income", "Net Income Common Stockholders", "NetIncome")
_EQUITY = (
    "Stockholders Equity",
    "Total Stockholder Equity",
    "Common Stock Equity",
    "Total Equity Gross Minority Interest",
)
_TOTAL_DEBT = ("Total Debt",)
_OP_CF = (
    "Operating Cash Flow",
    "Total Cash From Operating Activities",
    "Cash Flow From Continuing Operating Activities",
)
_CAPEX = ("Capital Expenditure", "Capital Expenditures", "Purchase Of PPE")
_FCF = ("Free Cash Flow",)

_INSERT_SQL = text(
    """
    INSERT INTO fundamental_signals_historical
        (isin, quarter_end_date, publication_date, pe_ratio, roe,
         debt_to_equity, fcf, revenue_growth_yoy, source)
    VALUES
        (:isin, :quarter_end_date, :publication_date, :pe_ratio, :roe,
         :debt_to_equity, :fcf, :revenue_growth_yoy, :source)
    ON CONFLICT (isin, quarter_end_date) DO NOTHING
    """
)
_SQL_PRICES = text(
    "SELECT trade_date, adj_close FROM prices_eod_adjusted "
    "WHERE isin = :isin AND adj_close IS NOT NULL ORDER BY trade_date"
)
_SQL_COUNT = text("SELECT count(*) FROM fundamental_signals_historical")


@dataclass(frozen=True)
class QuarterFundamentals:
    quarter_end_date: date
    publication_date: date
    pe_ratio: Decimal | None
    roe: Decimal | None
    debt_to_equity: Decimal | None
    fcf: Decimal | None
    revenue_growth_yoy: Decimal | None


# ---------------------------------------------------------------------------
# yfinance (threaded — no event-loop blocking)
# ---------------------------------------------------------------------------
def _fetch_statements_sync(yf_symbol: str) -> dict[str, Any]:
    """Quarterly income/balance/cashflow DataFrames + shares (best effort)."""
    import yfinance as yf

    ticker = yf.Ticker(yf_symbol)

    def _safe(attr: str) -> Any:
        try:
            return getattr(ticker, attr)
        except Exception as exc:  # noqa: BLE001 - external feed, best-effort
            log.warning("yf.stmt.partial", symbol=yf_symbol, attr=attr, error=str(exc))
            return None

    shares: float | None = None
    try:
        info = ticker.info or {}
        sh = info.get("sharesOutstanding")
        shares = float(sh) if sh else None
    except Exception as exc:  # noqa: BLE001
        log.warning("yf.stmt.info_failed", symbol=yf_symbol, error=str(exc))

    return {
        "income": _safe("quarterly_income_stmt"),
        "balance": _safe("quarterly_balance_sheet"),
        "cashflow": _safe("quarterly_cashflow"),
        "shares": shares,
    }


def _row_value(df: Any, labels: tuple[str, ...], col: Any) -> Decimal | None:
    """Value at (any matching label, column) in a yfinance statement DataFrame."""
    if df is None or getattr(df, "empty", True):
        return None
    idx = {str(i).strip().lower(): i for i in df.index}
    for label in labels:
        key = label.strip().lower()
        real = idx.get(key) or next(
            (orig for low, orig in idx.items() if key in low), None
        )
        if real is None:
            continue
        try:
            val = df.loc[real, col]
        except Exception:  # noqa: BLE001
            continue
        if val is None:
            continue
        try:
            f = float(val)
        except (ValueError, TypeError):
            continue
        if f != f or f in (float("inf"), float("-inf")):  # NaN / inf -> treat as missing
            continue
        try:
            return Decimal(str(f))
        except (InvalidOperation, ValueError, TypeError):
            continue
    return None


def compute_quarters(
    statements: dict[str, Any],
    price_series: dict[date, Decimal],
    *,
    max_quarters: int,
) -> list[QuarterFundamentals]:
    """Per-quarter fundamentals from yfinance statements (pure given inputs).

    TTM net income = quarter + prior 3 quarters (when all present). PE uses the
    adj_close on-or-before the publication date from `price_series`.
    """
    income = statements.get("income")
    balance = statements.get("balance")
    cashflow = statements.get("cashflow")
    shares = statements.get("shares")

    if income is None or getattr(income, "empty", True):
        return []
    qcols = sorted(income.columns, reverse=True)[: max_quarters + 4]

    rev_by = {c: _row_value(income, _REVENUE, c) for c in qcols}
    ni_by = {c: _row_value(income, _NET_INCOME, c) for c in qcols}

    out: list[QuarterFundamentals] = []
    for i, c in enumerate(qcols[:max_quarters]):
        q_end = c.date() if hasattr(c, "date") else c
        pub = q_end + timedelta(days=_PUB_LAG_DAYS)

        window = [ni_by.get(qcols[j]) for j in range(i, min(i + 4, len(qcols)))]
        ttm_ni = (
            sum((v for v in window if v is not None), Decimal(0))
            if len(window) == 4 and all(v is not None for v in window)
            else None
        )

        equity = _row_value(balance, _EQUITY, c)
        roe = (
            ttm_ni / equity
            if (ttm_ni is not None and equity not in (None, Decimal(0)))
            else None
        )
        total_debt = _row_value(balance, _TOTAL_DEBT, c)
        de = (
            total_debt / equity
            if (total_debt is not None and equity not in (None, Decimal(0)))
            else None
        )

        fcf = _row_value(cashflow, _FCF, c)
        if fcf is None:
            op_cf = _row_value(cashflow, _OP_CF, c)
            capex = _row_value(cashflow, _CAPEX, c)
            if op_cf is not None and capex is not None:
                fcf = op_cf + capex  # capex is negative in yfinance

        rev = rev_by.get(c)
        rev_prior = rev_by.get(qcols[i + 4]) if i + 4 < len(qcols) else None
        rev_growth = (
            rev / rev_prior - 1
            if (rev is not None and rev_prior not in (None, Decimal(0)))
            else None
        )

        pe: Decimal | None = None
        price = _price_on_or_before(price_series, pub)
        if price is not None and ttm_ni is not None and shares and ttm_ni > 0:
            eps_ttm = ttm_ni / Decimal(str(shares))
            if eps_ttm > 0:
                pe = price / eps_ttm

        out.append(
            QuarterFundamentals(
                quarter_end_date=q_end,
                publication_date=pub,
                pe_ratio=_q(pe, 4),
                roe=_q(roe, 6),
                debt_to_equity=_q(de, 6),
                fcf=_q(fcf, 4),
                revenue_growth_yoy=_q(rev_growth, 6),
            )
        )
    return out


def _q(v: Decimal | None, places: int) -> Decimal | None:
    if v is None:
        return None
    try:
        return v.quantize(Decimal(10) ** -places)
    except (InvalidOperation, ValueError):
        return None


def _price_on_or_before(price_series: dict[date, Decimal], d: date) -> Decimal | None:
    candidates = [td for td in price_series if td <= d]
    return price_series[max(candidates)] if candidates else None


# ---------------------------------------------------------------------------
# DB
# ---------------------------------------------------------------------------
async def _load_universe(session: Any, limit: int | None) -> list[tuple[str, str]]:
    stmt = select(Stock.isin, Stock.nse_symbol).where(
        Stock.delisted_on.is_(None), Stock.nse_symbol.is_not(None)
    )
    rows = [(i, s) for i, s in (await session.execute(stmt)).all()]
    return rows[:limit] if limit else rows


async def _price_series(session: Any, isin: str) -> dict[date, Decimal]:
    rows = (await session.execute(_SQL_PRICES, {"isin": isin})).all()
    return {td: ac for td, ac in rows}


async def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Backfill historical fundamentals.")
    parser.add_argument("--limit", type=int, default=None, help="Max stocks (debug).")
    parser.add_argument("--quarters", type=int, default=8, help="Quarters back.")
    args = parser.parse_args(argv)

    async with SessionLocal() as session:
        universe = await _load_universe(session, args.limit)
    log.info("fund_hist.start", stocks=len(universe), quarters=args.quarters)

    attempted = 0
    failed = 0
    for start in range(0, len(universe), _BATCH):
        batch = universe[start : start + _BATCH]
        payload: list[dict[str, Any]] = []
        async with SessionLocal() as session:
            for isin, symbol in batch:
                yf_symbol = f"{symbol}.NS"
                try:
                    statements = await asyncio.to_thread(
                        _fetch_statements_sync, yf_symbol
                    )
                    prices = await _price_series(session, isin)
                    quarters = compute_quarters(
                        statements, prices, max_quarters=args.quarters
                    )
                except Exception as exc:  # noqa: BLE001 - never crash the run
                    failed += 1
                    log.warning("fund_hist.stock_failed", isin=isin, error=str(exc))
                    continue
                for q in quarters:
                    payload.append(
                        {
                            "isin": isin,
                            "quarter_end_date": q.quarter_end_date,
                            "publication_date": q.publication_date,
                            "pe_ratio": q.pe_ratio,
                            "roe": q.roe,
                            "debt_to_equity": q.debt_to_equity,
                            "fcf": q.fcf,
                            "revenue_growth_yoy": q.revenue_growth_yoy,
                            "source": "yfinance",
                        }
                    )
            if payload:
                await session.execute(_INSERT_SQL, payload)
                await session.commit()
            attempted += len(payload)
        log.info(
            "fund_hist.batch",
            batch_start=start,
            stocks=len(batch),
            rows_attempted=len(payload),
            cumulative_attempted=attempted,
        )
        await asyncio.sleep(_BATCH_DELAY_S)

    async with SessionLocal() as session:
        stored = (await session.execute(_SQL_COUNT)).scalar_one()
    log.info("fund_hist.done", rows_attempted=attempted, stored=stored, failed=failed)
    print(
        f"Done. Rows attempted {attempted}, stored {stored}, "
        f"{failed} stocks failed/skipped."
    )


if __name__ == "__main__":
    asyncio.run(main())
