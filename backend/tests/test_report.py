"""Tests for the Report Agent (Chunk 4.4, redesigned) — pure template, no LLM.

The report is now fully deterministic structured formatting from a
ReportContext — zero Ollama, zero hallucination. Every section is rendered from
DB-derived values. FII signals use flow language (inflow/outflow) so banned
advisory words never appear (CLAUDE.md §2 rule 2).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from backend.agents.report import (
    DISCLAIMER,
    ReportContext,
    StockCtx,
    assemble_report,
    macd_direction,
    macro_summary_line,
    regime_implication,
    word_count,
)


def _stock() -> StockCtx:
    return StockCtx(
        rank=1,
        isin="INE002A01018",
        symbol="RELIANCE",
        sector="Pharma",
        label="bullish-watch",
        composite=Decimal("82.25"),
        t_score=Decimal("90"),
        f_score=Decimal("100"),
        m_score=Decimal("55"),
        risk_penalty=Decimal("3.00"),
        volatility_flag="high",
        atr_pct=Decimal("4.50"),
        rsi=Decimal("60.0"),
        ema_cross="golden",
        vs_ema200="above",
        macd_hist=Decimal("1.20"),
        roe=Decimal("0.254"),
        de=Decimal("36.65"),
        pe=Decimal("22.89"),
        rev_growth=Decimal("0.125"),
        sector_signal="leading",
        sector_mom_7d=Decimal("2.04"),
        fii_signal="sell",
        ts_date=date(2026, 5, 22),
        fs_date=date(2026, 5, 26),
    )


def _ctx() -> ReportContext:
    return ReportContext(
        report_date=date(2026, 5, 26),
        generated_at_ist="14:30",
        regime="risk-off",
        nifty_value=Decimal("23913.70"),
        nifty_signal="falling",
        usd_inr=Decimal("95.24"),
        usd_signal="stable",
        crude_signal="falling",
        fii_5d_sum=None,  # no real FII data -> n/a, never fabricated
        fii_signal=None,
        top_stocks=[_stock()],
        leading_sectors=["Pharma"],
        lagging_sectors=["Metals", "IT"],
        neutral_sectors=["Auto"],
        risk_stocks=[("GESHIP", Decimal("85"), "high", Decimal("4.77"))],
        signal_distribution={
            "bullish-watch": 13,
            "needs-confirmation": 211,
            "neutral": 218,
            "cautious": 62,
            "avoid": 3,
        },
        fund_date=date(2026, 5, 26),
    )


def test_word_count() -> None:
    assert word_count("one two three") == 3
    assert word_count("") == 0


def test_regime_implication() -> None:
    assert regime_implication("risk-on") == "favour growth and momentum"
    assert regime_implication("risk-off") == "favour quality and defensives"
    assert regime_implication("neutral") == "selective — stock-specific signals"
    assert regime_implication("unknown") == "selective — stock-specific signals"


def test_macd_direction() -> None:
    assert macd_direction(Decimal("1.2")) == "positive"
    assert macd_direction(Decimal("-0.3")) == "negative"
    assert macd_direction(Decimal("0")) == "flat"
    assert macd_direction(None) == "flat"


def test_macro_summary_line() -> None:
    line = macro_summary_line(_ctx())
    assert "risk-off" in line
    assert "\n" not in line


def test_assemble_report_structure() -> None:
    md = assemble_report(_ctx())

    # Header + macro snapshot
    assert "# Daily research note — 2026-05-26" in md
    assert "Generated: 14:30 IST | Regime: risk-off" in md
    assert "## Macro snapshot" in md
    assert "Nifty 50:" in md and "23913.70" in md and "falling" in md
    assert "USD/INR:" in md and "95.24" in md and "stable" in md
    assert "FII 5d:    n/a" in md  # no fabrication
    assert "favour quality and defensives" in md  # risk-off implication

    # Stock block + component scores + unit conversions
    assert "### 1. RELIANCE (Pharma) — bullish-watch" in md
    assert "Score: 82.25/100 | Risk: high" in md
    assert "Technical  (90/100)" in md
    assert "RSI 60.0 · golden · above EMA200" in md
    assert "MACD histogram: positive" in md
    assert "Fundamental (100/100)" in md
    assert "ROE 25.4% · D/E 0.37x · PE 22.89x" in md  # 0.254->25.4%, 36.65->0.37
    assert "Revenue growth: 12.5%" in md
    assert "Macro      (55/100)" in md
    assert "Sector leading (2.04% 7d)" in md
    assert "Risk penalty: -3.00 pts" in md
    assert "ATR 4.50%" in md
    assert "Sources: technical_signals 2026-05-22" in md

    # Sector rotation (all three buckets)
    assert "## Sector rotation" in md
    assert "Leading:  Pharma" in md
    assert "Lagging:  Metals, IT" in md
    assert "Neutral:  Auto" in md

    # Risk flags
    assert "## Risk flags" in md
    assert "GESHIP" in md and "risk 85/100" in md

    # Signal distribution (all 5 labels)
    assert "## Signal distribution" in md
    assert "bullish-watch:      13 stocks" in md
    assert "neutral:            218 stocks" in md
    assert "avoid:              3 stocks" in md

    # Disclaimer
    assert DISCLAIMER in md
    assert "Not investment advice" in DISCLAIMER
    assert "SEBI" in DISCLAIMER


def test_assemble_report_no_advisory_language() -> None:
    md = assemble_report(_ctx()).lower()
    for banned in (" buy ", " sell ", "guaranteed", "sure-shot", "recommendation"):
        assert banned not in md
