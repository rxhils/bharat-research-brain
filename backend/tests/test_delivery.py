"""Tests for the Delivery-% Agent parser (Build D) — pure, synthetic CSV only.

Company-name -> ISIN matching is a DB concern (pg_trgm) and is exercised live, not
here. These cover the pure `parse_delivery_csv`: Decimal delivery_pct, tolerant
columns, and graceful skipping of bad/blank rows (never raises).
"""
from __future__ import annotations

from decimal import Decimal

from backend.agents.delivery import parse_delivery_csv

_HEADER = "Company name,Dely%,5-Day Avg Del%,Delivery Volumes,Traded Volumes\n"


def test_parse_delivery_basic() -> None:
    csv_text = _HEADER + (
        'Reliance Industries Ltd,45.32,42.10,"1,00,000","2,20,000"\n'
        'Tata Consultancy Services,67.80,65.00,"50,000","75,000"\n'
    )
    rows = parse_delivery_csv(csv_text)
    assert len(rows) == 2
    assert rows[0].company_name == "Reliance Industries Ltd"
    assert rows[0].delivery_pct == Decimal("45.32")
    assert rows[0].avg_5d_delivery_pct == Decimal("42.10")
    assert rows[0].delivery_volume == 100000
    assert rows[0].traded_volume == 220000


def test_delivery_pct_is_decimal() -> None:
    rows = parse_delivery_csv(_HEADER + "Some Co,12.5,,,\n")
    assert isinstance(rows[0].delivery_pct, Decimal)
    assert rows[0].delivery_pct == Decimal("12.5")
    assert rows[0].avg_5d_delivery_pct is None
    assert rows[0].delivery_volume is None


def test_percent_sign_tolerated() -> None:
    rows = parse_delivery_csv(_HEADER + "Pct Co,45.32%,,,\n")
    assert rows[0].delivery_pct == Decimal("45.32")


def test_blank_pct_skipped_not_crashed() -> None:
    assert parse_delivery_csv(_HEADER + "Bad Co,,,,\n") == []


def test_missing_company_skipped() -> None:
    assert parse_delivery_csv(_HEADER + ",45.0,,,\n") == []
