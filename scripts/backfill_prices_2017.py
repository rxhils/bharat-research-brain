#!/usr/bin/env python
"""Backfill historical adjusted prices (2015-06 -> 2021-05) from yfinance.

One-shot loader so the covid-era walk-forward (2017-2020) has price history; the
native bhavcopy pipeline only reaches back to 2021-05-26. Writes BOTH:
  * prices_eod          — raw close + volume (volume feeds the technical sub-signal)
  * prices_eod_adjusted — Adj-Close-derived adjusted OHLCV (drives selection +
                          entry/exit). adj_factor = AdjClose/Close (split + dividend).

ON CONFLICT (trade_date, isin) DO NOTHING on both tables, so the existing
2021-05-26+ native rows are NEVER clobbered, and the script is re-runnable.

yfinance "Adj Close" (auto_adjust=False) is total-return-adjusted (splits +
dividends, multiplicative) — internally consistent and the right match for the
Nifty 500 TRI benchmark. NOTE: this differs from the native 2021-2026 pipeline's
adjustment METHOD (multiplicative split + subtractive dividend), so do not run a
backtest window that SPANS 2021-05; the covid windows (all end <= 2020-12) don't.

SURVIVORSHIP: ingests only today's active universe (`stocks WHERE delisted_on IS
NULL`). Pre-2021 index membership is unknown, so any 2017-2020 backtest off this
data excludes stocks that delisted/died — i.e. it is survivorship-biased
(optimistic). Flagged in the lesson note; not fixable without historical
constituents.

Usage:
    python -m scripts.backfill_prices_2017 [--start 2015-06-01] [--end 2021-05-26]
"""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import SessionLocal

log = structlog.get_logger()

_FETCH_CONCURRENCY = 8
_CHUNK = 25  # tickers fetched+inserted+committed per batch (bounds memory)
_Q4 = Decimal("0.0001")
_Q8 = Decimal("0.00000001")

_SQL_UNIVERSE = text(
    "SELECT isin, nse_symbol FROM stocks "
    "WHERE delisted_on IS NULL AND nse_symbol IS NOT NULL ORDER BY nse_symbol"
)
_SQL_NEW_RUN = text(
    "INSERT INTO data_ingestion_runs (agent_name, status) "
    "VALUES ('backfill_prices_2017', 'running') RETURNING id"
)
_SQL_FINISH_RUN = text(
    "UPDATE data_ingestion_runs SET status='success', finished_at=now() WHERE id=:id"
)
_SQL_INS_RAW = text(
    """
    INSERT INTO prices_eod
        (trade_date, isin, open, high, low, close, volume, source, ingestion_run_id)
    VALUES (:d, :isin, :o, :h, :l, :c, :v, 'yfinance', :run)
    ON CONFLICT (trade_date, isin) DO NOTHING
    """
)
_SQL_INS_ADJ = text(
    """
    INSERT INTO prices_eod_adjusted
        (trade_date, isin, adj_open, adj_high, adj_low, adj_close, adj_volume,
         adj_factor, source)
    VALUES (:d, :isin, :ao, :ah, :al, :ac, :v, :f, 'yfinance')
    ON CONFLICT (trade_date, isin) DO NOTHING
    """
)
_SQL_VERIFY = text(
    """
    SELECT MIN(trade_date), MAX(trade_date), COUNT(*), COUNT(DISTINCT isin)
    FROM prices_eod_adjusted WHERE source='yfinance'
    """
)


@dataclass(frozen=True)
class Bar:
    d: date
    o: Decimal
    h: Decimal
    low: Decimal
    c: Decimal
    adj_c: Decimal
    v: int | None


def _dec(x: object) -> Decimal | None:
    try:
        import math

        f = float(x)  # type: ignore[arg-type]
        if math.isnan(f):
            return None
        return Decimal(str(f)).quantize(_Q4)
    except (TypeError, ValueError):
        return None


