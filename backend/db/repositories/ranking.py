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
) -> dict[str, tuple[Decimal | None, str | None, str | None, Decimal | None]]:
    stmt = (
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
    return {
        i: (rsi, pve, cross, macd)
        for i, rsi, pve, cross, macd in (await session.execute(stmt)).all()
    }


async def fetch_fundamentals(
    session: AsyncSession,
) -> dict[str, tuple[Decimal | None, Decimal | None, Decimal | None, Decimal | None]]:
    stmt = (
        select(
            FundamentalSignal.isin,
            FundamentalSignal.pe_ratio,
            FundamentalSignal.roe,
            FundamentalSignal.debt_to_equity,
            FundamentalSignal.revenue_growth,
        )
        .distinct(FundamentalSignal.isin)
        .order_by(FundamentalSignal.isin, FundamentalSignal.fetched_date.desc())
    )
    return {
        i: (pe, roe, de, rg)
        for i, pe, roe, de, rg in (await session.execute(stmt)).all()
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
