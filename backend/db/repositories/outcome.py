"""Data access for the Outcome Agent (Phase 5, Chunk 5.1).

Pure dataclasses (`OutcomeRow`, `TrainingRow`, `AccuracySummary`) plus the
read/write helpers. Business logic (return math, encoders, accuracy) lives in the
agent (`backend.agents.outcome`) so this layer stays data-access only (AGENTS.md
§7). Upserts use ON CONFLICT on the natural key; "previous N trading day" is
derived from the actual sessions present in `prices_eod_adjusted`, so a pick's
exit lookup aligns exactly with the days we hold prices for.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import (
    DeliverySignal,
    MacroSignal,
    OutcomeLog,
    PriceEodAdjusted,
    Stock,
    StockRanking,
    VcpSignal,
    XgboostTraining,
)

_TRACKED_LABELS = ("bullish-watch", "needs-confirmation")


@dataclass
class OutcomeRow:
    isin: str
    pick_date: date
    signal_label: str
    composite_score: Decimal | None
    entry_price: Decimal | None
    exit_price_1d: Decimal | None = None
    exit_price_5d: Decimal | None = None
    return_1d_pct: Decimal | None = None
    return_5d_pct: Decimal | None = None
    direction_correct_1d: bool | None = None
    direction_correct_5d: bool | None = None
    technical_score: Decimal | None = None
    fundamental_score: Decimal | None = None
    macro_score: Decimal | None = None
    macro_regime: str | None = None
    india_vix: Decimal | None = None
    sector: str | None = None
    vcp_detected: bool | None = None
    delivery_pct: Decimal | None = None


@dataclass
class TrainingRow:
    isin: str
    pick_date: date
    f_technical_score: Decimal | None = None
    f_fundamental_score: Decimal | None = None
    f_macro_score: Decimal | None = None
    f_rsi_14: Decimal | None = None
    f_macd_hist: Decimal | None = None
    f_price_vs_ema200: Decimal | None = None
    f_pe_ratio: Decimal | None = None
    f_roe: Decimal | None = None
    f_revenue_growth: Decimal | None = None
    f_fii_signal_encoded: Decimal | None = None
    f_macro_regime_encoded: Decimal | None = None
    f_india_vix: Decimal | None = None
    f_vcp_score: Decimal | None = None
    f_delivery_pct: Decimal | None = None
    f_days_to_results: int | None = None
    target_return_5d: Decimal | None = None
    target_direction_5d: bool | None = None


@dataclass
class AccuracySummary:
    total_picks: int = 0
    correct_1d: int = 0
    correct_5d: int = 0
    accuracy_1d_pct: Decimal = Decimal("0.00")
    accuracy_5d_pct: Decimal = Decimal("0.00")
    by_signal: dict[str, dict[str, Any]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Trading-day helpers (sessions we actually hold prices for)
# ---------------------------------------------------------------------------
async def _prev_trading_day(
    session: AsyncSession, as_of: date, *, offset: int
) -> date | None:
    """The trade_date `offset` sessions before `as_of` in prices_eod_adjusted.

    offset=1 -> the most recent session strictly before as_of; offset=5 -> five
    sessions before. None if we don't have that much history.
    """
    stmt = (
        select(PriceEodAdjusted.trade_date)
        .distinct()
        .where(PriceEodAdjusted.trade_date < as_of)
        .order_by(PriceEodAdjusted.trade_date.desc())
        .offset(offset - 1)
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def fetch_adj_close(
    session: AsyncSession, trade_date: date, isins: Sequence[str] | None = None
) -> dict[str, Decimal]:
    """{isin: adj_close} on `trade_date`. Missing rows simply don't appear."""
    stmt = select(PriceEodAdjusted.isin, PriceEodAdjusted.adj_close).where(
        PriceEodAdjusted.trade_date == trade_date,
        PriceEodAdjusted.adj_close.is_not(None),
    )
    if isins is not None:
        stmt = stmt.where(PriceEodAdjusted.isin.in_(list(isins)))
    return {i: c for i, c in (await session.execute(stmt)).all()}


