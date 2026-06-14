"""Parser for the published Nifty 500 TRI CSV (investing.com export).

Real index data — NOT a proxy — so it carries no current-mcap lookahead. The
export quirks (handled here): UTF-8 BOM on the header, quoted fields, AMERICAN
MM/DD/YYYY dates (06/12/2026 = 12 June, not 6 Dec), thousands commas in values,
and newest-first ordering. We use the `Price` column (the TRI close;
Open/High/Low are identical in this source).
"""
from __future__ import annotations

import csv
import io
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


def parse_tri_csv(text: str) -> list[tuple[date, Decimal]]:
    """Parse TRI CSV text into `(trade_date, index_value)` sorted ascending.

    Tolerant of the BOM, quotes, MM/DD/YYYY dates, and thousands commas. Blank
    or unparseable rows are skipped (never fabricated).
    """
    out: list[tuple[date, Decimal]] = []
    for row in csv.DictReader(io.StringIO(text)):
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
            d = datetime.strptime(d_raw.strip(), "%m/%d/%Y").date()  # month-first
            val = Decimal(p_raw.strip().replace(",", ""))
        except (ValueError, InvalidOperation):
            continue
        out.append((d, val))
    out.sort(key=lambda x: x[0])
    return out
