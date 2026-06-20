#!/usr/bin/env python
"""Forward replay of the FROZEN F+ paper engine over ALREADY-COLLECTED real prices.

Bootstraps a real, NO-LOOKAHEAD equity curve from inception to the latest EOD price
date by stepping the engine one trading day at a time:
  - daily_mark        every trading day        (mark-to-market + cut-on-breakdown)
  - weekly_exposure   every EXPOSURE_CHECK_DAYS (regime -> exposure rescale)
  - quarterly_rebalance every REBALANCE_DAYS    (full F+ re-pick)

This is EXACTLY what scripts.nightly_run does going forward — replay just catches up
history that is already in prices_eod_adjusted. Requires inception to be committed.
Idempotent only in the sense that re-running appends; intended for a fresh inception.

Usage:  python -m scripts.paper_replay
"""
from __future__ import annotations

import asyncio

import structlog
from sqlalchemy import text

from backend.db.session import SessionLocal
from backend.paper import engine as E

log = structlog.get_logger()

_DATES = text(
    "SELECT DISTINCT trade_date FROM prices_eod_adjusted "
    "WHERE trade_date > :inception "
    "AND trade_date <= (SELECT MAX(trade_date) FROM prices_eod_adjusted) "
    "ORDER BY trade_date"
)


async def main() -> None:
    async with SessionLocal() as s:
        acct = await E.get_account(s)
        if acct is None:
            print("No paper_account — run `python -m scripts.paper_inception --commit` first.")
            return
        inception = acct["inception_date"]
        dates = [r[0] for r in (await s.execute(_DATES, {"inception": inception})).all()]
        print(f"Replaying {len(dates)} trading days forward from inception {inception} "
              f"(engine: Enhanced F+ commit 6ced078, mechanical composite)...")
        last = None
        for i, d in enumerate(dates, 1):
            last = await E.daily_mark(s, d)
            if i % E.EXPOSURE_CHECK_DAYS == 0:
                wk = await E.weekly_exposure(s, d)
                if wk["changed"]:
                    print(f"  {d}: exposure -> {wk['exposure']}")
            if i % E.REBALANCE_DAYS == 0:
                q = await E.quarterly_rebalance(s, d)
                print(f"  {d}: quarterly rebalance -> {q['names']} names")
        if last is not None:
            print(f"Done. {len(dates)} days replayed. Equity Rs {float(last['equity']):,.0f}, "
                  f"cash Rs {float(last['cash']):,.0f}.")
        else:
            print("No trading days after inception — nothing to replay yet.")


if __name__ == "__main__":
    asyncio.run(main())
