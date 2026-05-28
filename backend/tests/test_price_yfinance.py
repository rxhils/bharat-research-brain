"""Tests for the Price Agent's yfinance EOD fallback (nightly automation).

The fallback fills `prices_eod` from yfinance when the manual bhavcopy was not
loaded. It is gated by `settings.yfinance_price_fallback` and by a presence
check: if today already has >=400 rows (bhavcopy loaded manually), it skips.

All synthetic — no network, no DB. The yfinance client and the symbol/count
lookups are faked / monkeypatched. Dry-run asserts no inserts.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from backend.agents import price as price_mod
from backend.agents.price import PriceAgent, PriceResult
from backend.data_sources.yfinance_client import PriceBar
from backend.db.repositories import prices as prices_repo

KNOWN = "INE040A01034"  # HDFCBANK


class _FakeYf:
    """Records every yf_symbol requested; returns canned bars."""

    def __init__(self, bars_by_symbol: dict[str, list[PriceBar]]) -> None:
        self.bars_by_symbol = bars_by_symbol
        self.calls: list[str] = []

    async def fetch_price_history(
        self, yf_symbol: str, *, lookback_days: int = 5
    ) -> list[PriceBar]:
        self.calls.append(yf_symbol)
        return self.bars_by_symbol.get(yf_symbol, [])


def _bar(d: date = date(2026, 5, 29)) -> PriceBar:
    return PriceBar(
        trade_date=d,
        open=Decimal("100.0"),
        high=Decimal("110.0"),
        low=Decimal("95.0"),
        close=Decimal("105.0"),
        volume=1000,
    )


def _agent(yf: _FakeYf, symbols: list[tuple[str, str | None]]) -> PriceAgent:
    agent = PriceAgent(yf_client=yf)

    async def _fake_symbols(session: object) -> list[tuple[str, str | None]]:
        return symbols

    agent._load_symbols = _fake_symbols  # type: ignore[method-assign]
    return agent


# ---------------------------------------------------------------------------
# 1. Flag off -> no fetch, no insert
# ---------------------------------------------------------------------------
async def test_fallback_disabled_is_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(price_mod.settings, "yfinance_price_fallback", False)
    yf = _FakeYf({})
    agent = _agent(yf, [(KNOWN, "HDFCBANK")])

    result = await agent.fetch_eod_yfinance(dry_run=True)

    assert yf.calls == []
    assert result.rows_inserted == 0
    assert isinstance(result, PriceResult)


# ---------------------------------------------------------------------------
# 2. Bhavcopy already loaded (>=400 rows today) -> skip, no fetch
# ---------------------------------------------------------------------------
async def test_skips_when_bhavcopy_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(price_mod.settings, "yfinance_price_fallback", True)

    async def fake_count(session, trade_date):  # noqa: ANN001
        return 450

    monkeypatch.setattr(prices_repo, "count_for_date", fake_count)
    yf = _FakeYf({})
    agent = _agent(yf, [(KNOWN, "HDFCBANK")])

    result = await agent.fetch_eod_yfinance(dry_run=True)

    assert yf.calls == []  # presence gate short-circuits the fetch
    assert result.rows_inserted == 0


# ---------------------------------------------------------------------------
# 3. Bhavcopy missing (<400 rows) -> fetch all symbols with ".NS", insert
# ---------------------------------------------------------------------------
async def test_fetches_and_inserts_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(price_mod.settings, "yfinance_price_fallback", True)

    async def fake_count(session, trade_date):  # noqa: ANN001
        return 0

    captured: dict[str, object] = {}

    async def spy_bulk(session, rows, *, ingestion_run_id, source="nse_bhavcopy"):  # noqa: ANN001
        captured["rows"] = list(rows)
        captured["source"] = source
        captured["run_id"] = ingestion_run_id
        return len(rows)

    monkeypatch.setattr(prices_repo, "count_for_date", fake_count)
    monkeypatch.setattr(prices_repo, "bulk_insert", spy_bulk)

    yf = _FakeYf({"HDFCBANK.NS": [_bar()]})
    agent = _agent(yf, [(KNOWN, "HDFCBANK")])

    result = await agent.fetch_eod_yfinance(dry_run=False, ingestion_run_id=7)

    assert yf.calls == ["HDFCBANK.NS"]  # nse_symbol + ".NS"
    assert captured["source"] == "yfinance"
    assert captured["run_id"] == 7
    assert result.rows_inserted == 1
    assert result.rows_ready == 1


# ---------------------------------------------------------------------------
# 4. Symbols with no nse_symbol are skipped (no ".NS" of None)
# ---------------------------------------------------------------------------
async def test_skips_rows_without_nse_symbol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(price_mod.settings, "yfinance_price_fallback", True)

    async def fake_count(session, trade_date):  # noqa: ANN001
        return 0

    monkeypatch.setattr(prices_repo, "count_for_date", fake_count)
    yf = _FakeYf({"HDFCBANK.NS": [_bar()]})
    agent = _agent(yf, [(KNOWN, "HDFCBANK"), ("INE999X01019", None)])

    await agent.fetch_eod_yfinance(dry_run=True)

    assert yf.calls == ["HDFCBANK.NS"]  # the None-symbol stock never fetched


# ---------------------------------------------------------------------------
# 5. Dry-run performs no inserts even when bars are fetched
# ---------------------------------------------------------------------------
async def test_dry_run_no_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(price_mod.settings, "yfinance_price_fallback", True)
    calls = {"n": 0}

    async def fake_count(session, trade_date):  # noqa: ANN001
        return 0

    async def spy_bulk(session, rows, *, ingestion_run_id, source="nse_bhavcopy"):  # noqa: ANN001
        calls["n"] += 1
        return len(rows)

    monkeypatch.setattr(prices_repo, "count_for_date", fake_count)
    monkeypatch.setattr(prices_repo, "bulk_insert", spy_bulk)
    yf = _FakeYf({"HDFCBANK.NS": [_bar()]})
    agent = _agent(yf, [(KNOWN, "HDFCBANK")])

    result = await agent.fetch_eod_yfinance(dry_run=True)

    assert calls["n"] == 0
    assert result.rows_inserted == 0
    assert result.rows_ready == 1  # bars were fetched + filtered, just not written
