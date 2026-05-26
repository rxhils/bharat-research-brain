"""Data access for the Ranking Agent (Chunk 4.3).

Loads the latest row from every signal table (returning plain tuples/scalars so
this layer never imports the agent), and upserts composite rankings via
ON CONFLICT (isin, computed_date) DO UPDATE.
"""
from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import (
    FiiDiiFlow,
    FundamentalSignal,
    MacroSignal,
    NewsArticle,
    PriceEod,
    PriceEodAdjusted,
    RiskSignal,
    SectorSignal,
    Stock,
    StockRanking,
    TechnicalSignal,
)

_UPSERT_COLS = (
    "composite_score",
    "signal_label",
    "fundamental_score",
    "technical_score",
    "macro_score",
    "sentiment_adj",
    "risk_penalty",
    "score_breakdown",
    "source",
)


async def fetch_active_isins(session: AsyncSession) -> list[str]:
    stmt = select(Stock.isin).where(Stock.delisted_on.is_(None))
    return [i for (i,) in (await session.execute(stmt)).all()]


async def fetch_technicals(
    session: AsyncSession,
) -> dict[str, tuple[Any, ...]]:
    """Latest per-isin technicals in TechInputs order (Chunk 4.9 widened).

    (rsi_14, price_vs_ema200, ema_cross, macd_hist, fifty_two_week_high,
    fifty_two_week_low, current_price, current_volume, avg_volume_30d). The 52w
    band + avg volume come from fundamental_signals; current price/volume are the
    latest adjusted close / raw volume.
    """
    tech_stmt = (
        select(
            TechnicalSignal.isin,
            TechnicalSignal.rsi_14,
            TechnicalSignal.price_vs_ema200,
            TechnicalSignal.ema_cross,
            TechnicalSignal.macd_hist,
        )
        .distinct(TechnicalSignal.isin)
        .order_by(TechnicalSignal.isin, TechnicalSignal.computed_date.desc())
    )
    fund_stmt = (
        select(
            FundamentalSignal.isin,
            FundamentalSignal.fifty_two_week_high,
            FundamentalSignal.fifty_two_week_low,
            FundamentalSignal.avg_volume_30d,
        )
        .distinct(FundamentalSignal.isin)
        .order_by(FundamentalSignal.isin, FundamentalSignal.fetched_date.desc())
    )
    price_stmt = (
        select(PriceEodAdjusted.isin, PriceEodAdjusted.adj_close)
        .distinct(PriceEodAdjusted.isin)
        .order_by(PriceEodAdjusted.isin, PriceEodAdjusted.trade_date.desc())
    )
    vol_stmt = (
        select(PriceEod.isin, PriceEod.volume)
        .distinct(PriceEod.isin)
        .order_by(PriceEod.isin, PriceEod.trade_date.desc())
    )

    tech_by = {
        i: (rsi, pve, cross, macd)
        for i, rsi, pve, cross, macd in (await session.execute(tech_stmt)).all()
    }
    fund_by = {
        i: (hi, lo, av) for i, hi, lo, av in (await session.execute(fund_stmt)).all()
    }
    price_by = {i: p for i, p in (await session.execute(price_stmt)).all()}
    vol_by = {i: v for i, v in (await session.execute(vol_stmt)).all()}

    out: dict[str, tuple[Any, ...]] = {}
    for i in tech_by.keys() | fund_by.keys() | price_by.keys() | vol_by.keys():
        rsi, pve, cross, macd = tech_by.get(i, (None, None, None, None))
        hi, lo, av = fund_by.get(i, (None, None, None))
        out[i] = (rsi, pve, cross, macd, hi, lo, price_by.get(i), vol_by.get(i), av)
    return out


async def fetch_sector_median_pe(session: AsyncSession) -> dict[str, Decimal]:
    """Median trailing PE per sector from the latest fundamentals snapshot."""
    latest_date = select(func.max(FundamentalSignal.fetched_date)).scalar_subquery()
    median = func.percentile_cont(0.5).within_group(
        FundamentalSignal.pe_ratio.asc()
    )
    stmt = (
        select(Stock.sector, median)
        .join(FundamentalSignal, FundamentalSignal.isin == Stock.isin)
        .where(
            FundamentalSignal.fetched_date == latest_date,
            FundamentalSignal.pe_ratio.is_not(None),
            FundamentalSignal.pe_ratio > 0,
            Stock.sector.is_not(None),
        )
        .group_by(Stock.sector)
    )
    return {
        sector: Decimal(str(m))
        for sector, m in (await session.execute(stmt)).all()
        if m is not None
    }


