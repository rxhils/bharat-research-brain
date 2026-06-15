#!/usr/bin/env python
"""Connectivity + data smoke-test for the configured Postgres (POSTGRES_URL).

Point POSTGRES_URL at the hosted DB (Neon/Supabase) and run this to confirm the
forward system can reach it AND that the data the paper engine needs is present.
Read-only. Exits non-zero if connectivity fails or a required table is empty.

Usage:  python -m scripts.test_hosted_db
"""
from __future__ import annotations

import asyncio
import sys

from sqlalchemy import text

from backend.db.session import SessionLocal

# table -> minimum rows the forward engine needs to function
_REQUIRED = {
    "stocks": 1,
    "prices_eod_adjusted": 1,
    "benchmark_index": 1,
    "stock_rankings": 0,        # 0 = optional (agent snapshot; mechanical path ok empty)
    "paper_account": 0,         # 0 until inception is committed
    "paper_equity_curve": 0,
}


async def main() -> None:
    ok = True
    async with SessionLocal() as s:
        ver = (await s.execute(text("SELECT version()"))).scalar_one()
        print(f"connected: {ver.split(',')[0]}")
        maxd = (await s.execute(
            text("SELECT MAX(trade_date) FROM prices_eod_adjusted"))).scalar()
        print(f"latest EOD price date: {maxd}")
        for tbl, minimum in _REQUIRED.items():
            try:
                n = (await s.execute(text(f"SELECT COUNT(*) FROM {tbl}"))).scalar_one()
            except Exception as exc:  # noqa: BLE001 - smoke test surfaces any failure
                print(f"  FAIL {tbl}: {type(exc).__name__}: {exc}")
                ok = False
                continue
            flag = "OK " if n >= minimum else "FAIL"
            if n < minimum:
                ok = False
            print(f"  {flag} {tbl}: {n} rows (min {minimum})")
    print("RESULT:", "PASS — hosted DB is ready" if ok else "FAIL — fix before go-live")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
