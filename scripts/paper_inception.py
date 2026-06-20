#!/usr/bin/env python
"""Create an EMPTY-CASH paper book for a portfolio (Maven multi-portfolio).

The book is full capital in cash, 0 holdings, inception dated per the registry. The
FIRST real picks happen automatically at the nightly run on/after inception (NO
backfill, NO pre-picks). DRY-RUN by default; pass --commit to persist.

Usage:
    python -m scripts.paper_inception                      # dry-run, portfolio=Quant
    python -m scripts.paper_inception --portfolio Quant --commit   # create empty book
"""
from __future__ import annotations

import argparse
import asyncio

from backend.db.session import SessionLocal
from backend.paper import engine as E


async def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Create an empty-cash paper book.")
    p.add_argument("--portfolio", default="Quant", help="portfolio name (default Quant)")
    p.add_argument("--commit", action="store_true", help="persist (create the book)")
    args = p.parse_args(argv)

    async with SessionLocal() as s:
        port = await E.get_portfolio(s, args.portfolio)
        if port is None:
            print(f"No portfolio named {args.portfolio!r} in the registry.")
            return
        if port["status"] != "live":
            print(f"Portfolio {args.portfolio!r} status={port['status']} (not live) — "
                  "go live by flipping status to 'live' after its gauntlet passes.")
            return
        if port["inception_date"] is None:
            print(f"Portfolio {args.portfolio!r} has no inception_date set.")
            return
        cap = port["starting_capital"] or E.STARTING_CAPITAL
        existing = await E.get_account(s, port["id"])
        mode = "COMMITTED" if args.commit else "DRY-RUN (not persisted)"
        print(f"=== CREATE EMPTY-CASH BOOK — {mode} ===")
        print(f"portfolio: {args.portfolio} (id {port['id']}, status {port['status']})")
        print(f"engine: Enhanced F+ commit 6ced078 | inception {port['inception_date']} "
              f"| capital Rs {float(cap):,.0f} (100% cash, 0 holdings)")
        if existing is not None:
            print("Book ALREADY EXISTS — nothing to do (inception is once-only).")
            return
        if not args.commit:
            print("(DRY-RUN — re-run with --commit to create. First picks happen at the "
                  "nightly run on/after inception.)")
            return
        res = await E.create_book(s, port["id"], port["inception_date"], cap)
        print(f"Created: account {res['account_id']}, Rs {float(res['cash']):,.0f} cash, "
              f"0 holdings. Awaiting first nightly run on/after {port['inception_date']}.")


if __name__ == "__main__":
    asyncio.run(main())
