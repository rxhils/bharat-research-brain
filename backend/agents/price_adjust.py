"""Adjusted Price Agent — materializes prices_eod_adjusted (Chunk 2.1).

For each stock it loads the raw OHLCV series + corporate actions, runs the
pure `adjust_series` engine, and upserts the back-adjusted rows. The stored
`adj_factor` is the cumulative split MULTIPLIER (1 / engine divisor): 0.5 after
a 2:1 split, 1.0 with no prior split — matching the spec's verification.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import select

from backend.agents.adjusted_prices import Action, AdjBar, adjust_series
from backend.db.models import Stock
from backend.db.repositories import adjusted_prices as adj_repo
from backend.db.repositories import corporate_actions as ca_repo
from backend.db.session import SessionLocal

log = structlog.get_logger()

_FACTOR_Q = Decimal("0.00000001")


@dataclass
class AdjustResult:
    stocks_processed: int = 0
    bars: int = 0
    actions: int = 0
    rows_upserted: int = 0
    sample: list[tuple[date, Decimal | None, Decimal]] = field(default_factory=list)


def _multiplier(divisor: Decimal) -> Decimal:
    """Engine adj_factor is the split divisor; store the multiplier 1/divisor."""
    if not divisor:
        return Decimal(1)
    return (Decimal(1) / divisor).quantize(_FACTOR_Q)


def _to_row(isin: str, ab: AdjBar) -> dict[str, Any]:
    return {
        "trade_date": ab.trade_date,
        "isin": isin,
        "adj_open": ab.adj_open,
        "adj_high": ab.adj_high,
        "adj_low": ab.adj_low,
        "adj_close": ab.adj_close,
        "adj_volume": ab.adj_volume,
        "adj_factor": _multiplier(ab.adj_factor),
        "source": "adjusted",
    }


def _boundary_sample(adj: list[AdjBar]) -> list[tuple[date, Decimal | None, Decimal]]:
    """One row per change in adj_factor — shows each split boundary compactly."""
    out: list[tuple[date, Decimal | None, Decimal]] = []
    seen: Decimal | None = None
    for ab in adj:
        if ab.adj_factor != seen:
            out.append((ab.trade_date, ab.adj_close, _multiplier(ab.adj_factor)))
            seen = ab.adj_factor
    return out


class AdjustedPriceAgent:
    async def adjust_isin(self, isin: str, *, dry_run: bool = False) -> AdjustResult:
        async with SessionLocal() as session:
            raw = await adj_repo.fetch_raw_bars(session, isin)
            cas = await ca_repo.fetch_actions(session, isin=isin, limit=100_000)
            actions = [
                Action(
                    c.ex_date,
                    c.action_type,
                    c.ratio_numerator,
                    c.ratio_denominator,
                    c.amount_inr,
                )
                for c in cas
            ]
            adj = adjust_series(raw, actions)
            rows = [_to_row(isin, ab) for ab in adj]
            upserted = 0
            if not dry_run and rows:
                upserted = await adj_repo.bulk_upsert(session, rows)
                await session.commit()
        result = AdjustResult(
            stocks_processed=1 if raw else 0,
            bars=len(raw),
            actions=len(actions),
            rows_upserted=upserted,
            sample=_boundary_sample(adj),
        )
        log.info(
            "prices.adjust.isin",
            isin=isin,
            bars=result.bars,
            actions=result.actions,
            upserted=upserted,
            dry_run=dry_run,
        )
        return result

    async def adjust_all(self, *, dry_run: bool = False) -> AdjustResult:
        async with SessionLocal() as session:
            isins = list(
                (
                    await session.execute(
                        select(Stock.isin)
                        .where(Stock.delisted_on.is_(None))
                        .order_by(Stock.isin)
                    )
                )
                .scalars()
                .all()
            )

        agg = AdjustResult()
        for isin in isins:
            r = await self.adjust_isin(isin, dry_run=dry_run)
            agg.stocks_processed += r.stocks_processed
            agg.bars += r.bars
            agg.actions += r.actions
            agg.rows_upserted += r.rows_upserted
            if agg.stocks_processed % 50 == 0:
                log.info(
                    "prices.adjust.progress",
                    processed=agg.stocks_processed,
                    total=len(isins),
                )
        return agg
