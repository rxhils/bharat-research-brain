"""Tests for intraday signals (Chunk 2.3) — pure math + Redis write, offline.

VWAP distance, volume z-score, and 5-tick momentum are pure functions. The
service's on_tick is exercised with an injected FakeRedis + baselines, so no
network or DB is touched.
"""
from __future__ import annotations

import json
from decimal import Decimal

import pytest

from backend.services.intraday_signals import (
    IntradaySignalService,
    momentum_slope,
    volume_zscore,
    vwap_distance_pct,
)
from backend.services.live_feed import TickState

D = Decimal


class FakeRedis:
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


def _tick(isin: str, ltp: str, volume: int) -> TickState:
    v = D(ltp)
    return TickState(isin=isin, ltp=v, open=v, high=v, low=v, volume=volume)


# ---------------------------------------------------------------------------
# 1. VWAP distance %
# ---------------------------------------------------------------------------
def test_vwap_distance() -> None:
    assert vwap_distance_pct(D("110"), D("100")) == D("10")
    assert vwap_distance_pct(D("90"), D("100")) == D("-10")
    assert vwap_distance_pct(D("100"), D("0")) == D("0")  # guard div-by-zero


# ---------------------------------------------------------------------------
# 2. Volume z-score
# ---------------------------------------------------------------------------
def test_volume_zscore() -> None:
    assert volume_zscore(120.0, 100.0, 10.0) == pytest.approx(2.0)
    assert volume_zscore(80.0, 100.0, 10.0) == pytest.approx(-2.0)
    assert volume_zscore(100.0, 100.0, 0.0) == 0.0  # std 0 → 0
    assert volume_zscore(100.0, 100.0, None) == 0.0  # missing baseline → 0


# ---------------------------------------------------------------------------
# 3. 5-tick momentum (linear-regression slope)
# ---------------------------------------------------------------------------
def test_momentum_slope() -> None:
    assert momentum_slope([D(1), D(2), D(3), D(4), D(5)]) == pytest.approx(1.0)
    assert momentum_slope([D(5), D(4), D(3), D(2), D(1)]) == pytest.approx(-1.0)
    assert momentum_slope([D(3), D(3), D(3)]) == pytest.approx(0.0)
    assert momentum_slope([D(7)]) == 0.0  # <2 points
    assert momentum_slope([]) == 0.0


# ---------------------------------------------------------------------------
# 4. on_tick writes intraday:{isin} with the full signal shape + TTL
# ---------------------------------------------------------------------------
async def test_on_tick_writes_intraday() -> None:
    fake = FakeRedis()
    svc = IntradaySignalService(redis=fake, baselines={"INE0": (1000.0, 100.0)})
    await svc.on_tick("INE0", _tick("INE0", "100", 500))
    await svc.on_tick("INE0", _tick("INE0", "102", 1500))

    key = "intraday:INE0"
    assert key in fake.store
    assert fake.ttl[key] == 300
    p = json.loads(fake.store[key])
    assert set(p) == {
        "vwap",
        "vwap_distance_pct",
        "volume_zscore",
        "momentum_5tick",
        "session_high",
        "session_low",
        "tick_count",
        "last_updated",
    }
    assert p["tick_count"] == 2


# ---------------------------------------------------------------------------
# 5. VWAP is volume-weighted across ticks (uses incremental volume)
# ---------------------------------------------------------------------------
async def test_vwap_volume_weighted() -> None:
    fake = FakeRedis()
    svc = IntradaySignalService(redis=fake, baselines={})
    # tick1: price 100, cum vol 100 (dv=100); tick2: price 200, cum vol 300 (dv=200)
    await svc.on_tick("X", _tick("X", "100", 100))
    await svc.on_tick("X", _tick("X", "200", 300))
    p = json.loads(fake.store["intraday:X"])
    # vwap = (100*100 + 200*200) / 300 = 50000/300 = 166.67
    assert p["vwap"] == pytest.approx(166.67, abs=0.01)


# ---------------------------------------------------------------------------
# 6. session high/low track extremes across ticks
# ---------------------------------------------------------------------------
async def test_session_high_low() -> None:
    fake = FakeRedis()
    svc = IntradaySignalService(redis=fake, baselines={})
    for px, vol in [("100", 100), ("130", 200), ("90", 300), ("110", 400)]:
        await svc.on_tick("Y", _tick("Y", px, vol))
    p = json.loads(fake.store["intraday:Y"])
    assert p["session_high"] == pytest.approx(130.0)
    assert p["session_low"] == pytest.approx(90.0)
