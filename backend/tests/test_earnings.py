"""Tests for the Earnings-calendar Agent (Build E).

Pure `parse_earnings_csv` (synthetic CSV) + the Risk Agent's `days_to_results`
scoring. Company-name -> ISIN matching is a DB concern (pg_trgm), exercised live.

NOTE: Build E's prose rule is `<=2 -> +15, <=5 -> +10, <=10 -> +5`; its test bullet
"days=3 -> +15" contradicts that rule. We implement the rule (authoritative), so
days=3 falls in the `<=5` band (+10). Tested explicitly below.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from backend.agents.earnings import parse_earnings_csv
from backend.agents.risk import compute_risk

_HEADER = "Company Name,Result Date,Quarter\n"


def test_parse_earnings_basic() -> None:
    csv_text = _HEADER + (
        "Reliance Industries Ltd,28-May-2026,Q4 FY26\n"
        "Tata Consultancy Services,30-May-2026,Q4 FY26\n"
    )
    rows = parse_earnings_csv(csv_text)
    assert len(rows) == 2
    assert rows[0].company_name == "Reliance Industries Ltd"
    assert rows[0].result_date == date(2026, 5, 28)
    assert rows[0].quarter == "Q4 FY26"


def test_parse_earnings_date_formats() -> None:
    rows = parse_earnings_csv(_HEADER + "A Co,2026-06-15,\nB Co,15 Jun 2026,\n")
    assert rows[0].result_date == date(2026, 6, 15)
    assert rows[1].result_date == date(2026, 6, 15)
    assert rows[0].quarter is None


def test_bad_date_skipped_not_crashed() -> None:
    assert parse_earnings_csv(_HEADER + "Bad Co,not-a-date,Q1\n") == []


def _risk(days: int | None) -> Decimal:
    # base 50: atr None, no news spike, neutral regime, no pledge.
    return compute_risk(
        "INE000000000", None, 0, Decimal(0), "neutral", None, days
    ).risk_score


def test_risk_results_imminent_plus15() -> None:
    assert _risk(0) == Decimal(65)
    assert _risk(2) == Decimal(65)


def test_risk_results_day3_in_this_week_band_plus10() -> None:
    # Per the rule (<=2 -> +15), day 3 is in the <=5 band (+10), NOT +15.
    assert _risk(3) == Decimal(60)
    assert _risk(5) == Decimal(60)


def test_risk_results_fortnight_plus5() -> None:
    assert _risk(7) == Decimal(55)
    assert _risk(10) == Decimal(55)


def test_risk_results_far_no_change() -> None:
    assert _risk(20) == Decimal(50)
    assert _risk(11) == Decimal(50)


def test_risk_days_none_backward_compat() -> None:
    r = compute_risk("INE000000000", None, 0, Decimal(0), "neutral")
    assert r.risk_score == Decimal(50)
    assert r.days_to_results is None
