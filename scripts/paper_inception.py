#!/usr/bin/env python
"""Inception of the forward F+ paper portfolio (Rs 10,00,000).

DRY-RUN by default: computes what the FROZEN F+ engine would buy at the latest real
EOD close and prints the book WITHOUT persisting. Pass --commit to actually set
inception (writes paper_account/paper_position/paper_equity_curve). Inception is
once-only and is meant to run on the always-on cloud infra, not casually.

Score source = mechanical composite (the validated F+ signal). NO LOOKAHEAD: the
book is built from data <= as_of only.

Usage:
    python -m scripts.paper_inception                 # dry-run, latest price date
    python -m scripts.paper_inception --as-of 2026-05-26
    python -m scripts.paper_inception --commit        # GO LIVE (cloud only)
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import date

from sqlalchemy import bindparam, text

from backend.db.session import SessionLocal
from backend.paper import engine as E

_LATEST = text("SELECT MAX(trade_date) FROM prices_eod_adjusted")
_SYMS = text(
    "SELECT isin, nse_symbol FROM stocks WHERE isin = ANY(:isins)"
).bindparams(bindparam("isins"))


async def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="F+ paper inception (Rs 10L).")
    p.add_argument("--as-of", default=None, help="YYYY-MM-DD (default: latest price date)")
    p.add_argument("--commit", action="store_true", help="persist inception (GO LIVE)")
    args = p.parse_args(argv)

    async with SessionLocal() as s:
        as_of = (
            date.fromisoformat(args.as_of) if args.as_of
            else (await s.execute(_LATEST)).scalar_one()
        )
        res = await E.inception(s, as_of, dry_run=not args.commit)
        syms = {i: sym for i, sym in (await s.execute(
            _SYMS, {"isins": [r["isin"] for r in res["rows"]]})).all()}

    mode = "COMMITTED (LIVE)" if args.commit else "DRY-RUN (preview, not persisted)"
    print(f"\n=== F+ PAPER INCEPTION — {mode} ===")
    print(f"as_of (EOD close): {res['as_of']}   |   engine: Enhanced F+ commit 6ced078 "
          f"(vol-adj momentum + 6.5% cash yield, mechanical composite)")
    print(f"capital Rs {E.STARTING_CAPITAL:,.0f}   regime exposure: {res['exposure']}"
          f"   scoreable universe: {res['scoreable']}")
    print(f"invested Rs {res['invested']:,.0f}   cash Rs {res['cash']:,.0f}   "
          f"names: {res['n']}\n")
    print(f"{'#':>2} {'symbol':<12}{'sector':<18}{'entryRs':>10}{'shares':>10}{'valueRs':>11}")
    for i, r in enumerate(sorted(res["rows"], key=lambda x: -x["value"]), 1):
        print(f"{i:>2} {syms.get(r['isin'], r['isin']):<12}{r['sector']:<18}"
              f"{float(r['px']):>10.2f}{float(r['shares']):>10.2f}{float(r['value']):>11.0f}")
    if not args.commit:
        print("\n(DRY-RUN — nothing written. Re-run with --commit on cloud to go live.)")


if __name__ == "__main__":
    asyncio.run(main())
