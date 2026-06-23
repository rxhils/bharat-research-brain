#!/usr/bin/env python
"""Single daily entrypoint for the Maven live paper books — SELF-HEALING.

Runs after market close (cron ~20:00 IST). Order:
  STEP 1  ingest  — NSE bhavcopy (same-day official prices), with yfinance fallback
                    if the bhavcopy is still behind the expected session.
  STEP 2  status  — compute the latest price date + the expected last NSE session.
                    A late/stale feed is a WARNING, not a hard stop (self-healing).
  STEP 3  process — run the books ONLY if there is a NEW trading day to process (or a
                    live book still needs its first allocation). Processing each day
                    exactly once is important: daily_mark accrues one day of cash
                    interest, so a same-day re-run must NOT double-count.
  STEP 4  log a single verifiable status line.

Self-healing: if prices are late, this run simply finds "no new day" and exits
cleanly (exit 0); the next run picks the day up the moment it lands. It never aborts
the whole pipeline, and it never trades on stale data (it only acts when the price
date advances). NO LOOKAHEAD: decisions read only data <= the latest price date.

Usage:  python -m scripts.run_daily            (cron: daily ~20:00 IST, after close)
        python -m scripts.run_daily --no-ingest   (skip STEP 1; process current DB)
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import text

from backend.db.session import SessionLocal
from scripts import ingest_bhavcopy, ingest_eod, nightly_run

log = structlog.get_logger()
IST = timezone(timedelta(hours=5, minutes=30))
EOD_AVAILABLE_HOUR_IST = 17

_MAX_PRICE = text("SELECT MAX(trade_date) FROM prices_eod_adjusted")
_ELTD = text(
    "SELECT MAX(trade_date) FROM trading_calendar "
    "WHERE is_open AND exchange='NSE' AND trade_date <= :today"
)
_LAST_CURVE = text("SELECT MAX(trade_date) FROM paper_equity_curve")
_PENDING_FIRST = text(
    "SELECT count(*) FROM portfolios p WHERE p.status='live' "
    "AND p.inception_date IS NOT NULL AND p.inception_date <= :as_of "
    "AND NOT EXISTS (SELECT 1 FROM paper_equity_curve c WHERE c.portfolio_id=p.id)"
)
_LATEST_EQUITY = text(
    "SELECT p.name, c.trade_date, c.total_equity, c.cash_value, c.exposure_level "
    "FROM paper_equity_curve c JOIN portfolios p ON p.id=c.portfolio_id "
    "WHERE c.trade_date=(SELECT MAX(trade_date) FROM paper_equity_curve) ORDER BY p.name"
)


async def _scalar(sql, **kw):  # noqa: ANN001
    async with SessionLocal() as s:
        return (await s.execute(sql, kw)).scalar_one()


async def _status():
    """(latest_price_date, expected_last_session, is_fresh)."""
    now = datetime.now(IST)
    cutoff = now.date() if now.hour >= EOD_AVAILABLE_HOUR_IST else now.date() - timedelta(days=1)
    async with SessionLocal() as s:
        as_of = (await s.execute(_MAX_PRICE)).scalar_one()
        eltd = (await s.execute(_ELTD, {"today": cutoff})).scalar_one()
    fresh = as_of is not None and eltd is not None and as_of >= eltd
    return as_of, eltd, fresh


async def _final_line(as_of) -> None:  # noqa: ANN001
    async with SessionLocal() as s:
        rows = (await s.execute(_LATEST_EQUITY)).all()
    if not rows:
        print(f"DAILY RUN OK — prices as of {as_of}, no books have started yet.")
        return
    for name, d, eq, cash, exp in rows:
        print(f"  {name}: equity Rs {float(eq):,.0f} (cash Rs {float(cash):,.0f}, "
              f"exposure {float(exp)}, curve @ {d})")


async def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Daily self-healing live-book run.")
    p.add_argument("--no-ingest", action="store_true", help="skip ingest; process DB as-is")
    args = p.parse_args(argv)

    started = datetime.now(IST)
    print(f"=== DAILY RUN start {started.isoformat()} ===")

    # STEP 1 — ingest same-day prices (bhavcopy), yfinance fallback if still behind.
    if args.no_ingest:
        print("STEP 1 ingest: SKIPPED (--no-ingest).")
    else:
        print("STEP 1 ingest_bhavcopy (official same-day prices)…")
        await ingest_bhavcopy.main([])
        _as_of, _eltd, fresh = await _status()
        if not fresh:
            print("STEP 1b bhavcopy behind expected → yfinance fallback…")
            await ingest_eod.main([])

    # STEP 2 — status (self-healing: stale is a warning, never a hard abort).
    as_of, eltd, fresh = await _status()
    if as_of is None:
        print("No prices in DB at all — nothing to process.")
        return
    if fresh:
        print(f"STEP 2 FRESHNESS OK — prices as of {as_of} == expected session {eltd}.")
    else:
        print(f"STEP 2 ⚠ prices are behind (latest {as_of}, expected {eltd}). "
              f"Self-healing: will process what's available and retry next run.")

    # STEP 3 — process ONLY a genuinely new day (exactly-once: avoids double cash accrual).
    last_curve = await _scalar(_LAST_CURVE)
    pending_first = await _scalar(_PENDING_FIRST, as_of=as_of)
    new_day = last_curve is None or as_of > last_curve
    if not (new_day or pending_first):
        print(f"STEP 3 nothing new — books already current through {last_curve}. "
              f"(Idempotent no-op; will act when the price date advances past {last_curve}.)")
        await _final_line(as_of)
        return
    print(f"STEP 3 processing {as_of} (prior curve {last_curve}, "
          f"pending first-allocations {pending_first})…")
    await nightly_run.main()

    # STEP 4 — verifiable status line per book.
    await _final_line(as_of)


if __name__ == "__main__":
    asyncio.run(main())
