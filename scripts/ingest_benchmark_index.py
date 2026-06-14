#!/usr/bin/env python
"""Ingest a published benchmark index CSV into `benchmark_index` (Chunk 5.2c).

Real index data (Nifty 500 TRI) — not a proxy, no current-mcap lookahead. Parses
via `backend.data_sources.benchmark_csv.parse_tri_csv` (handles BOM, MM/DD/YYYY,
thousands commas, newest-first) and upserts `ON CONFLICT (index_name, trade_date)
DO NOTHING`. Reports coverage + value range for a sanity check.

Usage:
    python -m scripts.ingest_benchmark_index [--file PATH] [--name nifty500_tri]
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import text

from backend.data_sources.benchmark_csv import parse_tri_csv
from backend.db.session import SessionLocal

log = structlog.get_logger()

_DEFAULT_FILE = "data/benchmarks/nifty500_tri.csv"

_INSERT = text(
    """
    INSERT INTO benchmark_index (index_name, trade_date, index_value, source)
    VALUES (:index_name, :trade_date, :index_value, :source)
    ON CONFLICT (index_name, trade_date) DO NOTHING
    """
)
_VERIFY = text(
    """
    SELECT count(*) AS rows, min(trade_date) AS oldest, max(trade_date) AS newest,
           min(index_value) AS min_val, max(index_value) AS max_val
    FROM benchmark_index WHERE index_name = :name
    """
)


def _read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8-sig")


async def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Ingest a benchmark index CSV.")
    parser.add_argument("--file", default=_DEFAULT_FILE)
    parser.add_argument("--name", default="nifty500_tri")
    parser.add_argument("--source", default="investing")
    args = parser.parse_args(argv)

    text_content = await asyncio.to_thread(_read_text, args.file)
    rows = parse_tri_csv(text_content)
    log.info("benchmark.parsed", file=args.file, name=args.name, rows=len(rows))
    if not rows:
        print("No rows parsed — aborting (nothing written).")
        return

    payload: list[dict[str, Any]] = [
        {"index_name": args.name, "trade_date": d, "index_value": v,
         "source": args.source}
        for d, v in rows
    ]
    async with SessionLocal() as session:
        for i in range(0, len(payload), 2000):
            await session.execute(_INSERT, payload[i : i + 2000])
        await session.commit()
        v = (await session.execute(_VERIFY, {"name": args.name})).first()

    n_rows, oldest, newest, min_val, max_val = v
    pct = (float(max_val) / float(min_val) - 1.0) * 100 if min_val else 0.0
    log.info("benchmark.done", name=args.name, stored=n_rows)
    print(
        f"Done. {args.name}: {n_rows} rows, {oldest} -> {newest}, "
        f"value {min_val} -> {max_val} (min->max span {pct:.1f}%)."
    )


if __name__ == "__main__":
    asyncio.run(main())
