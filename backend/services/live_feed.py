"""Live price feed → Redis (Chunk 2.2).

Streams per-stock ticks into Redis keys `live:{isin}` (JSON, 5-min TTL) plus
a `live:meta` summary. DEMO mode (synthetic random-walk, the default and only
runnable path here) needs no broker; `fyers` mode is a thin lazy adapter that
raises clearly until the SDK + credentials are configured.

Shutdown: `live stop` sets `live:stop` = "1"; `stream()` polls it each round
and exits cleanly. Read-only quotes only — no order placement (CLAUDE.md §2
rule 1). Redis is the sole sink; nothing is written to prices_eod (bhavcopy
stays the EOD source).
"""
from __future__ import annotations

import asyncio
import json
import random
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

import structlog

from backend.config import settings
from backend.db.repositories._helpers import IST

log = structlog.get_logger()

LIVE_PREFIX = "live:"
META_KEY = "live:meta"
STOP_KEY = "live:stop"
TTL_SECONDS = 300
_CENT = Decimal("0.01")
_MAX_STEP = 0.005  # ±0.5% per tick


@dataclass
class TickState:
    isin: str
    ltp: Decimal
    open: Decimal
    high: Decimal
    low: Decimal
    volume: int


def random_walk_step(state: TickState, rng: random.Random) -> TickState:
    """One synthetic tick: ±0.5% move on ltp, rolling high/low, growing volume."""
    pct = Decimal(str(rng.uniform(-_MAX_STEP, _MAX_STEP)))
    new_ltp = (state.ltp * (Decimal(1) + pct)).quantize(_CENT)
    if new_ltp <= 0:
        new_ltp = state.ltp
    return TickState(
        isin=state.isin,
        ltp=new_ltp,
        open=state.open,
        high=max(state.high, new_ltp),
        low=min(state.low, new_ltp),
        volume=state.volume + rng.randint(100, 10_000),
    )


class LiveFeedService:
    def __init__(
        self,
        *,
        redis: Any | None = None,
        mode: str | None = None,
        symbols: list[str] | None = None,
        start_prices: dict[str, Decimal] | None = None,
        seed: int | None = None,
        signal_service: Any | None = None,
    ) -> None:
        self.mode = (mode or settings.live_feed_mode).lower()
        self._redis = redis
        self._symbols = symbols
        self._start_prices = start_prices
        self._rng = random.Random(seed)
        self._states: dict[str, TickState] = {}
        self._running = False
        self._signal_service = signal_service

    @property
    def symbol_count(self) -> int:
        return len(self._symbols or [])

    async def _client(self) -> Any:
        if self._redis is None:
            from redis.asyncio import Redis

            self._redis = Redis.from_url(settings.redis_url, decode_responses=True)
        return self._redis

    async def connect(self) -> None:
        """Load the symbol universe, seed states, clear the stop flag, publish meta."""
        client = await self._client()
        if self._symbols is None:
            self._symbols, self._start_prices = await self._load_universe()
        starts = self._start_prices or {}
        self._states = {}
        for isin in self._symbols:
            base = starts.get(isin) or Decimal("100")
            self._states[isin] = TickState(isin, base, base, base, base, 0)
        meta = {
            "started_at": datetime.now(IST).isoformat(),
            "symbol_count": len(self._symbols),
            "mode": self.mode,
        }
        await client.set(META_KEY, json.dumps(meta))
        await client.set(STOP_KEY, "0")
        if self._signal_service is not None:
            await self._signal_service.load_volume_baselines(self._symbols)
        log.info("live.connect", mode=self.mode, symbols=len(self._symbols))

    async def on_tick(self, tick: TickState) -> None:
        client = await self._client()
        payload = {
            "ltp": float(tick.ltp),
            "open": float(tick.open),
            "high": float(tick.high),
            "low": float(tick.low),
            "volume": tick.volume,
            "timestamp": datetime.now(IST).isoformat(),
        }
        await client.set(
            f"{LIVE_PREFIX}{tick.isin}", json.dumps(payload), ex=TTL_SECONDS
        )
        if self._signal_service is not None:
            await self._signal_service.on_tick(tick.isin, tick)

    async def _demo_round(self) -> int:
        for isin in self._symbols or []:
            self._states[isin] = random_walk_step(self._states[isin], self._rng)
            await self.on_tick(self._states[isin])
        return len(self._symbols or [])

    async def stream(self, *, interval: float = 2.0, duration: float = 0.0) -> int:
        """Run the tick loop until the stop flag is set (or duration elapses)."""
        if self.mode != "demo":
            raise NotImplementedError(
                f"LIVE_FEED_MODE={self.mode!r} requires the fyers-apiv3 SDK + "
                "broker credentials (not configured). Use LIVE_FEED_MODE=demo."
            )
        client = await self._client()
        self._running = True
        rounds = 0
        loop = asyncio.get_event_loop()
        started = loop.time()
        try:
            while self._running:
                await self._demo_round()
                rounds += 1
                if await client.get(STOP_KEY) == "1":
                    log.info("live.stream.stop_signal")
                    break
                if duration and (loop.time() - started) >= duration:
                    break
                await asyncio.sleep(interval)
        finally:
            self._running = False
        log.info("live.stream.done", rounds=rounds)
        return rounds

    async def disconnect(self) -> None:
        self._running = False
        if self._redis is not None:
            try:
                await self._redis.set(STOP_KEY, "1")
            except Exception as exc:  # never raise on shutdown
                log.warning("live.disconnect.error", error=str(exc))
        log.info("live.disconnect")

    async def status(self) -> dict[str, Any]:
        client = await self._client()
        meta_raw = await client.get(META_KEY)
        keys = await client.keys(f"{LIVE_PREFIX}*")
        live_keys = sorted(k for k in keys if k not in (META_KEY, STOP_KEY))
        samples: list[tuple[str, Any, Any]] = []
        for k in live_keys[:5]:
            v = await client.get(k)
            if v:
                p = json.loads(v)
                samples.append((k, p.get("ltp"), p.get("timestamp")))
        return {
            "meta": json.loads(meta_raw) if meta_raw else None,
            "live_count": len(live_keys),
            "samples": samples,
        }

    async def _load_universe(self) -> tuple[list[str], dict[str, Decimal]]:
        from sqlalchemy import select

        from backend.db.models import PriceEod, Stock
        from backend.db.session import SessionLocal

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
            rows = (
                await session.execute(
                    select(PriceEod.isin, PriceEod.close)
                    .distinct(PriceEod.isin)
                    .order_by(PriceEod.isin, PriceEod.trade_date.desc())
                )
            ).all()
        starts = {isin: close for isin, close in rows if close is not None}
        return isins, starts