# ---------------------------------------------------------------------------
# Pick recording inputs (the pick-date snapshot — mle no-leakage: <= pick_date)
# ---------------------------------------------------------------------------
async def fetch_rankings_for_picks(
    session: AsyncSession, pick_date: date
) -> list[OutcomeRow]:
    """Assemble OutcomeRows (entry + snapshot, no exits) for the tracked labels.

    Every supporting signal is taken as-of pick_date or earlier — never future
    data (mle no-leakage). Entry price is adj_close on pick_date (may be None if
    we have no adjusted bar that day; such picks are still recorded and skipped at
    fill time).
    """
    rank_stmt = (
        select(
            StockRanking.isin,
            StockRanking.signal_label,
            StockRanking.composite_score,
            StockRanking.technical_score,
            StockRanking.fundamental_score,
            StockRanking.macro_score,
            Stock.sector,
        )
        .join(Stock, Stock.isin == StockRanking.isin)
        .where(
            StockRanking.computed_date == pick_date,
            StockRanking.signal_label.in_(_TRACKED_LABELS),
        )
    )
    ranks = (await session.execute(rank_stmt)).all()
    if not ranks:
        return []

    isins = [r[0] for r in ranks]
    entry_by = await fetch_adj_close(session, pick_date, isins)
    regime, vix = await _fetch_macro_context(session, pick_date)
    vcp_by = await _fetch_vcp_detected(session, pick_date, isins)
    delivery_by = await _fetch_delivery_pct(session, pick_date, isins)

    rows: list[OutcomeRow] = []
    for isin, label, comp, tech, fund, macro, sector in ranks:
        rows.append(
            OutcomeRow(
                isin=isin,
                pick_date=pick_date,
                signal_label=label,
                composite_score=comp,
                entry_price=entry_by.get(isin),
                technical_score=tech,
                fundamental_score=fund,
                macro_score=macro,
                macro_regime=regime,
                india_vix=vix,
                sector=sector,
                vcp_detected=vcp_by.get(isin),
                delivery_pct=delivery_by.get(isin),
            )
        )
    return rows


async def _fetch_macro_context(
    session: AsyncSession, as_of: date
) -> tuple[str | None, Decimal | None]:
    regime_stmt = (
        select(MacroSignal.signal)
        .where(MacroSignal.indicator == "regime", MacroSignal.computed_date <= as_of)
        .order_by(MacroSignal.computed_date.desc())
        .limit(1)
    )
    vix_stmt = (
        select(MacroSignal.value)
        .where(
            MacroSignal.indicator == "india_vix", MacroSignal.computed_date <= as_of
        )
        .order_by(MacroSignal.computed_date.desc())
        .limit(1)
    )
    regime = (await session.execute(regime_stmt)).scalar_one_or_none()
    vix = (await session.execute(vix_stmt)).scalar_one_or_none()
    return regime, vix


async def _fetch_vcp_detected(
    session: AsyncSession, as_of: date, isins: Sequence[str]
) -> dict[str, bool]:
    stmt = (
        select(VcpSignal.isin, VcpSignal.vcp_detected)
        .distinct(VcpSignal.isin)
        .where(VcpSignal.isin.in_(list(isins)), VcpSignal.computed_date <= as_of)
        .order_by(VcpSignal.isin, VcpSignal.computed_date.desc())
    )
    return {i: d for i, d in (await session.execute(stmt)).all()}


async def _fetch_delivery_pct(
    session: AsyncSession, as_of: date, isins: Sequence[str]
) -> dict[str, Decimal]:
    stmt = (
        select(DeliverySignal.isin, DeliverySignal.delivery_pct)
        .distinct(DeliverySignal.isin)
        .where(
            DeliverySignal.isin.in_(list(isins)), DeliverySignal.trade_date <= as_of
        )
        .order_by(DeliverySignal.isin, DeliverySignal.trade_date.desc())
    )
    return {i: p for i, p in (await session.execute(stmt)).all()}


# ---------------------------------------------------------------------------
# Pending-exit fetches
# ---------------------------------------------------------------------------
def _row_from_model(m: OutcomeLog) -> OutcomeRow:
    return OutcomeRow(
        isin=m.isin,
        pick_date=m.pick_date,
        signal_label=m.signal_label,
        composite_score=m.composite_score,
        entry_price=m.entry_price,
        exit_price_1d=m.exit_price_1d,
        exit_price_5d=m.exit_price_5d,
        return_1d_pct=m.return_1d_pct,
        return_5d_pct=m.return_5d_pct,
        direction_correct_1d=m.direction_correct_1d,
        direction_correct_5d=m.direction_correct_5d,
        technical_score=m.technical_score,
        fundamental_score=m.fundamental_score,
        macro_score=m.macro_score,
        macro_regime=m.macro_regime,
        india_vix=m.india_vix,
        sector=m.sector,
        vcp_detected=m.vcp_detected,
        delivery_pct=m.delivery_pct,
    )


async def fetch_pending_1d(session: AsyncSession, as_of: date) -> list[OutcomeRow]:
    """Picks from the prior trading day still missing a 1d exit."""
    prev = await _prev_trading_day(session, as_of, offset=1)
    if prev is None:
        return []
    stmt = select(OutcomeLog).where(
        OutcomeLog.pick_date == prev, OutcomeLog.exit_price_1d.is_(None)
    )
    return [_row_from_model(m) for m in (await session.execute(stmt)).scalars().all()]


async def fetch_pending_5d(session: AsyncSession, as_of: date) -> list[OutcomeRow]:
    """Picks from five trading days ago still missing a 5d exit."""
    prev = await _prev_trading_day(session, as_of, offset=5)
    if prev is None:
        return []
    stmt = select(OutcomeLog).where(
        OutcomeLog.pick_date == prev, OutcomeLog.exit_price_5d.is_(None)
    )
    return [_row_from_model(m) for m in (await session.execute(stmt)).scalars().all()]


