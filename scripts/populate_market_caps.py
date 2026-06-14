#!/usr/bin/env python
"""Populate stocks.mcap_inr_cr from yfinance (Chunk 5.2c — fair benchmark).

`mcap_inr_cr` is 0/507, which forces equal-weight benchmark proxies — a brutally
unfair bar in a broad mid-cap rally. This fills market cap so a market-cap-
weighted Nifty 50/200 proxy is possible.

Per stock, market cap is fetched in this order (first hit wins):
  1. yfinance `fast_info.market_cap`  (fast, INR for .NS tickers)
  2. yfinance `info["marketCap"]`
  3. shares_outstanding x last close   (compute fallback)
Stored as crores (INR / 1e7), Decimal, 2 dp. UPDATE is idempotent (re-runnable).

HONESTY / LOOKAHEAD CAVEAT (mle): yfinance returns CURRENT (today's) market cap,
NOT point-in-time. A benchmark built from this weights/selects 2021 constituents
by their 2026 size — mild selection + weighting lookahead. This is a KNOWN
limitation, far better than equal-weight, and flagged in the lesson. A fully
correct benchmark needs historical shares-outstanding per date (deferred —
follow-up).

Usage:
    python -m scripts.populate_market_caps [--limit N]
"""
from __future__ import annotations

import argparse
import asyncio
from decimal import Decimal, InvalidOperation
from typing import Any

import structlog
from sqlalchemy import select, text

from backend.db.models import Stock
from backend.db.session import SessionLocal

log = structlog.get_logger()

_BATCH = 50
_BATCH_DELAY_S = 1.5
_CR = Decimal("10000000")  # 1 crore = 1e7

_UPDATE_SQL = text("UPDATE stocks SET mcap_inr_cr = :mcap WHERE isin = :isin")
_VERIFY_SQL = text(
    """
    SELECT count(*) AS total,
           count(mcap_inr_cr) AS populated,
           min(mcap_inr_cr) AS min_cr,
           max(mcap_inr_cr) AS max_cr,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY mcap_inr_cr) AS median_cr
    FROM stocks
    """
)


def _fetch_mcap_sync(yf_symbol: str) -> float | None:
    """Current market cap in INR (best effort), or None. Threaded — never blocks."""
    import yfinance as yf

    ticker = yf.Ticker(yf_symbol)

    # 1) fast_info.market_cap (FastInfo supports both attr and mapping access).
    try:
        fi = ticker.fast_info
        mc = None
        try:
            mc = fi["market_cap"]  # mapping access
        except Exception:  # noqa: BLE001
            mc = getattr(fi, "market_cap", None)
        if mc and float(mc) > 0:
            return float(mc)
    except Exception as exc:  # noqa: BLE001 - external feed, best-effort
        log.warning("mcap.fast_info_failed", symbol=yf_symbol, error=str(exc))

    # 2) info marketCap, then 3) shares x last price.
    try:
        info = ticker.info or {}
        mc = info.get("marketCap")
        if mc and float(mc) > 0:
            return float(mc)
        sh = info.get("sharesOutstanding")
        px = info.get("currentPrice") or info.get("previousClose")
        if sh and px and float(sh) > 0 and float(px) > 0:
            return float(sh) * float(px)
    except Exception as exc:  # noqa: BLE001
        log.warning("mcap.info_failed", symbol=yf_symbol, error=str(exc))
    return None


def _to_crores(mcap_inr: float) -> Decimal | None:
    """INR -> crores, Decimal 2dp. None on NaN/inf/garbage (never fabricate)."""
    if mcap_inr != mcap_inr or mcap_inr in (float("inf"), float("-inf")):
        return None
    try:
        return (Decimal(str(mcap_inr)) / _CR).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        return None


async def _load_universe(session: Any, limit: int | None) -> list[tuple[str, str]]:
    stmt = select(Stock.isin, Stock.nse_symbol).where(
        Stock.delisted_on.is_(None), Stock.nse_symbol.is_not(None)
    )
    rows = [(i, s) for i, s in (await session.execute(stmt)).all()]
    return rows[:limit] if limit else rows


async def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Populate stocks.mcap_inr_cr.")
    parser.add_argument("--limit", type=int, default=None, help="Max stocks (debug).")
    args = parser.parse_args(argv)

    async with SessionLocal() as session:
        universe = await _load_universe(session, args.limit)
    log.info("mcap.start", stocks=len(universe))

    updated = 0
    failed = 0
    for start in range(0, len(universe), _BATCH):
        batch = universe[start : start + _BATCH]
        payload: list[dict[str, Any]] = []
        for isin, symbol in batch:
            yf_symbol = f"{symbol}.NS"
            mcap_inr = await asyncio.to_thread(_fetch_mcap_sync, yf_symbol)
            cr = _to_crores(mcap_inr) if mcap_inr is not None else None
            if cr is None or cr <= 0:
                failed += 1
                continue
            payload.append({"isin": isin, "mcap": cr})
        if payload:
            async with SessionLocal() as session:
                await session.execute(_UPDATE_SQL, payload)
                await session.commit()
            updated += len(payload)
        log.info(
            "mcap.batch",
            batch_start=start,
            updated_cumulative=updated,
            failed_cumulative=failed,
        )
        await asyncio.sleep(_BATCH_DELAY_S)

    async with SessionLocal() as session:
        row = (await session.execute(_VERIFY_SQL)).first()
    total, populated, min_cr, max_cr, median_cr = row
    log.info("mcap.done", updated=updated, failed=failed, populated=populated)
    print(
        f"Done. Updated {updated}, failed/skipped {failed}.\n"
        f"Coverage: {populated}/{total} populated. "
        f"min={min_cr} cr, median={median_cr} cr, max={max_cr} cr."
    )


if __name__ == "__main__":
    asyncio.run(main())
