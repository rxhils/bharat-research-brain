"""Tests for the Ranking Agent (Chunk 4.3) — pure composite scoring, no DB.

`compute_score` and its component functions are pure. Fundamentals arrive in
raw yfinance units (roe/revenue_growth fractions, debt_to_equity percent); the
scorer converts them to the formula's percent/ratio units. Every formula step
and every label boundary is tested with synthetic inputs.
"""
from __future__ import annotations

from decimal import Decimal

from backend.agents.ranking import (
    FundInputs,
    MacroInputs,
    RankingRow,
    TechInputs,
    compute_score,
    risk_penalty,
    score_fundamental,
    score_macro,
    score_technical,
    sentiment_adjustment,
    signal_label,
)


# ---------------------------------------------------------------------------
# technical_score (RSI zone base + adjustments, clamp 0-100)
# ---------------------------------------------------------------------------
def test_technical_max_clamps_100() -> None:
    # rsi 60 -> zone 70; above +15; golden +10; macd>0 +5 = 100
    t = TechInputs(Decimal("60"), "above", "golden", Decimal("1.2"))
    assert score_technical(t) == Decimal("100")


def test_technical_min_clamps_0() -> None:
    # rsi 25 -> zone 20; below -10; death -10; macd<0 -5 = -5 -> 0
    t = TechInputs(Decimal("25"), "below", "death", Decimal("-0.4"))
    assert score_technical(t) == Decimal("0")


def test_technical_rsi_zones() -> None:
    flat = ("at", "none", Decimal("0"))
    assert score_technical(TechInputs(Decimal("28"), *flat)) == Decimal("20")
    assert score_technical(TechInputs(Decimal("40"), *flat)) == Decimal("40")
    assert score_technical(TechInputs(Decimal("50"), *flat)) == Decimal("50")
    assert score_technical(TechInputs(Decimal("60"), *flat)) == Decimal("70")
    assert score_technical(TechInputs(Decimal("70"), *flat)) == Decimal("60")
    assert score_technical(TechInputs(Decimal("80"), *flat)) == Decimal("30")


def test_technical_rsi_none_neutral_base() -> None:
    assert score_technical(TechInputs(None, None, None, None)) == Decimal("50")


# ---------------------------------------------------------------------------
# fundamental_score (base 50 + contributions, raw yfinance units)
# ---------------------------------------------------------------------------
def test_fundamental_reliance_like() -> None:
    # pe 22.89 -> +10; roe 0.0914 (9.1%) -> 0; d/e 36.65 (ratio 0.37) -> +15;
    # rev 0.125 (12.5%) -> +10 ; base 50 => 85
    f = FundInputs(
        Decimal("22.89"), Decimal("0.0914"), Decimal("36.65"), Decimal("0.125")
    )
    assert score_fundamental(f) == Decimal("85")


def test_fundamental_all_none_is_base() -> None:
    assert score_fundamental(FundInputs(None, None, None, None)) == Decimal("50")


def test_fundamental_strong() -> None:
    # pe 12 -> +20; roe 0.25 (25%) -> +25; d/e 30 (0.30 ratio) -> +15;
    # rev 0.30 (30%) -> +15; base 50 => 125 -> clamp 100
    f = FundInputs(Decimal("12"), Decimal("0.25"), Decimal("30"), Decimal("0.30"))
    assert score_fundamental(f) == Decimal("100")


def test_fundamental_weak() -> None:
    # pe 50 -> -10; roe 0.05 -> 0; d/e 200 (2.0 ratio) -> -10; rev -0.1 -> -5
    # base 50 => 25
    f = FundInputs(Decimal("50"), Decimal("0.05"), Decimal("200"), Decimal("-0.1"))
    assert score_fundamental(f) == Decimal("25")


# ---------------------------------------------------------------------------
# macro_score (base 50 + contributions)
# ---------------------------------------------------------------------------
def test_macro_strong() -> None:
    # strong_buy +20; leading +15; risk-on +10; base 50 => 95
    assert score_macro(MacroInputs("strong_buy", "leading", "risk-on")) == Decimal("95")


