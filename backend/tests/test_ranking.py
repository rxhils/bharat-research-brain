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
# fundamental_score — Chunk 4.8 extension signals (fcf / quarterly / div / icr)
# ---------------------------------------------------------------------------
def test_fundamental_4arg_form_unchanged() -> None:
    # backwards-compat: the original 4-arg construction yields the original score
    f = FundInputs(
        Decimal("22.89"), Decimal("0.0914"), Decimal("36.65"), Decimal("0.125")
    )
    assert score_fundamental(f) == Decimal("85")


def test_fundamental_fcf_negative_penalty() -> None:
    # base 50, valuation all None, fcf_positive False -> -10 => 40
    f = FundInputs(None, None, None, None, fcf_positive=False)
    assert score_fundamental(f) == Decimal("40")


def test_fundamental_fcf_positive_bonus() -> None:
    # base 50 + fcf_positive True (+5) => 55
    f = FundInputs(None, None, None, None, fcf_positive=True)
    assert score_fundamental(f) == Decimal("55")


def test_fundamental_profit_direction_adjustments() -> None:
    improving = FundInputs(None, None, None, None, q_profit_direction="improving")
    declining = FundInputs(None, None, None, None, q_profit_direction="declining")
    stable = FundInputs(None, None, None, None, q_profit_direction="stable")
    assert score_fundamental(improving) == Decimal("58")  # +8
    assert score_fundamental(declining) == Decimal("42")  # -8
    assert score_fundamental(stable) == Decimal("50")  # no change


def test_fundamental_dividend_stability_bonus() -> None:
    # >= 5 consecutive years -> +5; 4 years -> no change
    assert score_fundamental(
        FundInputs(None, None, None, None, dividend_consecutive_years=5)
    ) == Decimal("55")
    assert score_fundamental(
        FundInputs(None, None, None, None, dividend_consecutive_years=4)
    ) == Decimal("50")


def test_fundamental_interest_coverage_penalty() -> None:
    # icr < 2.0 -> -10; exactly 2.0 -> no penalty (not strictly <)
    assert score_fundamental(
        FundInputs(None, None, None, None, interest_coverage=Decimal("1.5"))
    ) == Decimal("40")
    assert score_fundamental(
        FundInputs(None, None, None, None, interest_coverage=Decimal("2.0"))
    ) == Decimal("50")


def test_fundamental_new_signals_combine_and_clamp() -> None:
    # reliance-like 85 + fcf+5 + improving+8 + div+5 = 103 -> clamp 100
    f = FundInputs(
        Decimal("22.89"),
        Decimal("0.0914"),
        Decimal("36.65"),
        Decimal("0.125"),
        fcf_positive=True,
        q_profit_direction="improving",
        dividend_consecutive_years=7,
    )
    assert score_fundamental(f) == Decimal("100")


# ---------------------------------------------------------------------------
# technical_score — Chunk 4.9: 52-week proximity + volume trend
# ---------------------------------------------------------------------------
def _flat_tech(rsi: Decimal, **kw: object) -> TechInputs:
    """RSI with no EMA/cross/MACD adjustment, plus any 4.9 kwargs."""
    return TechInputs(rsi, "at", "none", Decimal("0"), **kw)  # type: ignore[arg-type]


def test_technical_4arg_form_unchanged() -> None:
    # rsi 60 -> 70; above +15; golden +10; macd>0 +5 = 100
    t = TechInputs(Decimal("60"), "above", "golden", Decimal("1.2"))
    assert score_technical(t) == Decimal("100")


def test_technical_near_high_momentum() -> None:
    # rsi 60 zone -> 70; within 3% of 52w high AND rsi in 55-70 -> +8 = 78
    t = _flat_tech(
        Decimal("60"),
        fifty_two_week_high=Decimal("100"),
        current_price=Decimal("98"),
    )
    assert score_technical(t) == Decimal("78")


def test_technical_near_high_extended() -> None:
    # rsi 75 zone -> 30; within 3% of high AND rsi > 70 -> +3 = 33
    t = _flat_tech(
        Decimal("75"),
        fifty_two_week_high=Decimal("100"),
        current_price=Decimal("99"),
    )
    assert score_technical(t) == Decimal("33")


def test_technical_near_low_penalty() -> None:
    # rsi 50 zone -> 50; within 5% of 52w low -> -8 = 42
    t = _flat_tech(
        Decimal("50"),
        fifty_two_week_low=Decimal("100"),
        current_price=Decimal("103"),
    )
    assert score_technical(t) == Decimal("42")


