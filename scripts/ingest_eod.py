#!/usr/bin/env python
"""Daily incremental EOD price ingest (yfinance) for the live F+ paper system.

Appends the latest adjusted OHLCV for today's active universe into prices_eod /
prices_eod_adjusted, starting just after the last stored trade_date. Idempotent
(ON CONFLICT DO NOTHING via the reused backfill inserts) and re-runnable. Run
BEFORE scripts.nightly_run in the nightly cron. Permitted source (yfinance EOD,
CLAUDE.md §5) — NO NSE scraping.

NOTE (adjustment seam): yfinance "Adj Close" uses yfinance's own total-return
baseline, which differs from the native 2021-05-26+ bhavcopy adjustment method.
Day-over-day returns are correct; absolute levels can shift slightly at the
yfinance/native seam. For a perfectly clean forward record, run inception on a DB
whose history is all from this one source. See backfill_prices_2017.py for method.

Usage:
    python -m scripts.ingest_eod                 # since last stored date (+3d gap repair)
    python -m scripts.ingest_eod --lookback 10   # re-fetch last 10 days
    python -m scripts.ingest_eod --end 2026-06-13
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import date, timedelta

import structlog
from sqlalchemy import text

from backend.db.session import SessionLocal
from scripts.backfill_prices_2017 import _CHUNK, _FETCH_CONCURRENCY, _fetch, _insert_bars

log = structlog.get_logger()

_SQL_UNIVERSE = text(
    "SELECT isin, nse_symbol FROM stocks "
    "WHERE delisted_on IS NULL AND nse_symbol IS NOT NULL ORDER BY nse_symbol"
)
_SQL_LAST = text("SELECT MAX(trade_date) FROM prices_eod_adjusted")
_SQL_NEW_RUN = text(
    "INSERT INTO data_ingestion_runs (agent_name, status) "
    "VALUES ('ingest_eod', 'running') RETURNING id"
)
_SQL_FINISH_RUN = text(
    "UPDATE data_ingestion_runs SET status='success', finished_at=now() WHERE id=:id"
)


async def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Daily incremental yfinance EOD ingest.")
    p.add_argument("--lookback", type=int, default=3,
                   help="extra days before the last stored date to re-fetch (gap repair)")
    p.add_argument("--end", default=None, help="YYYY-MM-DD exclusive (default: tomorrow)")
    args = p.parse_args(argv)

    async with SessionLocal() as s:
        universe = [(i, sym) for i, sym in (await s.execute(_SQL_UNIVERSE)).all()]
        last = (await s.execute(_SQL_LAST)).scalar_one()
        start = (last - timedelta(days=args.lookback)) if last else date(2015, 6, 1)
        end = args.end or (date.today() + timedelta(days=1)).isoformat()
        run_id = (await s.execute(_SQL_NEW_RUN)).scalar_one()
        await s.commit()
        log.info("ingest_eod.start", stocks=len(universe), last_stored=str(last),
                 start=str(start), end=end, run_id=run_id)
        print(f"Ingesting {len(universe)} tickers {start} -> {end} (last stored {last})...")

        sem = asyncio.Semaphore(_FETCH_CONCURRENCY)
        done = with_data = total = 0
        for off in range(0, len(universe), _CHUNK):
            batch = universe[off:off + _CHUNK]
            results = await asyncio.gather(
                *(_fetch(sem, i, sym, start.isoformat(), end) for i, sym in batch))
            for isin, bars in results:
                if bars:
                    with_data += 1
                    total += len(bars)
                    await _insert_bars(s, isin, bars, run_id)
            await s.commit()
            done += len(batch)
            print(f"  {done}/{len(universe)} | with_data={with_data} bars={total}", flush=True)
        await s.execute(_SQL_FINISH_RUN, {"id": run_id})
        await s.commit()
        new_last = (await s.execute(_SQL_LAST)).scalar_one()
    print(f"\nDONE. {total} new bars ({with_data}/{len(universe)} tickers returned data). "
          f"Latest trade_date now {new_last}.")
    log.info("ingest_eod.done", bars=total, latest=str(new_last))


if __name__ == "__main__":
    asyncio.run(main())