def test_macro_weak() -> None:
    # sell -10; lagging -15; risk-off -10; base 50 => 15
    assert score_macro(MacroInputs("sell", "lagging", "risk-off")) == Decimal("15")


def test_macro_none_is_base() -> None:
    assert score_macro(MacroInputs(None, None, None)) == Decimal("50")


# ---------------------------------------------------------------------------
# sentiment adjustment + risk penalty
# ---------------------------------------------------------------------------
def test_sentiment_adjustment() -> None:
    assert sentiment_adjustment(Decimal("0.8")) == Decimal("4.00")
    assert sentiment_adjustment(Decimal("-1")) == Decimal("-5.00")
    assert sentiment_adjustment(None) == Decimal("0")


def test_risk_penalty() -> None:
    # risk 85 -> (85-50)*0.15 = 5.25, +5 (>70) = 10.25
    assert risk_penalty(Decimal("85")) == Decimal("10.25")
    # risk 50 -> 0
    assert risk_penalty(Decimal("50")) == Decimal("0.00")
    # risk 30 -> (30-50)*0.15 = -3.00 (low-risk bonus)
    assert risk_penalty(Decimal("30")) == Decimal("-3.00")
    assert risk_penalty(None) == Decimal("0")


# ---------------------------------------------------------------------------
# signal_label boundaries
# ---------------------------------------------------------------------------
def test_signal_label_boundaries() -> None:
    assert signal_label(Decimal("75")) == "bullish-watch"
    assert signal_label(Decimal("74.99")) == "needs-confirmation"
    assert signal_label(Decimal("55")) == "needs-confirmation"
    assert signal_label(Decimal("54.99")) == "neutral"
    assert signal_label(Decimal("40")) == "neutral"
    assert signal_label(Decimal("39.99")) == "cautious"
    assert signal_label(Decimal("25")) == "cautious"
    assert signal_label(Decimal("24.99")) == "avoid"


# ---------------------------------------------------------------------------
# compute_score — full 5-step pipeline
# ---------------------------------------------------------------------------
def test_compute_score_end_to_end() -> None:
    tech = TechInputs(Decimal("60"), "above", "golden", Decimal("1.2"))  # 100
    fund = FundInputs(
        Decimal("22.89"), Decimal("0.0914"), Decimal("36.65"), Decimal("0.125")
    )  # 85
    macro = MacroInputs("buy", "neutral", "risk-off")  # 50 +10 +0 -10 = 50
    # raw = 85*0.40 + 100*0.35 + 50*0.25 = 34 + 35 + 12.5 = 81.5
    # sent 0.5 -> +2.5 -> 84.0 ; risk 60 -> (60-50)*0.15=1.5 penalty -> 82.5
    row = compute_score(
        "INE002A01018", tech, fund, macro, Decimal("0.5"), Decimal("60")
    )
    assert isinstance(row, RankingRow)
    assert row.fundamental_score == Decimal("85")
    assert row.technical_score == Decimal("100")
    assert row.macro_score == Decimal("50")
    assert row.sentiment_adj == Decimal("2.50")
    assert row.risk_penalty == Decimal("1.50")
    assert row.composite_score == Decimal("82.50")
    assert row.signal_label == "bullish-watch"
    assert row.score_breakdown["fundamental_score"] == 85.0


def test_compute_score_clamps_and_labels_low() -> None:
    tech = TechInputs(Decimal("25"), "below", "death", Decimal("-1"))  # 0
    fund = FundInputs(
        Decimal("50"), Decimal("0.05"), Decimal("200"), Decimal("-0.1")
    )  # 25
    macro = MacroInputs("strong_sell", "lagging", "risk-off")  # 50 -20 -15 -10 = 5
    # raw = 25*0.40 + 0*0.35 + 5*0.25 = 10 + 0 + 1.25 = 11.25 ; sent None -> 0
    # risk 90 -> (90-50)*0.15=6 +5 = 11 penalty -> 0.25
    row = compute_score("INEX", tech, fund, macro, None, Decimal("90"))
    assert row.composite_score == Decimal("0.25")
    assert row.signal_label == "avoid"
