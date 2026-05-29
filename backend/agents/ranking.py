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

from dataclasses import dataclass, replace
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

# Sector-fair trailing PE (Chunk 4.11): the multiple the market normally awards
# a sector. A PE is scored by its ratio to this fair value, not in absolute
# terms — PE 25 is cheap for Pharma (fair 30) but expensive for Energy (fair 12).
# Keys must match `stocks.sector` labels. When a stock's sector is absent here,
# scoring falls back to the DB sector-median PE, then to absolute thresholds.
# Chunk 4.11b: keys are the EXACT active DB sector labels (SELECT DISTINCT
# sector FROM stocks WHERE delisted_on IS NULL, 19 rows, 2026-05-29) — no
# aliases, no dead keys. Every active sector maps so none falls through to the
# sector-median path. Fair-PE values reuse the original palette (the dead alias
# keys' multiples survive on their canonical label: Banking->Financials,
# Healthcare->Pharma, Technology->IT, Oil & Gas->Energy, Mining->Metals,
# Consumer->Consumer Services/Durables, Infra->Construction).
SECTOR_PE_FAIR: dict[str, Decimal] = {
    "Financials": Decimal("15"),
    "Capital Goods": Decimal("18"),
    "Pharma": Decimal("30"),
    "Auto": Decimal("20"),
    "Consumer Services": Decimal("38"),
    "FMCG": Decimal("40"),
    "IT": Decimal("25"),
    "Chemicals": Decimal("20"),
    "Construction": Decimal("18"),
    "Metals": Decimal("10"),
    "Energy": Decimal("12"),
    "Power": Decimal("12"),
    "Consumer Durables": Decimal("38"),
    "Services": Decimal("25"),
    "Realty": Decimal("25"),
    "Telecom": Decimal("25"),
    "Media": Decimal("20"),
    "Textiles": Decimal("18"),
    "Diversified": Decimal("20"),
}


@dataclass(frozen=True)
class TechInputs:
    rsi_14: Decimal | None
    price_vs_ema200: str | None
    ema_cross: str | None
    macd_hist: Decimal | None
    # Chunk 4.9 improvements 2+3 (default None keeps the original 4-arg form).
    fifty_two_week_high: Decimal | None = None
    fifty_two_week_low: Decimal | None = None
    current_price: Decimal | None = None
    current_volume: int | None = None
    avg_volume_30d: int | None = None
    # Build D wiring (default None keeps the original 4-arg form): delivery % is
    # an accumulation proxy — high delivery = lower intraday churn.
    delivery_pct: Decimal | None = None
    avg_5d_delivery_pct: Decimal | None = None
    # Chunk 4.10: VCP screen — a confirmed base near pivot earns a momentum bonus.
    vcp_detected: bool = False
    vcp_score: Decimal | None = None


@dataclass(frozen=True)
class DeliveryInputs:
    """Latest delivery snapshot per isin, carried from `fetch_delivery` into the
    stock's TechInputs in `run_all`."""

    isin: str
    delivery_pct: Decimal | None = None
    avg_5d_delivery_pct: Decimal | None = None


