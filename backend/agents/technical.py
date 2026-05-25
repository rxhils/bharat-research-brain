"""Technical Agent — nightly technical indicators on adjusted prices (Chunk 3.1).

Loads each stock's adjusted OHLC series + raw delivery series, computes RSI,
EMA(20/200), MACD, ATR, and the 30-day delivery average as-of the latest
adjusted date, and upserts one row into `technical_signals`. Pure indicator
math lives in `technical_indicators`; this orchestrates + persists. No LLMs.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import select

from backend.agents.technical_indicators import (
    atr,
    avg_last_n,
    ema,
    ema_cross_signal,
    macd,
    rsi,
)
from backend.db.models import Stock
from backend.db.repositories import technical as tech_repo
from backend.db.session import SessionLocal

log = structlog.get_logger()

SOURCE = "technical_agent"
_RSI_PERIOD = 14
_EMA_SHORT = 20
_EMA_LONG = 200
_ATR_PERIOD = 14
_DELIVERY_WINDOW = 30


@dataclass
class TechResult:
    stocks_processed: int = 0
    rows_upserted: int = 0
    skipped_no_data: int = 0


def _dec(value: float | None, places: int) -> Decimal | None:
    return Decimal(str(round(value, places))) if value is not None else None


def compute_row(
    isin: str,
    adj: list[tuple[date, Any, Any, Any, Any]],
    delivery: list[tuple[date, Any]],
) -> dict[str, Any]:
    """Build the technical_signals row from a stock's adjusted + delivery series."""
    computed_date = adj[-1][0]
    # Keep H/L/C aligned (only bars where all three are present).
    hlc = [
        (float(h), float(low), float(c))
        for (_d, _o, h, low, c) in adj
        if h is not None and low is not None and c is not None
    ]
    highs = [x[0] for x in hlc]
    lows = [x[1] for x in hlc]
    closes = [x[2] for x in hlc]
    last_close = closes[-1] if closes else None

    ema_short = ema(closes, _EMA_SHORT)
    ema_long = ema(closes, _EMA_LONG)
    macd_line, macd_sig, macd_hist = macd(closes)

    delivery_vals: list[float | None] = [
        float(dp) if dp is not None else None for _d, dp in delivery
    ]
    avg_delivery = avg_last_n(delivery_vals, _DELIVERY_WINDOW)

    if ema_long is None or last_close is None:
        price_vs = None
    elif last_close > ema_long:
        price_vs = "above"
    elif last_close < ema_long:
        price_vs = "below"
    else:
        price_vs = "at"

    return {
        "isin": isin,
        "computed_date": computed_date,
        "rsi_14": _dec(rsi(closes, _RSI_PERIOD), 4),
        "ema_20": _dec(ema_short, 4),
        "ema_200": _dec(ema_long, 4),
        "macd_line": _dec(macd_line, 4),
        "macd_signal": _dec(macd_sig, 4),
        "macd_hist": _dec(macd_hist, 4),
        "atr_14": _dec(atr(highs, lows, closes, _ATR_PERIOD), 4),
        "avg_delivery_pct_30d": _dec(avg_delivery, 2),
        "price_vs_ema200": price_vs,
        "ema_cross": ema_cross_signal(closes, _EMA_SHORT, _EMA_LONG),
        "source": SOURCE,
    }


class TechnicalAgent:
    async def run_isin(
        self, isin: str, *, dry_run: bool = False
    ) -> dict[str, Any] | None:
        async with SessionLocal() as session:
            adj = await tech_repo.load_adj_series(session, isin)
            if not adj:
                return None
            delivery = await tech_repo.load_delivery_series(session, isin)
            row = compute_row(isin, adj, delivery)
            if not dry_run:
                await tech_repo.bulk_upsert(session, [row])
                await session.commit()
        return row

    async def run_all(self, *, dry_run: bool = False) -> TechResult:
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

        res = TechResult()
        rows: list[dict[str, Any]] = []
        for isin in isins:
            async with SessionLocal() as session:
                adj = await tech_repo.load_adj_series(session, isin)
                if not adj:
                    res.skipped_no_data += 1
                    continue
                delivery = await tech_repo.load_delivery_series(session, isin)
            rows.append(compute_row(isin, adj, delivery))
            res.stocks_processed += 1
            if res.stocks_processed % 50 == 0:
                log.info(
                    "technical.progress",
                    processed=res.stocks_processed,
                    total=len(isins),
                )

        if not dry_run and rows:
            async with SessionLocal() as session:
                res.rows_upserted = await tech_repo.bulk_upsert(session, rows)
                await session.commit()
        log.info(
            "technical.run_all.done",
            processed=res.stocks_processed,
            upserted=res.rows_upserted,
            skipped=res.skipped_no_data,
            dry_run=dry_run,
        )
        return res