async def fetch_recent_outcomes(
    session: AsyncSession, *, days: int = 30, signal: str | None = None
) -> list[OutcomeRow]:
    """Outcome rows for the last `days` pick_dates (newest first)."""
    cutoff = select(func.max(OutcomeLog.pick_date)).scalar_subquery()
    stmt = select(OutcomeLog).where(
        OutcomeLog.pick_date
        >= func.coalesce(cutoff, OutcomeLog.pick_date)
        - text(f"interval '{int(days)} days'")
    )
    if signal is not None:
        stmt = stmt.where(OutcomeLog.signal_label == signal)
    stmt = stmt.order_by(
        OutcomeLog.pick_date.desc(), OutcomeLog.composite_score.desc()
    )
    return [_row_from_model(m) for m in (await session.execute(stmt)).scalars().all()]


# ---------------------------------------------------------------------------
# Upserts (ON CONFLICT on the natural key)
# ---------------------------------------------------------------------------
_OUTCOME_UPSERT_COLS = (
    "signal_label",
    "composite_score",
    "entry_price",
    "exit_price_1d",
    "exit_price_5d",
    "return_1d_pct",
    "return_5d_pct",
    "direction_correct_1d",
    "direction_correct_5d",
    "technical_score",
    "fundamental_score",
    "macro_score",
    "macro_regime",
    "india_vix",
    "sector",
    "vcp_detected",
    "delivery_pct",
)


async def upsert_outcome(session: AsyncSession, row: OutcomeRow) -> None:
    """Insert/update one outcome row on (isin, pick_date). Caller commits."""
    values = {
        "isin": row.isin,
        "pick_date": row.pick_date,
        "signal_label": row.signal_label,
        "composite_score": row.composite_score,
        "entry_price": row.entry_price,
        "exit_price_1d": row.exit_price_1d,
        "exit_price_5d": row.exit_price_5d,
        "return_1d_pct": row.return_1d_pct,
        "return_5d_pct": row.return_5d_pct,
        "direction_correct_1d": row.direction_correct_1d,
        "direction_correct_5d": row.direction_correct_5d,
        "technical_score": row.technical_score,
        "fundamental_score": row.fundamental_score,
        "macro_score": row.macro_score,
        "macro_regime": row.macro_regime,
        "india_vix": row.india_vix,
        "sector": row.sector,
        "vcp_detected": row.vcp_detected,
        "delivery_pct": row.delivery_pct,
    }
    stmt = pg_insert(OutcomeLog).values(**values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["isin", "pick_date"],
        set_={c: getattr(stmt.excluded, c) for c in _OUTCOME_UPSERT_COLS},
    )
    await session.execute(stmt)


_TRAINING_UPSERT_COLS = (
    "f_technical_score",
    "f_fundamental_score",
    "f_macro_score",
    "f_rsi_14",
    "f_macd_hist",
    "f_price_vs_ema200",
    "f_pe_ratio",
    "f_roe",
    "f_revenue_growth",
    "f_fii_signal_encoded",
    "f_macro_regime_encoded",
    "f_india_vix",
    "f_vcp_score",
    "f_delivery_pct",
    "f_days_to_results",
    "target_return_5d",
    "target_direction_5d",
)


async def upsert_training_row(session: AsyncSession, row: TrainingRow) -> None:
    """Insert/update one xgboost_training row on (isin, pick_date). Caller commits."""
    values = {
        "isin": row.isin,
        "pick_date": row.pick_date,
        "f_technical_score": row.f_technical_score,
        "f_fundamental_score": row.f_fundamental_score,
        "f_macro_score": row.f_macro_score,
        "f_rsi_14": row.f_rsi_14,
        "f_macd_hist": row.f_macd_hist,
        "f_price_vs_ema200": row.f_price_vs_ema200,
        "f_pe_ratio": row.f_pe_ratio,
        "f_roe": row.f_roe,
        "f_revenue_growth": row.f_revenue_growth,
        "f_fii_signal_encoded": row.f_fii_signal_encoded,
        "f_macro_regime_encoded": row.f_macro_regime_encoded,
        "f_india_vix": row.f_india_vix,
        "f_vcp_score": row.f_vcp_score,
        "f_delivery_pct": row.f_delivery_pct,
        "f_days_to_results": row.f_days_to_results,
        "target_return_5d": row.target_return_5d,
        "target_direction_5d": row.target_direction_5d,
    }
    stmt = pg_insert(XgboostTraining).values(**values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["isin", "pick_date"],
        set_={c: getattr(stmt.excluded, c) for c in _TRAINING_UPSERT_COLS},
    )
    await session.execute(stmt)
