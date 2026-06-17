#!/usr/bin/env python
"""Single daily entrypoint for the forward F+ paper system — fresh data, or abort.

Runs, in STRICT order:
  STEP 1  ingest_eod   — fetch today's real EOD prices (yfinance) → prices_eod_adjusted
  STEP 2  FRESHNESS    — assert max(price date) == the expected last NSE trading day.
                         If stale (date did not advance to the expected day) → ABORT
                         with a clear error and a non-zero exit. F+ is NOT run on stale
                         data. Also logs any gap (missed trading days) so a hole in the
                         record is visible.
  STEP 3  nightly_run  — F+ runs on the fresh prices (mark-to-market, cut-on-breakdown,
                         weekly exposure, quarterly rebalance — as due). F+ uses
                         MAX(trade_date), which is now the freshly-ingested day.
  STEP 4  log a single "DAILY RUN OK …" line (date / holds / exposure / equity) so the
          run is verifiable from the logs/website at a glance.

This is INFRA ONLY — it imports and sequences existing scripts and the FROZEN F+
engine (commit 57e72d5) untouched. The data-accuracy guards it relies on:
  - entry prices are append-only (engine only INSERTs entry_price, never UPDATEs it)
  - mark-to-market uses the actual fetched close per holding
  - stale prices ABORT here rather than producing fake trades on old data

Usage:  python -m scripts.run_daily            (cron: daily ~19:00 IST, after NSE close)
        python -m scripts.run_daily --no-ingest   (skip STEP 1; check+run on current DB)
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import text

from backend.db.session import SessionLocal
from scripts import ingest_eod, nightly_run

log = structlog.get_logger()
IST = timezone(timedelta(hours=5, minutes=30))
# Today's EOD bar is not published until well after the 15:30 IST close. Before this
# hour we do NOT expect today's bar — the expected last session is the prior one. The
# nightly cron runs ~19:00 IST (after this), so it correctly demands today's data.
EOD_AVAILABLE_HOUR_IST = 17

_MAX_PRICE = text("SELECT MAX(trade_date) FROM prices_eod_adjusted")
# Expected last trading day = most recent OPEN NSE session on/before 'today' (IST).
_ELTD = text(
    "SELECT MAX(trade_date) FROM trading_calendar "
    "WHERE is_open AND exchange = 'NSE' AND trade_date <= :today"
)
# Open NSE sessions after the previous max, up to the expected day, that have NO price
# rows = missed trading days (a hole in the record).
_MISSING = text(
    "SELECT c.trade_date FROM trading_calendar c "
    "WHERE c.is_open AND c.exchange = 'NSE' "
    "AND c.trade_date > :prior AND c.trade_date <= :eltd "
    "AND NOT EXISTS (SELECT 1 FROM prices_eod_adjusted p WHERE p.trade_date = c.trade_date) "
    "ORDER BY c.trade_date"
)
_LATEST_EQUITY = text(
    "SELECT trade_date, total_equity, cash_value, exposure_level, drawdown_pct "
    "FROM paper_equity_curve ORDER BY trade_date DESC LIMIT 1"
)
_OPEN_HOLDS = text("SELECT COUNT(*) FROM paper_position WHERE status = 'open'")


async def _prior_max() -> object:
    async with SessionLocal() as s:
        return (await s.execute(_MAX_PRICE)).scalar_one()


async def _freshness_check(prior_max) -> object:
    """Return the fresh max trade_date, or raise SystemExit if prices are stale."""
    now = datetime.now(IST)
    # Before the EOD-available hour, today's bar can't exist yet → the expected last
    # session is the most recent one on/before YESTERDAY. At/after it (the 19:00 cron),
    # today is fair game.
    cutoff = now.date() if now.hour >= EOD_AVAILABLE_HOUR_IST else now.date() - timedelta(days=1)
    async with SessionLocal() as s:
        new_max = (await s.execute(_MAX_PRICE)).scalar_one()
        eltd = (await s.execute(_ELTD, {"today": cutoff})).scalar_one()

        if eltd is None:
            raise SystemExit("FRESHNESS ABORT: trading_calendar has no NSE sessions "
                             f"on/before {cutoff}. Cannot determine the expected day.")
        if new_max is None:
            raise SystemExit("FRESHNESS ABORT: prices_eod_adjusted is empty — ingest "
                             "produced no data. F+ NOT run.")

        # Gap detection: open sessions between the prior max and the expected day that
        # still have no prices = missed days (record has a hole).
        if prior_max is not None:
            missing = [r[0] for r in (await s.execute(
                _MISSING, {"prior": prior_max, "eltd": eltd})).all()]
            if missing:
                log.warning("daily.gap", missing_days=[str(d) for d in missing])
                print(f"⚠ GAP: {len(missing)} trading day(s) have NO prices "
                      f"(record hole): {', '.join(str(d) for d in missing)}")

        if new_max < eltd:
            raise SystemExit(
                f"FRESHNESS ABORT: prices are STALE — latest price date is {new_max}, "
                f"but the expected last NSE trading day is {eltd}. The date did not "
                f"advance (ingest fetched nothing new, or yfinance has not published "
                f"{eltd} yet). F+ NOT run on stale data. Re-run after the EOD lands."
            )
        log.info("daily.fresh_ok", price_date=str(new_max), expected=str(eltd),
                 prior=str(prior_max))
        print(f"FRESHNESS OK: prices as of {new_max} == expected last NSE session {eltd}.")
        return new_max


async def _final_line(price_date) -> None:
    async with SessionLocal() as s:
        row = (await s.execute(_LATEST_EQUITY)).first()
        holds = (await s.execute(_OPEN_HOLDS)).scalar_one()
    if row is None:
        print(f"DAILY RUN OK — prices as of {price_date}, but NO paper portfolio yet "
              f"(inception not committed; run scripts.paper_inception --commit). "
              f"Prices are fresh; F+ has nothing to mark.")
        return
    eq_date, equity, cash, exposure, dd = row
    print(f"DAILY RUN OK — prices as of {price_date}, F+ holds {holds}, "
          f"exposure {float(exposure)}, equity Rs {float(equity):,.0f} "
          f"(cash Rs {float(cash):,.0f}, drawdown {float(dd)}%, curve @ {eq_date})")
    log.info("daily.ok", price_date=str(price_date), equity_date=str(eq_date),
             holds=holds, exposure=float(exposure), equity=float(equity))


async def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Daily F+ forward run — fresh data or abort.")
    p.add_argument("--no-ingest", action="store_true",
                   help="skip STEP 1 (freshness-check + run F+ on the current DB)")
    args = p.parse_args(argv)

    started = datetime.now(IST)
    print(f"=== DAILY RUN start {started.isoformat()} ===")

    prior = await _prior_max()

    # STEP 1 — fetch today's real EOD prices (append-only, idempotent).
    if args.no_ingest:
        print("STEP 1 ingest: SKIPPED (--no-ingest).")
    else:
        print("STEP 1 ingest_eod: fetching latest EOD prices…")
        await ingest_eod.main([])

    # STEP 2 — freshness gate. Raises SystemExit (non-zero) on stale data; F+ not run.
    print("STEP 2 freshness check…")
    price_date = await _freshness_check(prior)

    # STEP 3 — F+ on the fresh prices (frozen engine, unchanged).
    print("STEP 3 nightly_run (F+)…")
    await nightly_run.main()

    # STEP 4 — single verifiable status line.
    await _final_line(price_date)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except SystemExit as e:
        # Clear, non-zero exit on a freshness abort (or any explicit guard failure).
        msg = str(e)
        if msg and not msg.isdigit():
            print(msg)
            log.error("daily.abort", reason=msg)
            sys.exit(1)
        raise
