"""Intraday signals from live Redis ticks (Chunk 2.3).

Computes, per stock, three signals and writes them to `intraday:{isin}` (JSON,
5-min TTL):
  - VWAP distance %  : (ltp - session VWAP) / VWAP × 100
  - volume z-score   : (session volume - 20d avg) / 20d std  (one DB read at start)
  - 5-tick momentum  : linear-regression slope of the last 5 tick prices

The math functions are pure (no I/O). State (running VWAP accumulator, session
high/low, recent prices) lives in-process alongside the LiveFeedService that
drives `on_tick`. No DB reads per tick (only the baseline load at startup).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

import structlog

from backend.config import settings
from backend.db.repositories._helpers import IST
from backend.services.live_feed import TickState

log = structlog.get_logger()

INTRADAY_PREFIX = "intraday:"
TTL_SECONDS = 300
_MOMENTUM_WINDOW = 5


# ---------------------------------------------------------------------------
# Pure signal math
# ---------------------------------------------------------------------------
def vwap_distance_pct(ltp: Decimal, vwap: Decimal) -> Decimal:
    if vwap == 0:
        return Decimal(0)
    return (ltp - vwap) / vwap * 100


def volume_zscore(current: float, avg: float, std: float | None) -> float:
    if not std:  # None or 0 → no meaningful z
        return 0.0
    return (current - avg) / std


def momentum_slope(prices: list[Decimal]) -> float:
    """Linear-regression slope of evenly-spaced prices (x = 0..n-1)."""
    n = len(prices)
    if n < 2:
        return 0.0
    xbar = (n - 1) / 2
    ys = [float(p) for p in prices]
    ybar = sum(ys) / n
    num = sum((i - xbar) * (ys[i] - ybar) for i in range(n))
    den = sum((i - xbar) ** 2 for i in range(n))
    return num / den if den else 0.0


@dataclass
class SignalState:
    sum_pv: Decimal = Decimal(0)
    sum_v: int = 0
    prev_volume: int = 0
    session_high: Decimal | None = None
    session_low: Decimal | None = None
    recent_prices: list[Decimal] = field(default_factory=list)
    tick_count: int = 0


@dataclass
class IntradaySignals:
    vwap: Decimal
    vwap_distance_pct: Decimal
    volume_zscore: float
    momentum_5tick: float
    session_high: Decimal
    session_low: Decimal
    tick_count: int


class IntradaySignalService:
    def __init__(
        self,
        *,
        redis: Any | None = None,
        baselines: dict[str, tuple[float, float]] | None = None,
    ) -> None:
        self._redis = redis
        self._baselines = baselines or {}  # isin -> (avg_volume, std_volume)
        self._states: dict[str, SignalState] = {}

    async def _client(self) -> Any:
        if self._redis is None:
            from redis.asyncio import Redis

            self._redis = Redis.from_url(settings.redis_url, decode_responses=True)
        return self._redis

    async def load_volume_baselines(
        self, isins: list[str] | None = None
    ) -> dict[str, tuple[float, float]]:
        """One DB read: 20-day avg + sample std of daily volume per ISIN."""
        from sqlalchemy import func, select

        from backend.db.models import PriceEod
        from backend.db.session import SessionLocal

        rn = func.row_number().over(
            partition_by=PriceEod.isin, order_by=PriceEod.trade_date.desc()
        ).label("rn")
        sub = (
            select(
                PriceEod.isin.label("isin"),
                PriceEod.volume.label("volume"),
                rn,
            )
            .where(PriceEod.volume.is_not(None))
            .subquery()
        )
        stmt = (
            select(
                sub.c.isin,
                func.avg(sub.c.volume),
                func.stddev_samp(sub.c.volume),
            )
            .where(sub.c.rn <= 20)
            .group_by(sub.c.isin)
        )
        async with SessionLocal() as session:
            rows = (await session.execute(stmt)).all()
        self._baselines = {
            isin: (
                float(avg) if avg is not None else 0.0,
                float(std) if std is not None else 0.0,
            )
            for isin, avg, std in rows
        }
        log.info("intraday.baselines.loaded", count=len(self._baselines))
        return self._baselines

    def compute_signals(self, isin: str, tick: TickState) -> IntradaySignals:
        st = self._states[isin]
        vwap = (st.sum_pv / st.sum_v) if st.sum_v > 0 else tick.ltp
        avg, std = self._baselines.get(isin, (0.0, 0.0))
        return IntradaySignals(
            vwap=vwap,
            vwap_distance_pct=vwap_distance_pct(tick.ltp, vwap),
            volume_zscore=volume_zscore(float(tick.volume), avg, std),
            momentum_5tick=momentum_slope(st.recent_prices),
            session_high=st.session_high if st.session_high is not None else tick.ltp,
            session_low=st.session_low if st.session_low is not None else tick.ltp,
            tick_count=st.tick_count,
        )

    async def on_tick(self, isin: str, tick: TickState) -> None:
        st = self._states.get(isin)
        if st is None:
            st = SignalState()
            self._states[isin] = st
        dv = tick.volume - st.prev_volume
        if dv < 0:  # cumulative volume reset (new session) → restart accumulation
            dv = tick.volume
        st.sum_pv += tick.ltp * Decimal(dv)
        st.sum_v += dv
        st.prev_volume = tick.volume
        st.session_high = (
            tick.ltp if st.session_high is None else max(st.session_high, tick.ltp)
        )
        st.session_low = (
            tick.ltp if st.session_low is None else min(st.session_low, tick.ltp)
        )
        st.recent_prices.append(tick.ltp)
        if len(st.recent_prices) > _MOMENTUM_WINDOW:
            st.recent_prices.pop(0)
        st.tick_count += 1

        sig = self.compute_signals(isin, tick)
        payload = {
            "vwap": float(sig.vwap),
            "vwap_distance_pct": float(sig.vwap_distance_pct),
            "volume_zscore": round(sig.volume_zscore, 4),
            "momentum_5tick": round(sig.momentum_5tick, 6),
            "session_high": float(sig.session_high),
            "session_low": float(sig.session_low),
            "tick_count": sig.tick_count,
            "last_updated": datetime.now(IST).isoformat(),
        }
        client = await self._client()
        await client.set(
            f"{INTRADAY_PREFIX}{isin}", json.dumps(payload), ex=TTL_SECONDS
        )

    async def status(
        self, *, isin: str | None = None, limit: int = 10
    ) -> list[tuple[str, dict[str, Any]]]:
        client = await self._client()
        if isin is not None:
            v = await client.get(f"{INTRADAY_PREFIX}{isin}")
            return [(isin, json.loads(v))] if v else []
        keys = await client.keys(f"{INTRADAY_PREFIX}*")
        out: list[tuple[str, dict[str, Any]]] = []
        for k in keys:
            v = await client.get(k)
            if v:
                out.append((k.removeprefix(INTRADAY_PREFIX), json.loads(v)))
        out.sort(key=lambda kv: abs(kv[1].get("volume_zscore", 0.0)), reverse=True)
        return out[:limit]
