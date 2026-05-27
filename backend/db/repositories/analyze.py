"""Read-only aggregation for the `analyze` CLI command (ticker deep-dive).

Pure data access — gathers the latest row from every signal table for one ISIN
into a flat `AnalysisData` value object. No writes, no external fetches. Every
field is optional: a stock with no rankings/technicals/etc. still resolves, and
the formatter renders "data pending" for missing pieces.

Latest-per-table is taken by `ORDER BY <date> DESC LIMIT 1` (not "today"), so the
command works regardless of the UTC/IST date boundary.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import (
    FiiDiiFlow,
    FundamentalSignal,
    MacroSignal,
    NewsArticle,
    PriceEod,
    PriceEodAdjusted,
    PromoterSignal,
    RiskSignal,
    SectorSignal,
    Stock,
    StockRanking,
    TechnicalSignal,
)


@dataclass(frozen=True)
class NewsItem:
    headline: str
    published_at: datetime | None
    sentiment_label: str | None


@dataclass(frozen=True)
class AnalysisData:
    # Header
    isin: str
    nse_symbol: str | None
    company_name: str
    sector: str | None
    industry: str | None
    mcap_category: str | None
    mcap_inr_cr: Decimal | None
    # Ranking
    composite_score: Decimal | None = None
    signal_label: str | None = None
    technical_score: Decimal | None = None
    fundamental_score: Decimal | None = None
    macro_score: Decimal | None = None
    sentiment_adj: Decimal | None = None
    risk_penalty: Decimal | None = None
    ranking_computed_date: date | None = None
    ranking_computed_at: datetime | None = None
    # Technical
    rsi_14: Decimal | None = None
    ema_cross: str | None = None
    price_vs_ema200: str | None = None
    macd_hist: Decimal | None = None
    current_price: Decimal | None = None
    current_volume: int | None = None
    avg_volume_30d: int | None = None
    fifty_two_week_high: Decimal | None = None
    fifty_two_week_low: Decimal | None = None
    # Fundamental
    pe_ratio: Decimal | None = None
    sector_median_pe: Decimal | None = None
    roe: Decimal | None = None
    debt_to_equity: Decimal | None = None
    revenue_growth: Decimal | None = None
    free_cash_flow: int | None = None
    fcf_positive: bool | None = None
    q_profit_direction: str | None = None
    dividend_consecutive_years: int | None = None
    interest_coverage: Decimal | None = None
    # Macro
    sector_signal: str | None = None
    sector_momentum_7d: Decimal | None = None
    fii_signal: str | None = None
    regime: str | None = None
    vix_value: Decimal | None = None
    vix_signal: str | None = None
    # Risk
    risk_score: Decimal | None = None
    volatility_flag: str | None = None
    atr_pct: Decimal | None = None
    news_spike: bool | None = None
    pledge_risk_flag: str | None = None
    promoter_pledged_pct: Decimal | None = None
    # Sentiment + news
    news_count: int = 0
    avg_sentiment: Decimal | None = None
    recent_news: list[NewsItem] = field(default_factory=list)


async def resolve_isin(
    session: AsyncSession, *, symbol: str | None, isin: str | None
) -> str | None:
    """Resolve to an ISIN: direct isin, else exact (case-insensitive) nse_symbol."""
    if isin is not None:
        return (
            await session.execute(select(Stock.isin).where(Stock.isin == isin))
        ).scalar_one_or_none()
    if symbol is not None:
        return (
            await session.execute(
                select(Stock.isin).where(
                    func.upper(Stock.nse_symbol) == symbol.upper()
                )
            )
        ).scalar_one_or_none()
    return None


async def fuzzy_symbol_matches(
    session: AsyncSession, query: str, *, limit: int = 5
) -> list[tuple[str, str]]:
    """Closest (nse_symbol, company_name) by pg_trgm similarity on the symbol."""
    sim = func.similarity(Stock.nse_symbol, query)
    stmt = (
        select(Stock.nse_symbol, Stock.company_name)
        .where(Stock.nse_symbol.is_not(None), sim > 0.2)
        .order_by(sim.desc())
        .limit(limit)
    )
    return [(s, n) for s, n in (await session.execute(stmt)).all()]


async def _latest(session: AsyncSession, model: Any, date_col: Any, isin: str) -> Any:
    stmt = (
        select(model).where(model.isin == isin).order_by(date_col.desc()).limit(1)
    )
    return (await session.execute(stmt)).scalars().first()


async def fetch_analysis(session: AsyncSession, isin: str) -> AnalysisData | None:
    """Gather the latest signal rows for `isin` into a flat AnalysisData."""
    stock = (
        await session.execute(select(Stock).where(Stock.isin == isin))
    ).scalars().first()
    if stock is None:
        return None

    ranking = await _latest(session, StockRanking, StockRanking.computed_date, isin)
    tech = await _latest(session, TechnicalSignal, TechnicalSignal.computed_date, isin)
    fund = await _latest(
        session, FundamentalSignal, FundamentalSignal.fetched_date, isin
    )
    risk = await _latest(session, RiskSignal, RiskSignal.computed_date, isin)
    promoter = await _latest(
        session, PromoterSignal, PromoterSignal.report_date, isin
    )

    current_price = (
        await session.execute(
            select(PriceEodAdjusted.adj_close)
            .where(PriceEodAdjusted.isin == isin)
            .order_by(PriceEodAdjusted.trade_date.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    current_volume = (
        await session.execute(
            select(PriceEod.volume)
            .where(PriceEod.isin == isin)
            .order_by(PriceEod.trade_date.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    # Macro (latest per indicator) + market-wide FII signal.
    macro_stmt = (
        select(MacroSignal.indicator, MacroSignal.value, MacroSignal.signal)
        .distinct(MacroSignal.indicator)
        .order_by(MacroSignal.indicator, MacroSignal.computed_date.desc())
    )
    macro = {
        ind: (val, sig) for ind, val, sig in (await session.execute(macro_stmt)).all()
    }
    fii_signal = (
        await session.execute(
            select(FiiDiiFlow.fii_signal)
            .order_by(FiiDiiFlow.flow_date.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    # Sector signal + 7d momentum + sector-median PE for this stock's sector.
    sector_signal: str | None = None
    sector_momentum_7d: Decimal | None = None
    sector_median_pe: Decimal | None = None
    if stock.sector is not None:
        sec_row = (
            await session.execute(
                select(SectorSignal.signal, SectorSignal.momentum_7d)
                .where(SectorSignal.sector == stock.sector)
                .order_by(SectorSignal.computed_date.desc())
                .limit(1)
            )
        ).first()
        if sec_row is not None:
            sector_signal, sector_momentum_7d = sec_row
        latest_fund_date = select(
            func.max(FundamentalSignal.fetched_date)
        ).scalar_subquery()
        sector_median_pe = (
            await session.execute(
                select(
                    func.percentile_cont(0.5).within_group(
                        FundamentalSignal.pe_ratio.asc()
                    )
                )
                .join(Stock, Stock.isin == FundamentalSignal.isin)
                .where(
                    Stock.sector == stock.sector,
                    FundamentalSignal.fetched_date == latest_fund_date,
                    FundamentalSignal.pe_ratio.is_not(None),
                    FundamentalSignal.pe_ratio > 0,
                )
            )
        ).scalar_one_or_none()

    # Sentiment aggregate + recent matched news.
    count, avg = (
        await session.execute(
            select(func.count(), func.avg(NewsArticle.sentiment_score)).where(
                NewsArticle.isin == isin,
                NewsArticle.sentiment_score.is_not(None),
            )
        )
    ).one()
    news_rows = (
        await session.execute(
            select(
                NewsArticle.headline,
                NewsArticle.published_at,
                NewsArticle.sentiment_label,
            )
            .where(NewsArticle.isin == isin)
            .order_by(NewsArticle.published_at.desc().nullslast())
            .limit(3)
        )
    ).all()

    return AnalysisData(
        isin=stock.isin,
        nse_symbol=stock.nse_symbol,
        company_name=stock.company_name,
        sector=stock.sector,
        industry=stock.industry,
        mcap_category=stock.mcap_category,
        mcap_inr_cr=stock.mcap_inr_cr,
        composite_score=getattr(ranking, "composite_score", None),
        signal_label=getattr(ranking, "signal_label", None),
        technical_score=getattr(ranking, "technical_score", None),
        fundamental_score=getattr(ranking, "fundamental_score", None),
        macro_score=getattr(ranking, "macro_score", None),
        sentiment_adj=getattr(ranking, "sentiment_adj", None),
        risk_penalty=getattr(ranking, "risk_penalty", None),
        ranking_computed_date=getattr(ranking, "computed_date", None),
        ranking_computed_at=getattr(ranking, "computed_at", None),
        rsi_14=getattr(tech, "rsi_14", None),
        ema_cross=getattr(tech, "ema_cross", None),
        price_vs_ema200=getattr(tech, "price_vs_ema200", None),
        macd_hist=getattr(tech, "macd_hist", None),
        current_price=current_price,
        current_volume=current_volume,
        avg_volume_30d=getattr(fund, "avg_volume_30d", None),
        fifty_two_week_high=getattr(fund, "fifty_two_week_high", None),
        fifty_two_week_low=getattr(fund, "fifty_two_week_low", None),
        pe_ratio=getattr(fund, "pe_ratio", None),
        sector_median_pe=sector_median_pe,
        roe=getattr(fund, "roe", None),
        debt_to_equity=getattr(fund, "debt_to_equity", None),
        revenue_growth=getattr(fund, "revenue_growth", None),
        free_cash_flow=getattr(fund, "free_cash_flow", None),
        fcf_positive=getattr(fund, "fcf_positive", None),
        q_profit_direction=getattr(fund, "q_profit_direction", None),
        dividend_consecutive_years=getattr(fund, "dividend_consecutive_years", None),
        interest_coverage=getattr(fund, "interest_coverage", None),
        sector_signal=sector_signal,
        sector_momentum_7d=sector_momentum_7d,
        fii_signal=fii_signal,
        regime=macro.get("regime", (None, None))[1],
        vix_value=macro.get("india_vix", (None, None))[0],
        vix_signal=macro.get("india_vix", (None, None))[1],
        risk_score=getattr(risk, "risk_score", None),
        volatility_flag=getattr(risk, "volatility_flag", None),
        atr_pct=getattr(risk, "atr_pct", None),
        news_spike=getattr(risk, "news_spike", None),
        pledge_risk_flag=getattr(promoter, "pledge_risk_flag", None),
        promoter_pledged_pct=getattr(promoter, "promoter_pledged_pct", None),
        news_count=int(count or 0),
        avg_sentiment=avg,
        recent_news=[
            NewsItem(headline=h, published_at=p, sentiment_label=lbl)
            for h, p, lbl in news_rows
        ],
    )