@dataclass(frozen=True)
class FundInputs:
    pe_ratio: Decimal | None
    roe: Decimal | None
    debt_to_equity: Decimal | None
    revenue_growth: Decimal | None
    # Chunk 4.8 extension signals (default None keeps the original 4-arg form).
    fcf_positive: bool | None = None
    q_profit_direction: str | None = None
    dividend_consecutive_years: int | None = None
    interest_coverage: Decimal | None = None
    # Chunk 4.9 improvement 4: sector median PE for relative valuation.
    sector_median_pe: Decimal | None = None
    # Chunk 4.11: sector label, keyed into SECTOR_PE_FAIR + sector_bonus.
    sector: str = ""


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

    # 52-week proximity (Chunk 4.9): momentum confirmation near the high,
    # value-trap flag near the low.
    if (
        t.current_price is not None
        and t.fifty_two_week_high
        and t.current_price / t.fifty_two_week_high >= Decimal("0.97")
    ):
        if t.rsi_14 is not None and Decimal("55") <= t.rsi_14 <= Decimal("70"):
            score += 8  # within 3% of high + healthy momentum
        elif t.rsi_14 is not None and t.rsi_14 > Decimal("70"):
            score += 3  # extended but still strong
    if (
        t.current_price is not None
        and t.fifty_two_week_low
        and t.current_price / t.fifty_two_week_low <= Decimal("1.05")
    ):
        score -= 8  # within 5% of 52w low

    # Volume trend (Chunk 4.9): conviction behind the move.
    if t.current_volume is not None and t.avg_volume_30d and t.avg_volume_30d > 0:
        vol_ratio = Decimal(t.current_volume) / Decimal(t.avg_volume_30d)
        if vol_ratio >= 3:
            score += 10
        elif vol_ratio >= Decimal("1.5"):
            score += 5
        elif vol_ratio <= Decimal("0.5"):
            score -= 5

    # Delivery % (Build D): high delivery = accumulation conviction, very low
    # delivery = speculative intraday churn. Tiers are mutually exclusive; the
    # 5-day-avg gate adds a bonus for sustained accumulation.
    if t.delivery_pct is not None:
        if t.delivery_pct >= 70:
            score += 8
        elif t.delivery_pct >= 55:
            score += 4
        elif t.delivery_pct <= 20:
            score -= 5
        if (
            t.avg_5d_delivery_pct is not None
            and t.avg_5d_delivery_pct >= 60
            and t.delivery_pct >= 60
        ):
            score += 3

    # VCP screen (Chunk 4.10): a confirmed contraction base near its pivot is a
    # momentum bonus — strong setups +10, developing setups +5.
    if t.vcp_detected and t.vcp_score is not None:
        if t.vcp_score >= 60:
            score += 10
        elif t.vcp_score >= 40:
            score += 5

    return _clamp(score)


def score_fundamental(f: FundInputs) -> Decimal:
    """Base 50 + PE/ROE/D-E/growth contributions, clamped 0-100.

    Inputs are raw yfinance units; converted to the formula's units here.
    """
    score = Decimal(50)

    if f.pe_ratio is not None:
        fair_pe = SECTOR_PE_FAIR.get(f.sector)
        if fair_pe is not None and fair_pe > 0:
            # Sector-fair PE (Chunk 4.11): ratio to the sector's normal multiple.
            ratio = f.pe_ratio / fair_pe
            if ratio < Decimal("0.7"):
                score += 20  # very cheap
            elif ratio < Decimal("0.9"):
                score += 12  # cheap
            elif ratio < Decimal("1.1"):
                score += 6  # fair value
            elif ratio < Decimal("1.3"):
                score += 0  # slightly rich
            else:
                score -= 8  # expensive
        elif f.sector_median_pe is not None and f.sector_median_pe > 0:
            # Sector-relative PE (Chunk 4.9): cheap/expensive vs sector peers.
            pe_relative = f.pe_ratio / f.sector_median_pe
            if pe_relative < Decimal("0.7"):
                score += 20
            elif pe_relative < Decimal("0.9"):
                score += 10
            elif pe_relative <= Decimal("1.1"):
                score += 0
            elif pe_relative <= Decimal("1.3"):
                score -= 5
            else:
                score -= 10
        else:
            # Fallback: absolute PE thresholds (no sector data available).
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

    # Chunk 4.8 extension signals — cash generation, profit trend, payout
    # stability, and debt-servicing risk.
    if f.fcf_positive is False:
        score -= 10  # burning cash
    elif f.fcf_positive is True:
        score += 5  # real cash generation

    if f.q_profit_direction == "improving":
        score += 8
    elif f.q_profit_direction == "declining":
        score -= 8

    if (
        f.dividend_consecutive_years is not None
        and f.dividend_consecutive_years >= 5
    ):
        score += 5  # payout stability

    if f.interest_coverage is not None and f.interest_coverage < Decimal("2.0"):
        score -= 10  # debt risk

    # Sector quality bonus (Chunk 4.11): reward the metric that matters most for
    # each sector (bank profitability, pharma/FMCG growth, IT returns).
    score += sector_bonus(f.sector, f.roe, f.revenue_growth)

    return _clamp(score)