def _fetch_sync(symbol: str, start: str, end: str) -> list[Bar]:
    """yfinance daily OHLCV + Adj Close for one ticker. Empty on any failure."""
    import yfinance as yf  # lazy: keeps module importable without the dep

    try:
        hist = yf.Ticker(f"{symbol}.NS").history(
            start=start, end=end, auto_adjust=False
        )
    except Exception as exc:  # noqa: BLE001 - external feed, best-effort
        log.warning("backfill.fetch_failed", symbol=symbol, error=str(exc))
        return []
    if hist is None or getattr(hist, "empty", True):
        return []
    bars: list[Bar] = []
    for ts, row in hist.iterrows():
        o, h, low, c, ac = (
            _dec(row.get("Open")), _dec(row.get("High")), _dec(row.get("Low")),
            _dec(row.get("Close")), _dec(row.get("Adj Close")),
        )
        if c is None or c <= 0 or ac is None or o is None or h is None or low is None:
            continue
        if h < low:  # guard the high>=low CHECK on prices_eod
            continue
        vol_raw = row.get("Volume")
        try:
            v: int | None = None if vol_raw is None else int(vol_raw)
        except (TypeError, ValueError):
            v = None
        if v is not None and v < 0:
            v = None
        bars.append(Bar(ts.date(), o, h, low, c, ac, v))
    return bars


async def _fetch(sem: asyncio.Semaphore, isin: str, symbol: str,
                 start: str, end: str) -> tuple[str, list[Bar]]:
    async with sem:
        bars = await asyncio.to_thread(_fetch_sync, symbol, start, end)
    return isin, bars


async def _insert_bars(session: AsyncSession, isin: str, bars: list[Bar],
                       run_id: int) -> None:
    raw: list[dict[str, object]] = []
    adj: list[dict[str, object]] = []
    for b in bars:
        factor = (b.adj_c / b.c).quantize(_Q8)
        raw.append({"d": b.d, "isin": isin, "o": b.o, "h": b.h, "l": b.low,
                    "c": b.c, "v": b.v, "run": run_id})
        adj.append({"d": b.d, "isin": isin,
                    "ao": (b.o * factor).quantize(_Q4),
                    "ah": (b.h * factor).quantize(_Q4),
                    "al": (b.low * factor).quantize(_Q4),
                    "ac": b.adj_c, "v": b.v, "f": factor})
    if raw:
        await session.execute(_SQL_INS_RAW, raw)
        await session.execute(_SQL_INS_ADJ, adj)


async def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Backfill yfinance prices 2015-2021.")
    parser.add_argument("--start", default="2015-06-01")
    parser.add_argument("--end", default="2021-05-26")  # exclusive -> last bar 05-25
    args = parser.parse_args(argv)

    async with SessionLocal() as session:
        universe = [(i, s) for i, s in (await session.execute(_SQL_UNIVERSE)).all()]
        run_id = (await session.execute(_SQL_NEW_RUN)).scalar_one()
        await session.commit()
        log.info("backfill.start", stocks=len(universe), run_id=run_id,
                 start=args.start, end=args.end)

        sem = asyncio.Semaphore(_FETCH_CONCURRENCY)
        done = with_data = total_bars = 0
        for off in range(0, len(universe), _CHUNK):
            batch = universe[off : off + _CHUNK]
            results = await asyncio.gather(
                *(_fetch(sem, i, s, args.start, args.end) for i, s in batch)
            )
            for isin, bars in results:
                if bars:
                    with_data += 1
                    total_bars += len(bars)
                    await _insert_bars(session, isin, bars, run_id)
            await session.commit()
            done += len(batch)
            print(f"  {done}/{len(universe)} tickers | with_data={with_data} "
                  f"bars={total_bars}", flush=True)

        await session.execute(_SQL_FINISH_RUN, {"id": run_id})
        await session.commit()
        mn, mx, rows, isins = (await session.execute(_SQL_VERIFY)).first()

    print(f"\nDONE. yfinance-sourced adjusted rows: {rows} "
          f"({isins} stocks, {mn} -> {mx}). {with_data}/{len(universe)} tickers "
          f"returned data.")
    log.info("backfill.done", rows=rows, stocks=isins, first=str(mn), last=str(mx))


if __name__ == "__main__":
    asyncio.run(main())
