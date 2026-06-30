#!/usr/bin/env python
"""Ingest the Nifty Financial Services index CSV (investing.com export) into
`benchmark_index` as `niftyfin_pr`.

IMPORTANT — this is the PRICE-return index (ex-dividends), NOT a Total Return
index: investing.com only publishes the sector PRICE series. Stored as
`niftyfin_pr` (the `_pr` suffix flags it) so no one mistakes it for a TRI. It is
a slightly EASIER bar than a TRI (missing ~1-1.5%/yr of dividends) — declare that
in any sector report.

This file's export quirks differ from the Nifty-500 TRI file: dates are
DAY-FIRST `DD-MM-YYYY` (25-06-2026 = 25 June), with thousands commas and
newest-first ordering. (The shared `parse_tri_csv` is MONTH-FIRST, so it can't be
reused here — a dedicated day-first parser lives below.)

Writes ONLY to the local `benchmark_index` table (additive, new index_name),
`ON CONFLICT (index_name, trade_date) DO NOTHING`. Touches nothing else.

Usage:
    python -m scripts.ingest_benchmark_financials [--file PATH] [--name niftyfin_pr]
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import io
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import text

from backend.db.session import SessionLocal

log = structlog.get_logger()

_DEFAULT_FILE = "C:/Users/fazea/Downloads/Nifty Financial Services Historical Data.csv"

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


def parse_dayfirst_csv(text_content: str) -> list[tuple[date, Decimal]]:
    """Parse the investing.com Financial Services CSV: DAY-FIRST `DD-MM-YYYY`
    dates, thousands commas, newest-first. Returns (trade_date, value) ascending.
    Unparseable/blank rows are skipped (never fabricated)."""
    out: list[tuple[date, Decimal]] = []
    for row in csv.DictReader(io.StringIO(text_content)):
        d_raw: str | None = None
        p_raw: str | None = None
        for key, value in row.items():
            norm = (key or "").lstrip("﻿").strip().strip('"').lower()
            if norm == "date":
                d_raw = value
            elif norm == "price":
                p_raw = value
        if not d_raw or not p_raw or not d_raw.strip() or not p_raw.strip():
            continue
        try:
            d = datetime.strptime(d_raw.strip(), "%d-%m-%Y").date()  # DAY-first
            val = Decimal(p_raw.strip().replace(",", ""))
        except (ValueError, InvalidOperation):
            continue
        out.append((d, val))
    out.sort(key=lambda x: x[0])
    return out


def _read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8-sig")


async def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Ingest Nifty Financial Services PR CSV.")
    parser.add_argument("--file", default=_DEFAULT_FILE)
    parser.add_argument("--name", default="niftyfin_pr")
    parser.add_argument("--source", default="investing_pr")
    args = parser.parse_args(argv)

    text_content = await asyncio.to_thread(_read_text, args.file)
    rows = parse_dayfirst_csv(text_content)
    log.info("benchmark_fin.parsed", file=args.file, name=args.name, rows=len(rows))
    if not rows:
        print("No rows parsed — aborting (nothing written). Check date format / file.")
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
    print(
        f"Done. {args.name}: {n_rows} rows, {oldest} -> {newest}, "
        f"value {min_val} -> {max_val}.  "
        f"(PRICE index, ex-dividends — soft bar; earliest date -> {oldest})"
    )


if __name__ == "__main__":
    asyncio.run(main())
