#!/usr/bin/env python
"""Backfill historical market-breadth signals (Chunk 5.2b Task 3).

Pure compute from `prices_eod_adjusted` — no external source. For every trading
date it derives three breadth indicators and writes one row per (indicator,
computed_date) to `macro_signals_historical`:

  advance_decline_ratio = #(close > prev close) / #(close < prev close)
  pct_above_ema200      = % of stocks with close > their EMA200
  new_high_low_ratio    = #(within 2% of 252d max) / #(within 2% of 252d min)

No lookahead: each date's value uses only that stock's bars up to that date
(EMA200 / 252d window / prior close are all backward-looking). Breadth is
same-day observable, so `computed_date` IS the availability date (no lag).

Signals reuse the live Macro Agent (Chunk 4.12) thresholds:
  A/D  > 1.5 rising  / < 0.67 falling / else stable
  pct  > 65  bullish / < 35   bearish / else neutral
  NHL  > 2.0 strong  / < 0.5  weak    / else neutral

NOTE: EMA200 uses pandas ewm(span=200, adjust=False) (first-value seed); the live
agent SMA-seeds its EMA. Over a 200-span the seed fully decays in ~200 bars, so
the two agree on the backtest window — documented, not hidden.

ON CONFLICT (indicator, computed_date) DO NOTHING — never overwrites real data.

Usage:
    python scripts/backfill_market_breadth_historical.py
"""
from __future__ import annotations

import asyncio
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

import structlog
from sqlalchemy import text

from backend.db.session import SessionLocal

log = structlog.get_logger()

ADV_DECL = "advance_decline_ratio"
PCT_EMA200 = "pct_above_ema200"
NEW_HIGH_LOW = "new_high_low_ratio"

_EMA_SPAN = 200
_W52 = 252
_NEAR_HIGH = 0.98  # within 2% of the 252d max
_NEAR_LOW = 1.02   # within 2% of the 252d min
_Q4 = Decimal("0.0001")

_SQL_PRICES = text(
    "SELECT isin, trade_date, adj_close FROM prices_eod_adjusted "
    "WHERE adj_close IS NOT NULL ORDER BY isin, trade_date"
)
_INSERT = text(
    """
    INSERT INTO macro_signals_historical
        (indicator, computed_date, value, signal, source)
    VALUES (:indicator, :computed_date, :value, :signal, 'backfill')
    ON CONFLICT (indicator, computed_date) DO NOTHING
    """
)
_COUNT = text(
    "SELECT count(*) FROM macro_signals_historical WHERE source = 'backfill'"
)


def _ad_signal(ratio: float) -> str:
    if ratio > 1.5:
        return "rising"
    if ratio < 0.67:
        return "falling"
    return "stable"


def _pct_signal(pct: float) -> str:
    if pct > 65:
        return "bullish"
    if pct < 35:
        return "bearish"
    return "neutral"


def _nhl_signal(ratio: float) -> str:
    if ratio > 2.0:
        return "strong"
    if ratio < 0.5:
        return "weak"
    return "neutral"


def _q(x: float) -> Decimal:
    return Decimal(str(x)).quantize(_Q4, rounding=ROUND_HALF_EVEN)


def compute_breadth_frame(rows: list[tuple[str, Any, Any]]) -> Any:
    """Per-date breadth counts from (isin, trade_date, adj_close) rows.

    Returns a pandas DataFrame indexed by trade_date with columns:
    advancing, declining, above, ema_total, near_high, near_low.
    """
    import pandas as pd

    df = pd.DataFrame(rows, columns=["isin", "trade_date", "adj_close"])
    df["adj_close"] = df["adj_close"].astype(float)
    df = df.sort_values(["isin", "trade_date"])

    g = df.groupby("isin", sort=False)["adj_close"]
    prev = g.shift(1)
    df["advancing"] = (df["adj_close"] > prev).fillna(False)
    df["declining"] = (df["adj_close"] < prev).fillna(False)

    ema = g.transform(lambda s: s.ewm(span=_EMA_SPAN, adjust=False).mean())
    # EMA only meaningful once enough history exists.
    seq = g.cumcount()
    ema_valid = seq >= (_EMA_SPAN - 1)
    df["ema_total"] = ema_valid
    df["above"] = ema_valid & (df["adj_close"] > ema)

    roll_max = g.transform(lambda s: s.rolling(_W52, min_periods=_W52).max())
    roll_min = g.transform(lambda s: s.rolling(_W52, min_periods=_W52).min())
    df["near_high"] = roll_max.notna() & (df["adj_close"] >= roll_max * _NEAR_HIGH)
    df["near_low"] = roll_min.notna() & (df["adj_close"] <= roll_min * _NEAR_LOW)

    agg = df.groupby("trade_date").agg(
        advancing=("advancing", "sum"),
        declining=("declining", "sum"),
        above=("above", "sum"),
        ema_total=("ema_total", "sum"),
        near_high=("near_high", "sum"),
        near_low=("near_low", "sum"),
    )
    return agg


def build_rows(agg: Any) -> list[dict[str, Any]]:
    """One row per (indicator, date) from the per-date breadth counts."""
    out: list[dict[str, Any]] = []
    for trade_date, r in agg.iterrows():
        adv, dec = int(r["advancing"]), int(r["declining"])
        ratio = (adv / dec) if dec > 0 else float(adv if adv else 1)
        out.append(
            {
                "indicator": ADV_DECL,
                "computed_date": trade_date,
                "value": _q(ratio),
                "signal": _ad_signal(ratio),
            }
        )
        above, total = int(r["above"]), int(r["ema_total"])
        pct = (above / total * 100) if total > 0 else 0.0
        out.append(
            {
                "indicator": PCT_EMA200,
                "computed_date": trade_date,
                "value": _q(pct),
                "signal": _pct_signal(pct),
            }
        )
        nh, nl = int(r["near_high"]), int(r["near_low"])
        nhl = (nh / nl) if nl > 0 else float(nh if nh else 1)
        out.append(
            {
                "indicator": NEW_HIGH_LOW,
                "computed_date": trade_date,
                "value": _q(nhl),
                "signal": _nhl_signal(nhl),
            }
        )
    return out


async def main() -> None:
    async with SessionLocal() as session:
        price_rows = (await session.execute(_SQL_PRICES)).all()
    log.info("breadth.loaded", price_rows=len(price_rows))

    agg = await asyncio.to_thread(
        compute_breadth_frame, [(i, d, c) for i, d, c in price_rows]
    )
    rows = build_rows(agg)
    log.info("breadth.computed", dates=len(agg), rows=len(rows))

    async with SessionLocal() as session:
        # Insert in chunks to keep statements reasonable.
        for i in range(0, len(rows), 1000):
            await session.execute(_INSERT, rows[i : i + 1000])
        await session.commit()
        stored = (await session.execute(_COUNT)).scalar_one()

    log.info("breadth.done", rows_attempted=len(rows), stored=stored)
    print(f"Done. Attempted {len(rows)} rows across {len(agg)} dates, stored {stored}.")


if __name__ == "__main__":
    asyncio.run(main())
