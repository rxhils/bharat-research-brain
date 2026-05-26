"""Data access for the Report Agent (Chunk 4.4, deterministic redesign).

Assembles the report context from existing signal tables (no LLM) and upserts
the daily note via ON CONFLICT (report_date) DO UPDATE. `fetch_top_stocks`
builds the agent's StockCtx (lazy import avoids a module-level repo->agent cycle).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import (
    DailyReport,
    FiiDiiFlow,
    FundamentalSignal,
    MacroSignal,
    RiskSignal,
    SectorSignal,
    Stock,
    StockRanking,
    TechnicalSignal,
)

if TYPE_CHECKING:
    from backend.agents.report import StockCtx

_UPSERT_COLS = ("body_md", "word_count", "top_stocks", "macro_summary", "audit_passed")


async def fetch_macro(session: AsyncSession) -> dict[str, Any]:
    latest = select(func.max(MacroSignal.computed_date)).scalar_subquery()
    rows = (
        await session.execute(
            select(
                MacroSignal.indicator, MacroSignal.value, MacroSignal.signal
            ).where(MacroSignal.computed_date == latest)
        )
    ).all()
    by = {ind: (val, sig) for ind, val, sig in rows}
    return {
        "regime": (by.get("regime") or (None, "neutral"))[1],
        "nifty_value": (by.get("nifty_50") or (None, None))[0],
        "nifty_signal": (by.get("nifty_50") or (None, "unknown"))[1],
        "usd_inr": (by.get("usd_inr") or (None, None))[0],
        "usd_signal": (by.get("usd_inr") or (None, "unknown"))[1],
        "crude_signal": (by.get("crude_brent") or (None, "unknown"))[1],
    }


async def fetch_fii_latest(
    session: AsyncSession,
) -> tuple[Decimal | None, str | None]:
    stmt = (
        select(FiiDiiFlow.fii_5d_sum, FiiDiiFlow.fii_signal)
        .order_by(FiiDiiFlow.flow_date.desc())
        .limit(1)
    )
    row = (await session.execute(stmt)).first()
    return (row[0], row[1]) if row else (None, None)


async def _sector_map(session: AsyncSession) -> dict[str, tuple[str, Decimal | None]]:
    latest = select(func.max(SectorSignal.computed_date)).scalar_subquery()
    rows = (
        await session.execute(
            select(
                SectorSignal.sector, SectorSignal.signal, SectorSignal.momentum_7d
            ).where(SectorSignal.computed_date == latest)
        )
    ).all()
    return {sec: (sig, mom) for sec, sig, mom in rows}


async def fetch_top_stocks(session: AsyncSession, *, limit: int = 5) -> list[StockCtx]:
    from backend.agents.report import StockCtx  # lazy: avoid repo->agent cycle

    rank_date = select(func.max(StockRanking.computed_date)).scalar_subquery()
    ranking_rows = (
        await session.execute(
            select(
                StockRanking.isin,
                Stock.nse_symbol,
                Stock.sector,
                StockRanking.composite_score,
                StockRanking.signal_label,
                StockRanking.technical_score,
                StockRanking.fundamental_score,
                StockRanking.macro_score,
                StockRanking.risk_penalty,
            )
            .join(Stock, Stock.isin == StockRanking.isin)
            .where(StockRanking.computed_date == rank_date)
            .order_by(StockRanking.composite_score.desc())
            .limit(limit)
        )
    ).all()
    isins = [r[0] for r in ranking_rows]
    if not isins:
        return []

    tech_rows = (
        await session.execute(
            select(
                TechnicalSignal.isin,
                TechnicalSignal.rsi_14,
                TechnicalSignal.ema_cross,
                TechnicalSignal.price_vs_ema200,
                TechnicalSignal.macd_hist,
                TechnicalSignal.computed_date,
            )
            .distinct(TechnicalSignal.isin)
            .where(TechnicalSignal.isin.in_(isins))
            .order_by(TechnicalSignal.isin, TechnicalSignal.computed_date.desc())
        )
    ).all()
    tech = {r[0]: r[1:] for r in tech_rows}

    fund_rows = (
        await session.execute(
            select(
                FundamentalSignal.isin,
                FundamentalSignal.pe_ratio,
                FundamentalSignal.roe,
                FundamentalSignal.debt_to_equity,
                FundamentalSignal.revenue_growth,
                FundamentalSignal.fetched_date,
            )
            .distinct(FundamentalSignal.isin)
            .where(FundamentalSignal.isin.in_(isins))
            .order_by(FundamentalSignal.isin, FundamentalSignal.fetched_date.desc())
        )
    ).all()
    fund = {r[0]: r[1:] for r in fund_rows}

    risk_rows = (
        await session.execute(
            select(
                RiskSignal.isin, RiskSignal.volatility_flag, RiskSignal.atr_pct
            )
            .distinct(RiskSignal.isin)
            .where(RiskSignal.isin.in_(isins))
            .order_by(RiskSignal.isin, RiskSignal.computed_date.desc())
        )
    ).all()
    risk = {r[0]: (r[1], r[2]) for r in risk_rows}

    sectors = await _sector_map(session)
    _, fii_signal = await fetch_fii_latest(session)

    out: list[StockCtx] = []
    for rank, row in enumerate(ranking_rows, 1):
        isin, sym, sector, comp, label, t, f, m, rp = row
        rsi, cross, vs_ema, macd, ts_date = tech.get(
            isin, (None, None, None, None, None)
        )
        pe, roe, de, rev, fs_date = fund.get(isin, (None, None, None, None, None))
        vflag, atr = risk.get(isin, (None, None))
        sec_sig, sec_mom = sectors.get(sector or "", (None, None))
        out.append(
            StockCtx(
                rank=rank,
                isin=isin,
                symbol=sym or isin,
                sector=sector,
                label=label,
                composite=comp,
                t_score=t,
                f_score=f,
                m_score=m,
                risk_penalty=rp,
                volatility_flag=vflag,
                atr_pct=atr,
                rsi=rsi,
                ema_cross=cross,
                vs_ema200=vs_ema,
                macd_hist=macd,
                roe=roe,
                de=de,
                pe=pe,
                rev_growth=rev,
                sector_signal=sec_sig,
                sector_mom_7d=sec_mom,
                fii_signal=fii_signal,
                ts_date=ts_date,
                fs_date=fs_date,
            )
        )
    return out


async def fetch_top10(session: AsyncSession) -> list[tuple[str, Decimal]]:
    rank_date = select(func.max(StockRanking.computed_date)).scalar_subquery()
    rows = (
        await session.execute(
            select(StockRanking.isin, StockRanking.composite_score)
            .where(StockRanking.computed_date == rank_date)
            .order_by(StockRanking.composite_score.desc())
            .limit(10)
        )
    ).all()
    return [(i, s) for i, s in rows]


async def fetch_sector_buckets(
    session: AsyncSession,
) -> tuple[list[str], list[str], list[str]]:
    sectors = await _sector_map(session)
    leading = sorted(s for s, (sig, _) in sectors.items() if sig == "leading")
    lagging = sorted(s for s, (sig, _) in sectors.items() if sig == "lagging")
    neutral = sorted(s for s, (sig, _) in sectors.items() if sig == "neutral")
    return leading, lagging, neutral


async def fetch_risk_top(
    session: AsyncSession, *, limit: int = 3
) -> list[tuple[str, Decimal, str, Decimal | None]]:
    latest = select(func.max(RiskSignal.computed_date)).scalar_subquery()
    rows = (
        await session.execute(
            select(
                Stock.nse_symbol,
                RiskSignal.risk_score,
                RiskSignal.volatility_flag,
                RiskSignal.atr_pct,
            )
            .join(Stock, Stock.isin == RiskSignal.isin)
            .where(RiskSignal.computed_date == latest)
            .order_by(RiskSignal.risk_score.desc())
            .limit(limit)
        )
    ).all()
    return [(sym or "?", score, flag, atr) for sym, score, flag, atr in rows]


async def fetch_signal_distribution(session: AsyncSession) -> dict[str, int]:
    latest = select(func.max(StockRanking.computed_date)).scalar_subquery()
    rows = (
        await session.execute(
            select(StockRanking.signal_label, func.count())
            .where(StockRanking.computed_date == latest)
            .group_by(StockRanking.signal_label)
        )
    ).all()
    return {label: int(n) for label, n in rows}


async def fetch_fund_date(session: AsyncSession) -> date | None:
    return (
        await session.execute(select(func.max(FundamentalSignal.fetched_date)))
    ).scalar_one_or_none()


async def upsert_report(session: AsyncSession, row: dict[str, Any]) -> int:
    stmt = pg_insert(DailyReport).values([row])
    stmt = stmt.on_conflict_do_update(
        index_elements=["report_date"],
        set_={c: getattr(stmt.excluded, c) for c in _UPSERT_COLS}
        | {"generated_at": func.now()},
    )
    result = await session.execute(stmt)
    return result.rowcount or 0


async def fetch_reports(session: AsyncSession, *, limit: int = 5) -> list[DailyReport]:
    stmt = select(DailyReport).order_by(DailyReport.report_date.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def fetch_report(
    session: AsyncSession, *, report_date: date
) -> DailyReport | None:
    stmt = select(DailyReport).where(DailyReport.report_date == report_date)
    return (await session.execute(stmt)).scalars().first()


async def set_audit_passed(
    session: AsyncSession, report_date: date, passed: bool
) -> int:
    """Flip daily_reports.audit_passed for the given date. Caller commits."""
    from sqlalchemy import update

    result = await session.execute(
        update(DailyReport)
        .where(DailyReport.report_date == report_date)
        .values(audit_passed=passed)
    )
    return result.rowcount or 0
