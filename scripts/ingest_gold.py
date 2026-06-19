"""Ingest rupee-gold (GOLDBEES.NS, Nippon India Gold ETF) for the Phase-2 gauntlet.

Single-sourced from yfinance (same methodology discipline as the equity series:
ONE provider, ONE adjustment method). Stores into a dedicated `gold_prices_eod`
table so it never pollutes the equity universe (`stocks` / `_active_isins`).
Phase-2 Test 2 (gold-in-cash) reads this table by date.

    POSTGRES_URL=... PYTHONPATH=. python scripts/ingest_gold.py

Reports coverage vs the NSE equity trading calendar for all 8 walk-forward
windows so gaps are visible (fail loudly if a window is materially incomplete).
"""
from __future__ import annotations

import asyncio
import os
from datetime import date

import asyncpg
import pandas as pd
import yfinance as yf

_TICKER = "GOLDBEES.NS"
_START, _END = "2017-01-01", "2026-06-19"

_DDL = """
CREATE TABLE IF NOT EXISTS gold_prices_eod (
    trade_date  date PRIMARY KEY,
    adj_close   numeric(18,6) NOT NULL,
    close       numeric(18,6) NOT NULL,
    source      text NOT NULL DEFAULT 'yfinance:GOLDBEES.NS',
    computed_at timestamptz NOT NULL DEFAULT now()
);
"""

# The 8 walk-forward windows (must match the gauntlet harness).
_WINDOWS = [
    ("E1 W1 2017-18", date(2017, 1, 16), date(2018, 12, 31)),
    ("E1 W2 2017-19", date(2017, 6, 1), date(2019, 6, 1)),
    ("E1 W3 2018-cov", date(2018, 1, 1), date(2020, 6, 30)),
    ("E1 W4 2018-20", date(2018, 6, 1), date(2020, 12, 31)),
    ("E2 W1 2021-23", date(2021, 6, 1), date(2023, 6, 1)),
    ("E2 W2 2022-24", date(2022, 6, 1), date(2024, 6, 1)),
    ("E2 W3 2023-25", date(2023, 6, 1), date(2025, 6, 1)),
    ("E2 W4 2024-26", date(2024, 1, 1), date(2026, 5, 26)),
]


def _fetch() -> list[tuple]:
    df = yf.download(_TICKER, start=_START, end=_END, auto_adjust=False, progress=False)
    if df is None or df.empty:
        raise SystemExit("yfinance returned no data for " + _TICKER)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    rows: list[tuple] = []
    for idx, r in df.iterrows():
        adj = r.get("Adj Close")
        cls = r.get("Close")
        if pd.isna(adj) or pd.isna(cls):
            continue
        rows.append((idx.date(), float(adj), float(cls)))
    return rows


async def main() -> int:
    url = os.environ["POSTGRES_URL"].replace("+asyncpg", "").split("?")[0]
    rows = _fetch()
    conn = await asyncpg.connect(url)
    try:
        await conn.execute(_DDL)
        await conn.executemany(
            "INSERT INTO gold_prices_eod (trade_date, adj_close, close) "
            "VALUES ($1,$2,$3) ON CONFLICT (trade_date) DO UPDATE SET "
            "adj_close=EXCLUDED.adj_close, close=EXCLUDED.close, computed_at=now()",
            rows,
        )
        tot = await conn.fetchrow(
            "SELECT count(*) n, min(trade_date) mn, max(trade_date) mx FROM gold_prices_eod")
        print(f"gold_prices_eod: {tot['n']} rows  {tot['mn']} -> {tot['mx']}  "
              f"(source {_TICKER}, single yfinance method)")
        print("\nwindow            gold_days  nse_days  coverage   status")
        all_ok = True
        for nm, a, b in _WINDOWS:
            g = await conn.fetchval(
                "SELECT count(*) FROM gold_prices_eod WHERE trade_date BETWEEN $1 AND $2", a, b)
            e = await conn.fetchval(
                "SELECT count(DISTINCT trade_date) FROM prices_eod_adjusted "
                "WHERE trade_date BETWEEN $1 AND $2", a, b)
            cov = (g / e * 100) if e else 0.0
            ok = cov >= 99.0
            all_ok = all_ok and ok
            print(f"  {nm:<15} {g:>8}  {e:>8}   {cov:>6.2f}%   {'OK' if ok else 'GAP!'}")
        print("\nALL WINDOWS GAP-FREE (>=99% of NSE calendar):", all_ok)
        return 0 if all_ok else 1
    finally:
        await conn.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
