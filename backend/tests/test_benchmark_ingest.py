"""Pure tests for the Nifty 500 TRI CSV parser (Chunk 5.2c benchmark)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from backend.data_sources.benchmark_csv import parse_tri_csv

# Mimics the real investing.com export: BOM header, quoted fields, MM/DD/YYYY
# dates, thousands commas, newest-first. Open/High/Low == Price in this source.
_SAMPLE = (
    '﻿"Date","Price","Open","High","Low","Vol.","Change %"\n'
    '"06/12/2026","36,193.53","36,193.53","36,193.53","36,193.53","","2.22%"\n'
    '"01/02/2024","24,580.35","24,580.35","24,580.35","24,580.35","","0.10%"\n'
    '"03/17/2021","18,720.14","18,720.14","18,720.14","18,720.14","","-1.54%"\n'
)


def test_parse_tri_dates_month_first_and_commas() -> None:
    rows = parse_tri_csv(_SAMPLE)
    assert len(rows) == 3
    # MM/DD/YYYY: 06/12/2026 is June 12 (month-first), NOT December 6.
    assert (date(2026, 6, 12), Decimal("36193.53")) in rows
    # thousands comma stripped, mid row parsed
    assert (date(2024, 1, 2), Decimal("24580.35")) in rows


def test_parse_tri_sorted_ascending() -> None:
    rows = parse_tri_csv(_SAMPLE)
    # input is newest-first; output must be ascending by date
    assert rows[0] == (date(2021, 3, 17), Decimal("18720.14"))
    assert rows[-1] == (date(2026, 6, 12), Decimal("36193.53"))
    assert [d for d, _ in rows] == sorted(d for d, _ in rows)


def test_parse_tri_skips_blank_rows() -> None:
    text = _SAMPLE + '"","","","","","",""\n'
    assert len(parse_tri_csv(text)) == 3
