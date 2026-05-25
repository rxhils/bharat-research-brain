"""Tests for the live price feed (Chunk 2.2), DEMO mode — no network, no DB.

The random-walk tick step is pure; Redis writes go through an injected fake
client, so the whole DEMO path is unit-testable offline.
"""
from __future__ import annotations

import json
import random
from decimal import Decimal

from backend.services.live_feed import (
    LiveFeedService,
    TickState,
    random_walk_step,
)

D = Decimal


class FakeRedis:
    """Minimal async Redis stand-in recording set/ttl, supporting keys()."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttl: dict[str, int | None] = {}

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = value
        self.ttl[key] = ex

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def keys(self, pattern: str) -> list[str]:
        prefix = pattern.rstrip("*")
        return [k for k in self.store if k.startswith(prefix)]

    async def aclose(self) -> None:  # pragma: no cover
        pass


def _state(isin: str = "INE000A01010", ltp: str = "100") -> TickState:
    v = D(ltp)
    return TickState(isin=isin, ltp=v, open=v, high=v, low=v, volume=0)


# ---------------------------------------------------------------------------
# 1. Random-walk invariants
# ---------------------------------------------------------------------------
def test_random_walk_invariants() -> None:
    rng = random.Random(42)
    s = _state(ltp="500")
    for _ in range(200):
        s = random_walk_step(s, rng)
        assert s.ltp > 0
        assert s.low <= s.ltp <= s.high
        assert s.high >= s.low
        assert s.volume >= 0


def test_random_walk_volume_grows() -> None:
    rng = random.Random(1)
    s = _state(ltp="500")
    s1 = random_walk_step(s, rng)
    s2 = random_walk_step(s1, rng)
    assert s2.volume > s1.volume > s.volume


# ---------------------------------------------------------------------------
# 2. Deterministic with a fixed seed
# ---------------------------------------------------------------------------
def test_random_walk_deterministic() -> None:
    a = _state(ltp="500")
    b = _state(ltp="500")
    rng_a, rng_b = random.Random(7), random.Random(7)
    for _ in range(50):
        a = random_walk_step(a, rng_a)
        b = random_walk_step(b, rng_b)
    assert a == b


# ---------------------------------------------------------------------------
# 3. on_tick writes the Redis key with TTL 300 and correct JSON shape
# ---------------------------------------------------------------------------
async def test_on_tick_writes_redis() -> None:
    fake = FakeRedis()
    svc = LiveFeedService(redis=fake, mode="demo", symbols=["INE000A01010"])
    tick = TickState("INE000A01010", D("101.50"), D("100"), D("102"), D("99"), 1234)
    await svc.on_tick(tick)

    key = "live:INE000A01010"
    assert key in fake.store
    assert fake.ttl[key] == 300
    payload = json.loads(fake.store[key])
    assert set(payload) == {"ltp", "open", "high", "low", "volume", "timestamp"}
    assert payload["ltp"] == 101.5
    assert payload["volume"] == 1234
    assert isinstance(payload["timestamp"], str)


# ---------------------------------------------------------------------------
# 4. One demo round emits a tick per symbol
# ---------------------------------------------------------------------------
async def test_demo_round_emits_all_symbols() -> None:
    fake = FakeRedis()
    symbols = ["INE000A01010", "INE111B01011", "INE222C01012"]
    svc = LiveFeedService(
        redis=fake, mode="demo", symbols=symbols, start_prices={}, seed=5
    )
    await svc.connect()
    n = await svc._demo_round()
    assert n == 3
    assert all(f"live:{i}" in fake.store for i in symbols)


# ---------------------------------------------------------------------------
# 5. connect writes live:meta with mode + symbol_count
# ---------------------------------------------------------------------------
async def test_connect_writes_meta() -> None:
    fake = FakeRedis()
    symbols = ["INE000A01010", "INE111B01011"]
    svc = LiveFeedService(redis=fake, mode="demo", symbols=symbols, start_prices={})
    await svc.connect()
    assert "live:meta" in fake.store
    meta = json.loads(fake.store["live:meta"])
    assert meta["mode"] == "demo"
    assert meta["symbol_count"] == 2
    assert "started_at" in meta


# ---------------------------------------------------------------------------
# 6. start_prices seed the opening ltp; one step stays near the seed
# ---------------------------------------------------------------------------
async def test_start_prices_seed_ltp() -> None:
    fake = FakeRedis()
    svc = LiveFeedService(
        redis=fake,
        mode="demo",
        symbols=["INE000A01010"],
        start_prices={"INE000A01010": D("2500")},
        seed=3,
    )
    await svc.connect()
    await svc._demo_round()
    payload = json.loads(fake.store["live:INE000A01010"])
    assert 2400 < payload["ltp"] < 2600
