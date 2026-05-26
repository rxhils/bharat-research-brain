"""Ranking Agent (Chunk 4.3) — the composite morning score per stock.

Reads every signal table (technical, fundamental, sector, FII/DII, macro,
sentiment, risk) and produces a 0-100 composite score + a plain-English label
from the APPROVED vocabulary (CLAUDE.md §2 rule 2): bullish-watch /
needs-confirmation / neutral / cautious / avoid. Pure computation, no LLM, no
external calls.

UNIT NOTE: fundamentals are stored in raw yfinance units — `roe` and
`revenue_growth` are fractions (0.094 = 9.4%) and `debt_to_equity` is a percent
(36.65 = 0.37 ratio). The formula's thresholds are in percent (roe > 20%) and
ratio (d/e < 0.5), so `score_fundamental` converts: roe×100, revenue_growth×100,
debt_to_equity÷100, pe as-is.

`compute_score` + the component functions are pure (fully unit tested); only
`run_all` touches the DB.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal

import structlog

log = structlog.get_logger()

SOURCE = "ranking_agent"
_Q2 = Decimal("0.01")

# Composite weights.
_W_FUND = Decimal("0.40")
_W_TECH = Decimal("0.35")
_W_MACRO = Decimal("0.25")


@dataclass(frozen=True)
class TechInputs:
    rsi_14: Decimal | None
    price_vs_ema200: str | None
    ema_cross: str | None
    macd_hist: Decimal | None


@dataclass(frozen=True)
class FundInputs:
    pe_ratio: Decimal | None
    roe: Decimal | None
    debt_to_equity: Decimal | None
    revenue_growth: Decimal | None


@dataclass(frozen=True)
class MacroInputs:
    fii_signal: str | None
    sector_signal: str | None
    macro_regime: str | None


@dataclass(frozen=True)
class RankingRow:
    isin: str
    composite_score: Decimal
    signal_label: str
    fundamental_score: Decimal
    technical_score: Decimal
    macro_score: Decimal
    sentiment_adj: Decimal
    risk_penalty: Decimal
    score_breakdown: dict[str, object]
    source: str = SOURCE


def _clamp(
    value: Decimal, lo: Decimal = Decimal(0), hi: Decimal = Decimal(100)
) -> Decimal:
    return max(lo, min(hi, value))


def _q2(value: Decimal) -> Decimal:
    return value.quantize(_Q2, rounding=ROUND_HALF_EVEN)


# ---------------------------------------------------------------------------
# Component scores (pure)
# ---------------------------------------------------------------------------
def score_technical(t: TechInputs) -> Decimal:
    """RSI-zone base + EMA/cross/MACD adjustments, clamped 0-100."""
    if t.rsi_14 is None:
        score = Decimal(50)
    else:
        rsi = t.rsi_14
        if rsi < 30:
            score = Decimal(20)
        elif rsi < 45:
            score = Decimal(40)
        elif rsi < 55:
            score = Decimal(50)
        elif rsi < 65:
            score = Decimal(70)
        elif rsi < 75:
            score = Decimal(60)
        else:
            score = Decimal(30)

    if t.price_vs_ema200 == "above":
        score += 15
    elif t.price_vs_ema200 == "below":
        score -= 10

    if t.ema_cross == "golden":
        score += 10
    elif t.ema_cross == "death":
        score -= 10

    if t.macd_hist is not None:
        if t.macd_hist > 0:
            score += 5
        elif t.macd_hist < 0:
            score -= 5

    return _clamp(score)


def score_fundamental(f: FundInputs) -> Decimal:
    """Base 50 + PE/ROE/D-E/growth contributions, clamped 0-100.

    Inputs are raw yfinance units; converted to the formula's units here.
    """
    score = Decimal(50)

    if f.pe_ratio is not None:
        pe = f.pe_ratio
        if pe < 15:
            score += 20
        elif pe < 25:
            score += 10
        elif pe <= 40:
            score += 0
        else:
            score -= 10

    if f.roe is not None:
        roe_pct = f.roe * 100  # fraction -> percent
        if roe_pct > 20:
            score += 25
        elif roe_pct >= 15:
            score += 15
        elif roe_pct >= 10:
            score += 10

    if f.debt_to_equity is not None:
        de_ratio = f.debt_to_equity / 100  # yfinance percent -> ratio
        if de_ratio < Decimal("0.5"):
            score += 15
        elif de_ratio <= Decimal("1.5"):
            score += 5
        else:
            score -= 10

    if f.revenue_growth is not None:
        rg_pct = f.revenue_growth * 100  # fraction -> percent
        if rg_pct > 20:
            score += 15
        elif rg_pct >= 10:
            score += 10
        elif rg_pct >= 0:
            score += 5
        else:
            score -= 5

    return _clamp(score)


def score_macro(m: MacroInputs) -> Decimal:
    """Base 50 + FII / sector / regime contributions, clamped 0-100."""
    score = Decimal(50)
    score += {
        "strong_buy": 20,
        "buy": 10,
        "neutral": 0,
        "sell": -10,
        "strong_sell": -20,
    }.get(m.fii_signal or "", 0)
    score += {"leading": 15, "neutral": 0, "lagging": -15}.get(
        m.sector_signal or "", 0
    )
    score += {"risk-on": 10, "neutral": 0, "risk-off": -10}.get(
        m.macro_regime or "", 0
    )
    return _clamp(score)


def sentiment_adjustment(sentiment_score: Decimal | None) -> Decimal:
    """avg news sentiment (-1..+1) -> +/-5 modifier."""
    if sentiment_score is None:
        return Decimal(0)
    return _q2(sentiment_score * 5)


def risk_penalty(risk_score: Decimal | None) -> Decimal:
    """(risk_score - 50) * 0.15, +5 extra above 70. Negative = low-risk bonus."""
    if risk_score is None:
        return Decimal(0)
    penalty = (risk_score - 50) * Decimal("0.15")
    if risk_score > 70:
        penalty += 5
    return _q2(penalty)


def signal_label(score: Decimal) -> str:
    if score >= 75:
        return "bullish-watch"
    if score >= 55:
        return "needs-confirmation"
    if score >= 40:
        return "neutral"
    if score >= 25:
        return "cautious"
    return "avoid"


def compute_score(
    isin: str,
    tech: TechInputs,
    fund: FundInputs,
    macro: MacroInputs,
    sentiment_score: Decimal | None,
    risk_score: Decimal | None,
) -> RankingRow:
    """Full 5-step composite: components -> weighted -> sentiment -> risk -> clamp."""
    t_score = score_technical(tech)
    f_score = score_fundamental(fund)
    m_score = score_macro(macro)

    raw = f_score * _W_FUND + t_score * _W_TECH + m_score * _W_MACRO
    sent_adj = sentiment_adjustment(sentiment_score)
    penalty = risk_penalty(risk_score)
    composite = _clamp(_q2(raw + sent_adj - penalty))

    label = signal_label(composite)
    breakdown: dict[str, object] = {
        "technical_score": float(t_score),
        "fundamental_score": float(f_score),
        "macro_score": float(m_score),
        "weighted_raw": float(_q2(raw)),
        "sentiment_adj": float(sent_adj),
        "risk_penalty": float(penalty),
        "composite_score": float(composite),
        "weights": {"fundamental": 0.40, "technical": 0.35, "macro": 0.25},
    }
    return RankingRow(
        isin=isin,
        composite_score=composite,
        signal_label=label,
        fundamental_score=f_score,
        technical_score=t_score,
        macro_score=m_score,
        sentiment_adj=sent_adj,
        risk_penalty=penalty,
        score_breakdown=breakdown,
        source=SOURCE,
    )


class RankingAgent:
    name = "ranking"

    async def run_all(self, *, dry_run: bool = False) -> list[RankingRow]:
        from backend.db.repositories import ranking as ranking_repo
        from backend.db.repositories._helpers import today_ist
        from backend.db.session import SessionLocal

        async with SessionLocal() as session:
            isins = await ranking_repo.fetch_active_isins(session)
            tech = await ranking_repo.fetch_technicals(session)
            fund = await ranking_repo.fetch_fundamentals(session)
            risk = await ranking_repo.fetch_risk(session)
            sent = await ranking_repo.fetch_sentiment(session)
            sector_by_isin = await ranking_repo.fetch_sector_by_isin(session)
            fii_signal = await ranking_repo.fetch_fii_signal(session)
            regime = await ranking_repo.fetch_macro_regime(session)

        rows: list[RankingRow] = []
        for i in isins:
            tt = tech.get(i)
            t = TechInputs(*tt) if tt else TechInputs(None, None, None, None)
            ff = fund.get(i)
            f = FundInputs(*ff) if ff else FundInputs(None, None, None, None)
            m = MacroInputs(fii_signal, sector_by_isin.get(i), regime)
            rows.append(compute_score(i, t, f, m, sent.get(i), risk.get(i)))
        rows.sort(key=lambda r: r.composite_score, reverse=True)

        if not dry_run and rows:
            payload = [_to_dict(r, today_ist()) for r in rows]
            async with SessionLocal() as session:
                await ranking_repo.bulk_upsert(session, payload)
                await session.commit()

        log.info(
            "ranking.run.done",
            stocks=len(rows),
            regime=regime,
            dry_run=dry_run,
            bullish=sum(1 for r in rows if r.signal_label == "bullish-watch"),
        )
        return rows


def _to_dict(r: RankingRow, computed_date: date) -> dict[str, object]:
    return {
        "isin": r.isin,
        "computed_date": computed_date,
        "composite_score": r.composite_score,
        "signal_label": r.signal_label,
        "fundamental_score": r.fundamental_score,
        "technical_score": r.technical_score,
        "macro_score": r.macro_score,
        "sentiment_adj": r.sentiment_adj,
        "risk_penalty": r.risk_penalty,
        "score_breakdown": r.score_breakdown,
        "source": r.source,
    }
