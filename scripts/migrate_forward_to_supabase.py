#!/usr/bin/env python
"""Migrate ONLY the forward-needed data to a hosted Postgres (Supabase free tier).

The 1.06M historical price rows (≈523 MB, 96% of the local DB) are BACKTEST-only and
stay local. The 24/7 forward system needs only:
  - the last ~N trading days of prices_eod_adjusted (default 600 calendar days ≈ 400 td)
  - the composite-score inputs it reads: stocks, benchmark_index,
    {fundamental,macro,sector}_signals_historical, stock_rankings
  - small support tables: trading_calendar, index_constituents, stock_identifiers
  - the F+ paper portfolio state: paper_account/position/equity_curve/event_log
→ Total ≈ 50–80 MB, comfortably under the 500 MB free tier.

This copies DATA only. Create the schema on the target FIRST:  alembic upgrade head
(pointed at the target URL). Idempotent: every insert is ON CONFLICT DO NOTHING, so
re-running tops up missing rows without duplicating.

INFRA ONLY — does not import or touch the F+ engine. Read-only on the source.

Usage:
    # 1) Dry run (no target needed) — prints the plan + row counts + est. size
    python -m scripts.migrate_forward_to_supabase --dry-run

    # 2) Real migrate — target schema must already exist (alembic upgrade head)
    FORWARD_TARGET_URL='postgresql://USER:PASS@HOST:5432/postgres?sslmode=require' \
    FORWARD_SOURCE_URL='postgresql://bharat:PASS@localhost:5432/bharat' \
    python -m scripts.migrate_forward_to_supabase

Env:
    FORWARD_SOURCE_URL  source DB (default: backend settings.postgres_url, +asyncpg stripped)
    FORWARD_TARGET_URL  target DB (Supabase). Omit → dry run.
    FORWARD_PRICE_DAYS  calendar-day window for prices_eod_adjusted (default 600)
"""
from __future__ import annotations

import asyncio
import os
import sys

import asyncpg

# Forward-needed tables, in FK-safe insert order. prices_eod_adjusted is sliced by date;
# every other table is copied whole (all are small — KB to low MB).
PARENT_TABLES = [
    "stocks",
    "stock_identifiers",
    "trading_calendar",
    "index_constituents",
    "benchmark_index",
    "fundamental_signals_historical",
    "macro_signals_historical",
    "sector_signals_historical",
    "stock_rankings",
]
PRICE_TABLE = "prices_eod_adjusted"
PAPER_TABLES = [
    "paper_account",
    "paper_position",
    "paper_equity_curve",
    "paper_event_log",
]
BATCH = 5000


def _plain(url: str) -> str:
    """asyncpg wants a plain postgres URL (no +asyncpg, no sqlalchemy driver tag)."""
    return url.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgres+asyncpg://", "postgresql://"
    )


def _source_url() -> str:
    env = os.getenv("FORWARD_SOURCE_URL")
    if env:
        return _plain(env)
    # fall back to the backend's configured DB (local Docker)
    from backend.config import settings

    return _plain(settings.postgres_url)


async def _columns(conn: asyncpg.Connection, table: str) -> list[str]:
    rows = await conn.fetch(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name=$1 ORDER BY ordinal_position",
        table,
    )
    return [r["column_name"] for r in rows]


async def _exists(conn: asyncpg.Connection, table: str) -> bool:
    return bool(await conn.fetchval("SELECT to_regclass($1)", f"public.{table}"))