def test_technical_volume_strong_conviction() -> None:
    # rsi 50 -> 50; vol 3x -> +10 = 60
    t = _flat_tech(
        Decimal("50"), current_volume=3_000_000, avg_volume_30d=1_000_000
    )
    assert score_technical(t) == Decimal("60")


def test_technical_volume_above_average() -> None:
    # vol 1.5x -> +5 = 55
    t = _flat_tech(
        Decimal("50"), current_volume=1_500_000, avg_volume_30d=1_000_000
    )
    assert score_technical(t) == Decimal("55")


def test_technical_volume_low_conviction() -> None:
    # vol 0.5x -> -5 = 45
    t = _flat_tech(
        Decimal("50"), current_volume=500_000, avg_volume_30d=1_000_000
    )
    assert score_technical(t) == Decimal("45")


# ---------------------------------------------------------------------------
# technical_score — Build D: delivery % (accumulation proxy)
# ---------------------------------------------------------------------------
def test_technical_delivery_strong_conviction() -> None:
    # rsi 50 -> 50; delivery 75 (>=70) -> +8 = 58
    t = _flat_tech(Decimal("50"), delivery_pct=Decimal("75"))
    assert score_technical(t) == Decimal("58")


def test_technical_delivery_above_average() -> None:
    # rsi 50 -> 50; delivery 60 (>=55, <70) -> +4 = 54
    t = _flat_tech(Decimal("50"), delivery_pct=Decimal("60"))
    assert score_technical(t) == Decimal("54")


def test_technical_delivery_speculative_churn() -> None:
    # rsi 50 -> 50; delivery 15 (<=20) -> -5 = 45
    t = _flat_tech(Decimal("50"), delivery_pct=Decimal("15"))
    assert score_technical(t) == Decimal("45")


def test_technical_delivery_none_no_change() -> None:
    # delivery None -> no change; rsi 50 -> 50 (backward compat)
    t = _flat_tech(Decimal("50"), delivery_pct=None)
    assert score_technical(t) == Decimal("50")


def test_technical_delivery_sustained_accumulation_bonus() -> None:
    # rsi 50 -> 50; delivery 72 (>=70) +8; avg_5d 65 & delivery >=60 -> +3 = 61
    t = _flat_tech(
        Decimal("50"),
        delivery_pct=Decimal("72"),
        avg_5d_delivery_pct=Decimal("65"),
    )
    assert score_technical(t) == Decimal("61")


def test_technical_delivery_bonus_needs_both_avg_and_pct() -> None:
    # avg_5d 65 but delivery 50 (<60) -> tier none + no bonus; rsi 50 -> 50
    t = _flat_tech(
        Decimal("50"),
        delivery_pct=Decimal("50"),
        avg_5d_delivery_pct=Decimal("65"),
    )
    assert score_technical(t) == Decimal("50")


# ---------------------------------------------------------------------------
# fundamental_score — Chunk 4.9: sector-relative PE (with absolute fallback)
# ---------------------------------------------------------------------------
def test_fundamental_sector_pe_cheap() -> None:
    # pe 10 vs sector median 20 -> rel 0.5 < 0.7 -> +20 = 70
    f = FundInputs(Decimal("10"), None, None, None, sector_median_pe=Decimal("20"))
    assert score_fundamental(f) == Decimal("70")


def test_fundamental_sector_pe_slight_discount() -> None:
    # pe 16 / 20 = 0.8 -> +10 = 60
    f = FundInputs(Decimal("16"), None, None, None, sector_median_pe=Decimal("20"))
    assert score_fundamental(f) == Decimal("60")


def test_fundamental_sector_pe_fair() -> None:
    # pe 20 / 20 = 1.0 -> 0 = 50
    f = FundInputs(Decimal("20"), None, None, None, sector_median_pe=Decimal("20"))
    assert score_fundamental(f) == Decimal("50")


def test_fundamental_sector_pe_slight_premium() -> None:
    # pe 24 / 20 = 1.2 -> -5 = 45
    f = FundInputs(Decimal("24"), None, None, None, sector_median_pe=Decimal("20"))
    assert score_fundamental(f) == Decimal("45")


def test_fundamental_sector_pe_expensive() -> None:
    # pe 30 / 20 = 1.5 > 1.3 -> -10 = 40
    f = FundInputs(Decimal("30"), None, None, None, sector_median_pe=Decimal("20"))
    assert score_fundamental(f) == Decimal("40")


def test_fundamental_absolute_pe_fallback_when_no_sector() -> None:
    # no sector median -> absolute thresholds: pe 10 < 15 -> +20 = 70
    f = FundInputs(Decimal("10"), None, None, None)
    assert score_fundamental(f) == Decimal("70")


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