async def fetch_isin_sectors(session: AsyncSession) -> dict[str, str | None]:
    """isin -> sector for active stocks (for sector-relative PE lookup)."""
    stmt = select(Stock.isin, Stock.sector).where(Stock.delisted_on.is_(None))
    return {i: s for i, s in (await session.execute(stmt)).all()}


async def fetch_fundamentals(
    session: AsyncSession,
) -> dict[str, tuple[Any, ...]]:
    """Latest per-isin fundamentals in FundInputs order (incl. Chunk 4.8 signals)."""
    stmt = (
        select(
            FundamentalSignal.isin,
            FundamentalSignal.pe_ratio,
            FundamentalSignal.roe,
            FundamentalSignal.debt_to_equity,
            FundamentalSignal.revenue_growth,
            FundamentalSignal.fcf_positive,
            FundamentalSignal.q_profit_direction,
            FundamentalSignal.dividend_consecutive_years,
            FundamentalSignal.interest_coverage,
        )
        .distinct(FundamentalSignal.isin)
        .order_by(FundamentalSignal.isin, FundamentalSignal.fetched_date.desc())
    )
    return {
        row[0]: tuple(row[1:]) for row in (await session.execute(stmt)).all()
    }


async def fetch_risk(session: AsyncSession) -> dict[str, Decimal]:
    stmt = (
        select(RiskSignal.isin, RiskSignal.risk_score)
        .distinct(RiskSignal.isin)
        .order_by(RiskSignal.isin, RiskSignal.computed_date.desc())
    )
    return {i: s for i, s in (await session.execute(stmt)).all()}


async def fetch_sentiment(session: AsyncSession) -> dict[str, Decimal]:
    """Average sentiment_score per isin across all matched articles."""
    stmt = (
        select(NewsArticle.isin, func.avg(NewsArticle.sentiment_score))
        .where(
            NewsArticle.isin.is_not(None),
            NewsArticle.sentiment_score.is_not(None),
        )
        .group_by(NewsArticle.isin)
    )
    return {i: avg for i, avg in (await session.execute(stmt)).all()}


async def fetch_sector_by_isin(session: AsyncSession) -> dict[str, str]:
    """sector_signal mapped onto each active isin via its sector (latest date)."""
    latest_date = select(func.max(SectorSignal.computed_date)).scalar_subquery()
    stmt = (
        select(Stock.isin, SectorSignal.signal)
        .join(SectorSignal, SectorSignal.sector == Stock.sector)
        .where(
            Stock.delisted_on.is_(None), SectorSignal.computed_date == latest_date
        )
    )
    return {i: sig for i, sig in (await session.execute(stmt)).all()}


async def fetch_fii_signal(session: AsyncSession) -> str | None:
    """Latest market-wide FII signal (single value)."""
    stmt = select(FiiDiiFlow.fii_signal).order_by(FiiDiiFlow.flow_date.desc()).limit(1)
    return (await session.execute(stmt)).scalar_one_or_none()


async def fetch_macro_regime(session: AsyncSession) -> str:
    stmt = (
        select(MacroSignal.signal)
        .where(MacroSignal.indicator == "regime")
        .order_by(MacroSignal.computed_date.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none() or "neutral"


async def bulk_upsert(session: AsyncSession, rows: Sequence[dict[str, Any]]) -> int:
    """Insert/update ranking rows. Returns affected count. Caller commits."""
    if not rows:
        return 0
    stmt = pg_insert(StockRanking).values(list(rows))
    stmt = stmt.on_conflict_do_update(
        index_elements=["isin", "computed_date"],
        set_={c: getattr(stmt.excluded, c) for c in _UPSERT_COLS}
        | {"computed_at": func.now()},
    )
    result = await session.execute(stmt)
    return result.rowcount or 0


async def fetch_rankings(
    session: AsyncSession,
    *,
    limit: int = 20,
    sector: str | None = None,
    signal: str | None = None,
) -> list[tuple[StockRanking, str | None, str | None]]:
    """Latest-date rankings joined to (nse_symbol, sector), highest score first."""
    latest_date = select(func.max(StockRanking.computed_date)).scalar_subquery()
    stmt = (
        select(StockRanking, Stock.nse_symbol, Stock.sector)
        .join(Stock, Stock.isin == StockRanking.isin)
        .where(StockRanking.computed_date == latest_date)
    )
    if sector is not None:
        stmt = stmt.where(Stock.sector == sector)
    if signal is not None:
        stmt = stmt.where(StockRanking.signal_label == signal)
    stmt = stmt.order_by(StockRanking.composite_score.desc()).limit(limit)
    return [(r, sym, sec) for r, sym, sec in (await session.execute(stmt)).all()]