def sector_bonus(
    sector: str, roe: Decimal | None, revenue_growth: Decimal | None
) -> Decimal:
    """Sector-specific quality bonus (Chunk 4.11, real-label keys 4.11b), 0-5 pts.

    `roe` and `revenue_growth` arrive as raw yfinance fractions (0.18 = 18%).
    Keys are exact active DB sector labels (no aliases). Financials: +5 if
    roe > 15%. IT: +5 if roe > 20%. Pharma: +5 if revenue_growth > 15%.
    FMCG / Consumer Services / Consumer Durables: +3 if revenue_growth > 10%.
    All other sectors: 0.
    """
    roe_pct = roe * 100 if roe is not None else None
    rg_pct = revenue_growth * 100 if revenue_growth is not None else None
    if sector == "Financials":
        return Decimal(5) if roe_pct is not None and roe_pct > 15 else Decimal(0)
    if sector == "IT":
        return Decimal(5) if roe_pct is not None and roe_pct > 20 else Decimal(0)
    if sector == "Pharma":
        return Decimal(5) if rg_pct is not None and rg_pct > 15 else Decimal(0)
    if sector in ("FMCG", "Consumer Services", "Consumer Durables"):
        return Decimal(3) if rg_pct is not None and rg_pct > 10 else Decimal(0)
    return Decimal(0)


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
        from backend.agents.risk import RiskAgent
        from backend.db.repositories import ranking as ranking_repo
        from backend.db.repositories import vcp as vcp_repo
        from backend.db.repositories._helpers import today_ist
        from backend.db.session import SessionLocal

        # Refresh risk signals first so earnings proximity (days_to_results) and
        # the other risk inputs are current in risk_signals before ranking reads
        # them via fetch_risk. dry_run propagates: no writes when previewing.
        await RiskAgent().run_all(dry_run=dry_run)

        async with SessionLocal() as session:
            isins = await ranking_repo.fetch_active_isins(session)
            tech = await ranking_repo.fetch_technicals(session)
            delivery = await ranking_repo.fetch_delivery(session)
            fund = await ranking_repo.fetch_fundamentals(session)
            risk = await ranking_repo.fetch_risk(session)
            sent = await ranking_repo.fetch_sentiment(session)
            sector_by_isin = await ranking_repo.fetch_sector_by_isin(session)
            fii_signal = await ranking_repo.fetch_fii_signal(session)
            regime = await ranking_repo.fetch_macro_regime(session)
            sector_medians = await ranking_repo.fetch_sector_medians(session)
            isin_sector = await ranking_repo.fetch_isin_sectors(session)
            vcp = await vcp_repo.fetch_latest(session)

        rows: list[RankingRow] = []
        for i in isins:
            tt = tech.get(i)
            t = TechInputs(*tt) if tt else TechInputs(None, None, None, None)
            d = delivery.get(i)
            if d is not None:
                di = DeliveryInputs(i, *d)
                t = replace(
                    t,
                    delivery_pct=di.delivery_pct,
                    avg_5d_delivery_pct=di.avg_5d_delivery_pct,
                )
            v = vcp.get(i)
            if v is not None:
                t = replace(
                    t, vcp_detected=v.vcp_detected, vcp_score=v.vcp_score
                )
            sec = isin_sector.get(i)
            sm = sector_medians.get(sec) if sec else None
            ff = fund.get(i)
            base_f = FundInputs(*ff) if ff else FundInputs(None, None, None, None)
            f = replace(
                base_f,
                sector=sec or "",
                sector_median_pe=sm.median_pe if sm else None,
            )
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
