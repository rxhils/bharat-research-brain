#!/usr/bin/env python
"""Forward replay of a portfolio's paper book over ALREADY-COLLECTED real prices.

Portfolio-aware (Maven multi-portfolio). Steps a book one trading day at a time from
its inception to the latest EOD price date:
  - first trading day on/after inception (empty book) -> first_allocation
  - thereafter: daily_mark, + weekly_exposure every EXPOSURE_CHECK_DAYS,
    + quarterly_rebalance every REBALANCE_DAYS

NOTE: the flagship "Quant" book is launched WITHOUT replay (100% real from Monday's
live run — no backfill). This tool exists for bootstrapping/testing a book whose
inception is in the past; do NOT run it on Quant. Requires the book (create_book) to
exist. Replay only catches up history already in prices_eod_adjusted.

Usage:  python -m scripts.paper_replay --portfolio <name>
"""
from __future__ import annotations

import argparse
import asyncio

import structlog
from sqlalchemy import text

from backend.db.session import SessionLocal
from backend.paper import engine as E

log = structlog.get_logger()

_DATES = text(
    "SELECT DISTINCT trade_date FROM prices_eod_adjusted "
    "WHERE trade_date >= :inception "
    "AND trade_date <= (SELECT MAX(trade_date) FROM prices_eod_adjusted) "
    "ORDER BY trade_date"
)


async def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Replay a portfolio's paper book forward.")
    p.add_argument("--portfolio", required=True, help="portfolio name (NOT Quant)")
    args = p.parse_args(argv)

    async with SessionLocal() as s:
        port = await E.get_portfolio(s, args.portfolio)
        if port is None:
            print(f"No portfolio named {args.portfolio!r}.")
            return
        pid, inc = port["id"], port["inception_date"]
        acct = await E.get_account(s, pid)
        if acct is None:
            print(f"No book for {args.portfolio!r} — run `paper_inception --portfolio "
                  f"{args.portfolio} --commit` first.")
            return
        if inc is None:
            print(f"{args.portfolio!r} has no inception_date.")
            return
        dates = [r[0] for r in (await s.execute(_DATES, {"inception": inc})).all()]
        print(f"Replaying {len(dates)} trading days for {args.portfolio} from inception "
              f"{inc} (engine: Enhanced F+ 6ced078)...")
        last = None
        td = 0
        for d in dates:
            if not await E.has_started(s, pid):
                res = await E.first_allocation(s, pid, d)
                print(f"  {d}: FIRST ALLOCATION -> {res['n']} names @ {res['exposure']}")
                td = 1
                continue
            td += 1
            last = await E.daily_mark(s, pid, d)
            if td % E.EXPOSURE_CHECK_DAYS == 0:
                wk = await E.weekly_exposure(s, pid, d)
                if wk["changed"]:
                    print(f"  {d}: exposure -> {wk['exposure']}")
            if td % E.REBALANCE_DAYS == 0:
                q = await E.quarterly_rebalance(s, pid, d)
                print(f"  {d}: quarterly rebalance -> {q['names']} names")
        if last is not None:
            print(f"Done. Equity Rs {float(last['equity']):,.0f}, "
                  f"cash Rs {float(last['cash']):,.0f}.")
        else:
            print("No trading days after inception — nothing to replay yet.")


if __name__ == "__main__":
    asyncio.run(main())
