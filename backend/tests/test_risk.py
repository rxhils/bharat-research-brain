"""Tests for the Risk Agent (Chunk 4.2) — pure risk scoring, no DB.

`compute_risk` is a pure function over already-aggregated inputs (ATR%, news
counts, macro regime). All risk math is tested here with synthetic values.
"""
from __future__ import annotations

from decimal import Decimal

from backend.agents.risk import RiskRow, compute_risk


# ---------------------------------------------------------------------------
# volatility_flag
# ---------------------------------------------------------------------------
def test_flag_high() -> None:
    r = compute_risk("INE1", Decimal("4.5"), 0, Decimal("0"), "neutral")
    assert r.volatility_flag == "high"


def test_flag_medium() -> None:
    r = compute_risk("INE1", Decimal("3.0"), 0, Decimal("0"), "neutral")
    assert r.volatility_flag == "medium"


def test_flag_low() -> None:
    r = compute_risk("INE1", Decimal("0.8"), 0, Decimal("0"), "neutral")
    assert r.volatility_flag == "low"


def test_flag_low_when_atr_none() -> None:
    r = compute_risk("INE1", None, 0, Decimal("0"), "neutral")
    assert r.volatility_flag == "low"
    assert r.atr_pct is None


# ---------------------------------------------------------------------------
# news_spike
# ---------------------------------------------------------------------------
def test_news_spike_true() -> None:
    # 10 in 24h vs 2/day avg -> 10 > 6 and >= 3
    r = compute_risk("INE1", Decimal("1.5"), 10, Decimal("2"), "neutral")
    assert r.news_spike is True


def test_news_spike_false_below_min_count() -> None:
    # 2 > 3x0.1 but count < 3 -> no spike
    r = compute_risk("INE1", Decimal("1.5"), 2, Decimal("0.1"), "neutral")
    assert r.news_spike is False


def test_news_spike_false_not_3x() -> None:
    # 5 vs 3/day avg -> 5 not > 9
    r = compute_risk("INE1", Decimal("1.5"), 5, Decimal("3"), "neutral")
    assert r.news_spike is False


# ---------------------------------------------------------------------------
# risk_score
# ---------------------------------------------------------------------------
def test_score_base_neutral() -> None:
    # atr in [1,2] -> no band; no spike; neutral regime -> base 50
    r = compute_risk("INE1", Decimal("1.5"), 0, Decimal("0"), "neutral")
    assert r.risk_score == Decimal("50")
    assert r.days_to_results is None
    assert r.source == "risk_agent"


def test_score_high_vol_spike_riskoff_clamps_100() -> None:
    # 50 + 25 (atr>4) + 15 (spike) + 10 (risk-off) = 100
    r = compute_risk("INE1", Decimal("5.0"), 12, Decimal("2"), "risk-off")
    assert r.risk_score == Decimal("100")


def test_score_low_vol_stable() -> None:
    # 50 - 10 (atr<1) = 40
    r = compute_risk("INE1", Decimal("0.5"), 0, Decimal("0"), "risk-on")
    assert r.risk_score == Decimal("40")


def test_score_medium_vol_riskoff() -> None:
    # 50 + 10 (atr>2) + 10 (risk-off) = 70
    r = compute_risk("INE1", Decimal("3.0"), 0, Decimal("0"), "risk-off")
    assert r.risk_score == Decimal("70")


def test_score_returns_riskrow() -> None:
    r = compute_risk("INE002A01018", Decimal("2.5"), 0, Decimal("0"), "neutral")
    assert isinstance(r, RiskRow)
    assert r.isin == "INE002A01018"


# ---------------------------------------------------------------------------
# pledge risk flag raises risk_score (Chunk 4.9 improvement 5)
# ---------------------------------------------------------------------------
def test_pledge_critical_raises_20() -> None:
    # base 50 + critical 20 = 70
    r = compute_risk("INE1", Decimal("1.5"), 0, Decimal("0"), "neutral",
                     pledge_flag="critical")
    assert r.risk_score == Decimal("70")


def test_pledge_high_raises_10() -> None:
    r = compute_risk("INE1", Decimal("1.5"), 0, Decimal("0"), "neutral",
                     pledge_flag="high")
    assert r.risk_score == Decimal("60")


def test_pledge_moderate_raises_5() -> None:
    r = compute_risk("INE1", Decimal("1.5"), 0, Decimal("0"), "neutral",
                     pledge_flag="moderate")
    assert r.risk_score == Decimal("55")


def test_pledge_safe_and_none_no_change() -> None:
    assert compute_risk("INE1", Decimal("1.5"), 0, Decimal("0"), "neutral",
                        pledge_flag="safe").risk_score == Decimal("50")
    assert compute_risk("INE1", Decimal("1.5"), 0, Decimal("0"), "neutral",
                        pledge_flag=None).risk_score == Decimal("50")


def test_pledge_reclamps_to_100() -> None:
    # 50 + 25 (atr>4) + 15 (spike) + 10 (risk-off) + 20 (critical) -> clamp 100
    r = compute_risk("INE1", Decimal("5.0"), 12, Decimal("2"), "risk-off",
                     pledge_flag="critical")
    assert r.risk_score == Decimal("100")
