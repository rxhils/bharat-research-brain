#!/usr/bin/env python
"""Backfill historical sector-momentum signals (Chunk 5.2b Task 4).

Pure compute from `prices_eod_adjusted` + `stocks.sector` — no external source.
For each trading date with >= 30 prior trading days, for each real sector label:
  avg_return_30d = mean over active stocks of (close / close_30_trading_days_ago - 1)
  stock_count    = number of stocks contributing
Then the day's sectors are ranked cross-sectionally and classified:
  top third -> leading, bottom third -> lagging, middle -> neutral.

mle no-lookahead: the 30-day return at date D uses close[D] and close[D-30]
(both <= D), computed via a strictly-backward shift; classification uses only
that day's sector averages. An explicit assert verifies the 30-days-ago bar
predates the computed_date. Sector momentum is same-day observable, so
`computed_date` IS the availability date.

Active-stock filter honors survivorship: a stock counts on date D only if
`delisted_on IS NULL OR delisted_on > D`.

The cross-sectional rank breaks ties by sector name (deterministic) so re-runs
produce identical classifications when avg returns tie at 4 decimals.

ON CONFLICT (sector, computed_date) DO NOTHING — never overwrites real data.

Usage:
    python scripts/backfill_sector_momentum_historical.py
"""
from __future__ import annotations

import asyncio
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

import structlog
from sqlalchemy import text

from backend.db.session import SessionLocal

log = structlog.get_logger()

_LOOKBACK = 30  # trading days
_Q4 = Decimal("0.0001")

_SQL_PRICES = text(
    "SELECT isin, trade_date, adj_close FROM prices_eod_adjusted "
    "WHERE adj_close IS NOT NULL ORDER BY isin, trade_date"
)
_SQL_SECTORS = text(
    "SELECT isin, sector, delisted_on FROM stocks WHERE sector IS NOT NULL"
)
_INSERT = text(
    """
    INSERT INTO sector_signals_historical
        (sector, computed_date, avg_return_30d, stock_count, classification, source)
    VALUES (:sector, :computed_date, :avg_return_30d, :stock_count,
            :classification, 'backfill')
    ON CONFLICT (sector, computed_date) DO NOTHING
    """
)
_COUNT = text("SELECT count(*) FROM sector_signals_historical")


def _q(x: float) -> Decimal:
    return Decimal(str(x)).quantize(_Q4, rounding=ROUND_HALF_EVEN)


def compute_sector_rows(
    price_rows: list[tuple[str, Any, Any]],
    sector_rows: list[tuple[str, str, Any]],
) -> list[dict[str, Any]]:
    """Per (sector, date) avg 30d return + classification (pure given inputs).

    Lookahead guard: the 30-days-ago trade_date must strictly precede the
    computed_date for every contributing row (asserted).
    """
    import pandas as pd

    df = pd.DataFrame(price_rows, columns=["isin", "trade_date", "adj_close"])
    if df.empty:
        return []
    df["adj_close"] = df["adj_close"].astype(float)
    df = df.sort_values(["isin", "trade_date"])

    g = df.groupby("isin", sort=False)
    df["close_30ago"] = g["adj_close"].shift(_LOOKBACK)
    df["date_30ago"] = g["trade_date"].shift(_LOOKBACK)
    df = df[df["close_30ago"].notna() & (df["close_30ago"] != 0)].copy()
    df["ret30"] = df["adj_close"] / df["close_30ago"] - 1.0

    # LOOKAHEAD GUARD (mle-workflow): every return uses only bars on-or-before D.
    assert (df["date_30ago"] < df["trade_date"]).all(), "lookahead in 30d return"

    sec = pd.DataFrame(sector_rows, columns=["isin", "sector", "delisted_on"])
    df = df.merge(sec, on="isin", how="inner")
    # Active-on-date filter (survivorship): delisted_on NULL or strictly after D.
    active = df["delisted_on"].isna() | (df["delisted_on"] > df["trade_date"])
    df = df[active]

    grouped = (
        df.groupby(["trade_date", "sector"])
        .agg(avg_return_30d=("ret30", "mean"), stock_count=("ret30", "size"))
        .reset_index()
    )

    out: list[dict[str, Any]] = []
    for trade_date, day in grouped.groupby("trade_date"):
        # Deterministic: sector name breaks ties so re-runs are identical.
        ranked = day.sort_values(
            ["avg_return_30d", "sector"], ascending=[False, True]
        ).reset_index(drop=True)
        n = len(ranked)
        k = n // 3  # top third leading, bottom third lagging, middle neutral
        for i, row in ranked.iterrows():
            if k > 0 and i < k:
                cls = "leading"
            elif k > 0 and i >= n - k:
                cls = "lagging"
            else:
                cls = "neutral"
            out.append(
                {
                    "sector": row["sector"],
                    "computed_date": trade_date,
                    "avg_return_30d": _q(float(row["avg_return_30d"])),
                    "stock_count": int(row["stock_count"]),
                    "classification": cls,
                }
            )
    return out


async def main() -> None:
    async with SessionLocal() as session:
        price_rows = (await session.execute(_SQL_PRICES)).all()
        sector_rows = (await session.execute(_SQL_SECTORS)).all()
    log.info("sector_hist.loaded", price_rows=len(price_rows), stocks=len(sector_rows))

    rows = await asyncio.to_thread(
        compute_sector_rows,
        [(i, d, c) for i, d, c in price_rows],
        [(i, s, dl) for i, s, dl in sector_rows],
    )
    log.info("sector_hist.computed", rows=len(rows))

    async with SessionLocal() as session:
        for i in range(0, len(rows), 2000):
            await session.execute(_INSERT, rows[i : i + 2000])
        await session.commit()
        stored = (await session.execute(_COUNT)).scalar_one()

    log.info("sector_hist.done", rows_attempted=len(rows), stored=stored)
    print(f"Done. Attempted {len(rows)} rows, stored {stored}.")


if __name__ == "__main__":
    asyncio.run(main())
