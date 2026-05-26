"""Macro Agent (Chunk 4.1) — market-regime context for the Ranking Agent.

Pulls four public, no-auth, permitted macro indicators (CLAUDE.md §2 rule 5 —
Frankfurter FX is public ECB data; Yahoo Finance is what yfinance wraps) and
derives a market regime (risk-on / risk-off / neutral). No NSE scraping.

Each indicator is fetched independently and resiliently: a down/blocked source
yields signal='unknown' (never a fabricated value, never a crash). The bond
yield additionally falls back to the last-known RBI repo rate (6.5%).

The trend + regime logic (`classify_trend`, `compute_regime`) is pure and unit
tested; only `fetch_*` / `run` do I/O. Results are upserted into
`macro_signals`, including a special `indicator='regime'` row.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import structlog

from backend.data_sources._http import fetch_bytes
from backend.db.repositories._helpers import today_ist
from backend.errors import DataSourceError

log = structlog.get_logger()

# Indicator keys (also the macro_signals.indicator values).
USD_INR = "usd_inr"
CRUDE = "crude_brent"
NIFTY = "nifty_50"
BOND = "india_10y"
REGIME = "regime"

# Default regime weights (tunable placeholders consumed by the Ranking Agent
# in Phase 4.3 — how much each indicator tilts the score).
_WEIGHTS: dict[str, Decimal] = {
    USD_INR: Decimal("0.15"),
    CRUDE: Decimal("0.15"),
    NIFTY: Decimal("0.40"),
    BOND: Decimal("0.10"),
    REGIME: Decimal("1.00"),
}

_STABLE_BAND_PCT = Decimal("0.5")  # |move| <= 0.5% counts as "stable"
_RBI_REPO_FALLBACK = Decimal("6.5")  # last-known RBI repo rate (bond fallback)

_FRANKFURTER = "https://api.frankfurter.app"
_YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart"

# Regime numeric encoding for the special `regime` row's `value`.
_REGIME_VALUE = {
    "risk-on": Decimal("1"),
    "neutral": Decimal("0"),
    "risk-off": Decimal("-1"),
}


@dataclass(frozen=True)
class MacroReading:
    indicator: str
    value: Decimal | None
    signal: str  # rising | falling | stable | unknown (or risk-* for regime)
    regime_weight: Decimal
    source: str


# ---------------------------------------------------------------------------
# Pure logic
# ---------------------------------------------------------------------------
def classify_trend(
    current: Decimal | None,
    baseline: Decimal | None,
    *,
    stable_pct: Decimal = _STABLE_BAND_PCT,
) -> str:
    """rising / falling / stable vs a baseline; unknown if either is missing."""
    if current is None or baseline is None or baseline == 0:
        return "unknown"
    pct = (current - baseline) / baseline * 100
    if abs(pct) <= stable_pct:
        return "stable"
    return "rising" if pct > 0 else "falling"


def compute_regime(readings: dict[str, MacroReading]) -> str:
    """Derive the market regime from nifty / crude / usd_inr signals (pure)."""
    nifty = readings[NIFTY].signal if NIFTY in readings else "unknown"
    crude = readings[CRUDE].signal if CRUDE in readings else "unknown"
    usd = readings[USD_INR].signal if USD_INR in readings else "unknown"

    if nifty == "falling" or crude == "rising" or usd == "rising":
        return "risk-off"
    if (
        nifty in ("rising", "stable")
        and crude in ("stable", "falling")
        and usd in ("stable", "falling")
    ):
        return "risk-on"
    return "neutral"


def parse_frankfurter_timeseries(text: str) -> list[Decimal]:
    """Frankfurter {"rates": {date: {CCY: rate}}} -> rates ordered by date asc."""
    data = json.loads(text)
    rates = data.get("rates", {})
    out: list[Decimal] = []
    for d in sorted(rates):
        inner = rates[d]
        if isinstance(inner, dict):
            for v in inner.values():
                if v is not None:
                    out.append(Decimal(str(v)))
                break
    return out


def parse_yahoo_chart(text: str) -> tuple[Decimal | None, list[Decimal]]:
    """Yahoo chart JSON -> (latest price, daily closes). Tolerant of gaps/empty."""
    data = json.loads(text)
    result = (data.get("chart") or {}).get("result") or []
    if not result:
        return None, []
    node = result[0]
    meta = node.get("meta") or {}
    latest = meta.get("regularMarketPrice")
    quote = ((node.get("indicators") or {}).get("quote") or [{}])[0]
    closes = [Decimal(str(c)) for c in (quote.get("close") or []) if c is not None]
    latest_dec = (
        Decimal(str(latest))
        if latest is not None
        else (closes[-1] if closes else None)
    )
    return latest_dec, closes


def _mean(values: list[Decimal]) -> Decimal | None:
    return sum(values, Decimal(0)) / len(values) if values else None


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class MacroAgent:
    name = "macro"

    async def fetch_usd_inr(self) -> MacroReading:
        end = today_ist()
        start = end - timedelta(days=30)
        url = f"{_FRANKFURTER}/{start.isoformat()}..{end.isoformat()}?from=USD&to=INR"
        try:
            body, _meta = await fetch_bytes(url, cache_ttl=0)
            series = parse_frankfurter_timeseries(body.decode())
        except (DataSourceError, ValueError) as exc:
            log.warning("macro.usd_inr.failed", error=str(exc))
            return self._unknown(USD_INR, "frankfurter")
        if not series:
            return self._unknown(USD_INR, "frankfurter")
        latest = series[-1]
        signal = classify_trend(latest, _mean(series))
        return MacroReading(USD_INR, latest, signal, _WEIGHTS[USD_INR], "frankfurter")

    async def fetch_crude(self) -> MacroReading:
        latest, closes = await self._yahoo("BZ=F", CRUDE)
        if latest is None:
            return self._unknown(CRUDE, "yahoo")
        signal = classify_trend(latest, _mean(closes[-30:]))  # 30-day baseline
        return MacroReading(CRUDE, latest, signal, _WEIGHTS[CRUDE], "yahoo")

    async def fetch_nifty(self) -> MacroReading:
        latest, closes = await self._yahoo("^NSEI", NIFTY)
        if latest is None:
            return self._unknown(NIFTY, "yahoo")
        # Above 200-day MA = positive (rising); below = negative (falling).
        signal = classify_trend(latest, _mean(closes[-200:]))
        return MacroReading(NIFTY, latest, signal, _WEIGHTS[NIFTY], "yahoo")

    async def fetch_bond_yield(self) -> MacroReading:
        latest, closes = await self._yahoo("^INBMK10Y", BOND)
        if latest is None:
            # Fallback: last-known RBI repo rate, flagged unknown (not fabricated).
            return MacroReading(
                BOND, _RBI_REPO_FALLBACK, "unknown", _WEIGHTS[BOND], "fallback_rbi_repo"
            )
        signal = classify_trend(latest, _mean(closes[-30:]))
        return MacroReading(BOND, latest, signal, _WEIGHTS[BOND], "yahoo")

    async def _yahoo(
        self, symbol: str, indicator: str
    ) -> tuple[Decimal | None, list[Decimal]]:
        url = f"{_YAHOO_CHART}/{symbol}?range=1y&interval=1d"
        try:
            body, _meta = await fetch_bytes(url, cache_ttl=0)
            return parse_yahoo_chart(body.decode())
        except (DataSourceError, ValueError) as exc:
            log.warning("macro.yahoo.failed", indicator=indicator, error=str(exc))
            return None, []

    @staticmethod
    def _unknown(indicator: str, source: str) -> MacroReading:
        return MacroReading(indicator, None, "unknown", _WEIGHTS[indicator], source)

    async def run(self, *, dry_run: bool = False) -> dict[str, MacroReading]:
        readings = {
            USD_INR: await self.fetch_usd_inr(),
            CRUDE: await self.fetch_crude(),
            NIFTY: await self.fetch_nifty(),
            BOND: await self.fetch_bond_yield(),
        }
        regime = compute_regime(readings)
        readings[REGIME] = MacroReading(
            REGIME, _REGIME_VALUE[regime], regime, _WEIGHTS[REGIME], "macro_agent"
        )

        if not dry_run:
            from backend.db.repositories import macro as macro_repo
            from backend.db.session import SessionLocal

            payload = [_to_dict(r, today_ist()) for r in readings.values()]
            async with SessionLocal() as session:
                await macro_repo.bulk_upsert(session, payload)
                await session.commit()

        log.info(
            "macro.run.done",
            regime=regime,
            dry_run=dry_run,
            **{k: v.signal for k, v in readings.items() if k != REGIME},
        )
        return readings


def _to_dict(r: MacroReading, computed_date: date) -> dict[str, Any]:
    return {
        "indicator": r.indicator,
        "computed_date": computed_date,
        "value": r.value,
        "signal": r.signal,
        "regime_weight": r.regime_weight,
        "source": r.source,
    }
