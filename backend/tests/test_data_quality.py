"""Tests for the Data Quality Agent's pure check logic (Chunk 1.4).

The detection predicates, gap finder, staleness rule, and finding builders
are pure — unit tested here. The SQL fetches + writes are exercised by the
live `quality run`.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from backend.agents.data_quality import (
    Finding,
    find_price_gaps,
    gap_finding,
    is_nonpositive,
    is_ohlc_violation,
    is_stale,
    nonpositive_finding,
    ohlc_finding,
    stale_finding,
    volume_finding,
)

D = Decimal


# ---------------------------------------------------------------------------
# 1-4. Price gap detection (internal gaps only; bounded to [min,max] present)
# ---------------------------------------------------------------------------
def test_find_price_gaps_internal() -> None:
    opens = [date(2024, 1, d) for d in (1, 2, 3, 4, 5)]
    present = {date(2024, 1, 1), date(2024, 1, 3), date(2024, 1, 5)}
    assert find_price_gaps(opens, present) == [date(2024, 1, 2), date(2024, 1, 4)]


def test_find_price_gaps_none_present() -> None:
    opens = [date(2024, 1, 1), date(2024, 1, 2)]
    assert find_price_gaps(opens, set()) == []


def test_find_price_gaps_no_gaps() -> None:
    opens = [date(2024, 1, 1), date(2024, 1, 2)]
    present = {date(2024, 1, 1), date(2024, 1, 2)}
    assert find_price_gaps(opens, present) == []


def test_find_price_gaps_ignores_pre_listing_and_trailing() -> None:
    # open days span more than the stock's presence window; only the internal
    # missing day (Jan 3) is a gap — Jan 1 (pre) and Jan 5 (trailing) are not.
    opens = [date(2024, 1, d) for d in (1, 2, 3, 4, 5)]
    present = {date(2024, 1, 2), date(2024, 1, 4)}
    assert find_price_gaps(opens, present) == [date(2024, 1, 3)]


# ---------------------------------------------------------------------------
# 5. Staleness — stale when days_since_last >= threshold (default 30).
# ---------------------------------------------------------------------------
def test_is_stale() -> None:
    ref = date(2026, 5, 25)
    assert is_stale(None, ref) is True  # never priced
    assert is_stale(date(2026, 1, 1), ref) is True  # ~144 days
    assert is_stale(date(2026, 5, 20), ref) is False  # 5 days
    assert is_stale(date(2026, 4, 24), ref) is True  # 31 days


def test_is_stale_boundary() -> None:
    ref = date(2026, 5, 25)
    assert is_stale(date(2026, 4, 25), ref, threshold_days=30) is True  # exactly 30
    assert is_stale(date(2026, 4, 26), ref, threshold_days=30) is False  # 29


# ---------------------------------------------------------------------------
# 6. OHLC + nonpositive predicates
# ---------------------------------------------------------------------------
def test_is_ohlc_violation() -> None:
    assert is_ohlc_violation(D("100"), D("90"), D("95"), D("92")) is True  # low>high
    assert is_ohlc_violation(D("100"), D("110"), D("95"), D("120")) is True  # close>high
    assert is_ohlc_violation(D("100"), D("110"), D("95"), D("90")) is True  # close<low
    assert is_ohlc_violation(D("100"), D("110"), D("95"), D("105")) is False
    assert is_ohlc_violation(None, None, None, None) is False  # null-safe


def test_is_nonpositive() -> None:
    assert is_nonpositive(D("100"), D("110"), D("0"), D("105")) is True
    assert is_nonpositive(D("-1"), D("110"), D("95"), D("105")) is True
    assert is_nonpositive(D("100"), D("110"), D("95"), D("105")) is False
    assert is_nonpositive(D("100"), None, D("95"), D("105")) is False  # null skipped


# ---------------------------------------------------------------------------
# 7. Finding builders carry the right severity + code (data_quality_log contract)
# ---------------------------------------------------------------------------
def test_gap_finding() -> None:
    f = gap_finding("INE001A01010", [date(2024, 1, 2), date(2024, 1, 4)])
    assert isinstance(f, Finding)
    assert f.severity == "warn"
    assert f.code == "PRICE_GAP"
    assert f.isin == "INE001A01010"
    assert f.context["gap_count"] == 2


def test_ohlc_finding_is_error() -> None:
    f = ohlc_finding(
        "INE001A01010", [{"trade_date": "2024-01-02", "high": "90", "low": "95"}]
    )
    assert f.severity == "error"
    assert f.code == "OHLC_VIOLATION"
    assert f.context["count"] == 1


def test_nonpositive_finding_is_error() -> None:
    f = nonpositive_finding(
        "INE001A01010", [{"trade_date": "2024-01-02", "close": "0"}]
    )
    assert f.severity == "error"
    assert f.code == "ZERO_NEGATIVE_PRICE"


def test_volume_finding_is_warn() -> None:
    f = volume_finding("INE001A01010", [date(2024, 1, 2), date(2024, 1, 3)])
    assert f.severity == "warn"
    assert f.code == "VOLUME_ZERO"
    assert f.context["count"] == 2


def test_stale_finding_is_warn() -> None:
    f = stale_finding("INE001A01010", date(2026, 1, 1), date(2026, 5, 25))
    assert f.severity == "warn"
    assert f.code == "STALE_UNIVERSE"
    assert f.context["last_price_date"] == "2026-01-01"
    assert f.context["days_stale"] > 30