async def _copy_table(
    src: asyncpg.Connection,
    tgt: asyncpg.Connection,
    table: str,
    where: str = "",
) -> int:
    """Stream rows source→target with ON CONFLICT DO NOTHING. Returns rows sent."""
    cols = await _columns(src, table)
    if not cols:
        print(f"  ! {table}: no columns / missing on source — skipped")
        return 0
    collist = ", ".join(f'"{c}"' for c in cols)
    placeholders = ", ".join(f"${i + 1}" for i in range(len(cols)))
    insert_sql = (
        f'INSERT INTO "{table}" ({collist}) VALUES ({placeholders}) '
        f"ON CONFLICT DO NOTHING"
    )
    select_sql = f'SELECT {collist} FROM "{table}" {where}'

    read = 0
    async with src.transaction():
        cur = await src.cursor(select_sql)
        while True:
            recs = await cur.fetch(BATCH)
            if not recs:
                break
            rows = [tuple(r) for r in recs]
            read += len(rows)
            await tgt.executemany(insert_sql, rows)
            print(f"    {table}: {read} rows…", end="\r", flush=True)
    print(f"  ✓ {table}: {read} rows sent (ON CONFLICT DO NOTHING)            ")
    return read


async def _dry_run(src: asyncpg.Connection, price_days: int) -> None:
    print("\nDRY RUN - no target. Forward-data footprint that WOULD be migrated:\n")
    total_bytes = 0.0
    for t in PARENT_TABLES + PAPER_TABLES:
        if not await _exists(src, t):
            print(f"  {t:<34} (missing on source)")
            continue
        n = await src.fetchval(f'SELECT count(*) FROM "{t}"')
        b = await src.fetchval("SELECT pg_total_relation_size($1)", f"public.{t}")
        total_bytes += b or 0
        print(f"  {t:<34} {n:>10,} rows   {(b or 0) / 1e6:7.2f} MB")
    # priced slice
    maxd = await src.fetchval(f"SELECT max(trade_date) FROM {PRICE_TABLE}")
    n_all = await src.fetchval(f"SELECT count(*) FROM {PRICE_TABLE}")
    n_slice = await src.fetchval(
        f"SELECT count(*) FROM {PRICE_TABLE} WHERE trade_date >= $1::date - $2::int",
        maxd,
        price_days,
    )
    full_b = await src.fetchval("SELECT pg_total_relation_size($1)", f"public.{PRICE_TABLE}")
    est_slice_b = (full_b or 0) * (n_slice / n_all) if n_all else 0
    total_bytes += est_slice_b
    print(
        f"  {PRICE_TABLE:<34} {n_slice:>10,} rows   {est_slice_b / 1e6:7.2f} MB  "
        f"(of {n_all:,} total; last {price_days} days through {maxd})"
    )
    print(f"\n  {'TOTAL forward footprint':<34} {'':>10}   {total_bytes / 1e6:7.2f} MB")
    print(f"  Supabase free tier = 500 MB -> {'OK' if total_bytes < 500e6 else 'OVER (500MB)'}\n")
    print("Set FORWARD_TARGET_URL and re-run (without --dry-run) to migrate.")


async def main() -> None:
    price_days = int(os.getenv("FORWARD_PRICE_DAYS", "600"))
    dry = "--dry-run" in sys.argv
    src = await asyncpg.connect(_source_url())
    try:
        if dry or not os.getenv("FORWARD_TARGET_URL"):
            await _dry_run(src, price_days)
            return
        tgt = await asyncpg.connect(_plain(os.environ["FORWARD_TARGET_URL"]))
        try:
            print("\nMigrating forward data → target (idempotent)…\n")
            for t in PARENT_TABLES:
                if await _exists(src, t) and await _exists(tgt, t):
                    await _copy_table(src, tgt, t)
                else:
                    print(f"  ! {t}: missing on source or target — run alembic on target first")
            maxd = await src.fetchval(f"SELECT max(trade_date) FROM {PRICE_TABLE}")
            await _copy_table(
                src, tgt, PRICE_TABLE,
                where=f"WHERE trade_date >= '{maxd}'::date - {price_days}",
            )
            for t in PAPER_TABLES:
                if await _exists(src, t) and await _exists(tgt, t):
                    await _copy_table(src, tgt, t)
            sz = await tgt.fetchval(
                "SELECT pg_size_pretty(pg_database_size(current_database()))"
            )
            print(f"\nDone. Target DB size now: {sz}")
        finally:
            await tgt.close()
    finally:
        await src.close()


if __name__ == "__main__":
    asyncio.run(main())
