#!/usr/bin/env python
"""Nightly orchestration for the forward F+ paper portfolio (the '24/7' engine).

Runs AFTER market close + EOD price ingest. Idempotent and logged — safe to re-run.

Steps:
  1. (Agentic pipeline) — DEFERRED: live News/FII/Fundamental agents need API keys
     (NEWSAPI_KEY/FMP_KEY/FYERS_ACCESS_TOKEN are empty). Until those exist, the F+
     score is the MECHANICAL composite (the validated signal), computed inside the
     paper engine. When keys are added, swap the score source to stock_rankings here.
  2. Paper engine, as due by trading-day count since inception:
       - DAILY  : mark-to-market + cut-on-breakdown (every run)
       - WEEKLY : every 5 trading days — regime -> exposure rescale
       - QUARTERLY: every 63 trading days — full F+ name rebalance
  3. The equity curve + drawdown are updated by the daily step.

No-lookahead: as_of = the latest trading date that has EOD prices; every decision
reads only data <= as_of. Does nothing (cleanly) until inception has been committed.

Usage:  python -m scripts.nightly_run        (cron: daily ~19:00 IST)
"""
from __future__ import annotations

import asyncio

import structlog
from sqlalchemy import text

from backend.db.session import SessionLocal
from backend.paper import engine as E

log = structlog.get_logger()

_LATEST = text("SELECT MAX(trade_date) FROM prices_eod_adjusted")
_TD_SINCE = text(
    "SELECT COUNT(DISTINCT trade_date) FROM prices_eod_adjusted "
    "WHERE trade_date >= :inception AND trade_date <= :as_of"
)


async def main() -> None:
    async with SessionLocal() as s:
        acct = await E.get_account(s)
        if acct is None:
            print("No paper_account yet — inception not committed. Nothing to do. "
                  "(Run scripts.paper_inception --commit on the cloud to go live.)")
            return
        as_of = (await s.execute(_LATEST)).scalar_one()
        if as_of <= acct["inception_date"]:
            print(f"Latest price date {as_of} <= inception {acct['inception_date']}; "
                  "waiting for the next EOD. Nothing to do.")
            return
        td = (await s.execute(
            _TD_SINCE, {"inception": acct["inception_date"], "as_of": as_of})).scalar_one()

        log.info("nightly.start", as_of=str(as_of), trading_days_since_inception=td)
        daily = await E.daily_mark(s, as_of)
        print(f"DAILY  {as_of}: equity Rs {float(daily['equity']):,.0f}, "
              f"cash Rs {float(daily['cash']):,.0f}, breakdown_cuts {daily['breakdown_cuts']}")

        if td % E.EXPOSURE_CHECK_DAYS == 0:
            wk = await E.weekly_exposure(s, as_of)
            print(f"WEEKLY {as_of}: regime exposure {wk['exposure']} "
                  f"(changed={wk['changed']})")
        if td % E.REBALANCE_DAYS == 0:
            q = await E.quarterly_rebalance(s, as_of)
            print(f"QUARTERLY {as_of}: re-picked {q['names']} names at exposure "
                  f"{q['exposure']}")
        log.info("nightly.done", as_of=str(as_of))
        print(f"Nightly run complete for {as_of} (trading day #{td} since inception).")


if __name__ == "__main__":
    asyncio.run(main())
