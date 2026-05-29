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
import zlib
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.data.scenario_patterns import detect_active_event
from backend.data_sources._http import fetch_bytes
from backend.db.repositories._helpers import today_ist
from backend.errors import DataSourceError

log = structlog.get_logger()

# Indicator keys (also the macro_signals.indicator values).
USD_INR = "usd_inr"
CRUDE = "crude_brent"
NIFTY = "nifty_50"
BOND = "india_10y"
INDIA_VIX = "india_vix"
REGIME = "regime"
SCENARIO_EVENT = "scenario_event"  # Chunk 4.13 — active macro event row

# Chunk 4.12 — market-breadth indicators (computed from existing DB tables, no
# external source). These describe internal participation, not a price level.
ADV_DECL = "advance_decline_ratio"
PCT_EMA200 = "pct_above_ema200"
NEW_HIGH_LOW = "new_high_low_ratio"

# Default regime weights (tunable placeholders consumed by the Ranking Agent
# in Phase 4.3 — how much each indicator tilts the score).
_WEIGHTS: dict[str, Decimal] = {
    USD_INR: Decimal("0.15"),
    CRUDE: Decimal("0.15"),
    NIFTY: Decimal("0.40"),
    BOND: Decimal("0.10"),
    INDIA_VIX: Decimal("0.20"),
    REGIME: Decimal("1.00"),
    # Breadth rows are informational (they drive the regime override, not the
    # weighted macro score), so they carry zero direct weight.
    ADV_DECL: Decimal("0"),
    PCT_EMA200: Decimal("0"),
    NEW_HIGH_LOW: Decimal("0"),
    # Scenario event (Chunk 4.13) is informational at the macro row level; the
    # per-sector tilt is applied by the Ranking Agent, so it carries no weight.
    SCENARIO_EVENT: Decimal("0"),
}

_STABLE_BAND_PCT = Decimal("0.5")  # |move| <= 0.5% counts as "stable"
_RBI_REPO_FALLBACK = Decimal("6.5")  # last-known RBI repo rate (bond fallback)

# India VIX fear bands (level, not trend): <15 calm, 15-20 caution, >20 fear.
_VIX_STABLE_MAX = Decimal("15")
_VIX_ELEVATED_MAX = Decimal("20")

# Breadth thresholds (Chunk 4.12).
_AD_RISING = Decimal("1.5")  # advancing/declining ratio above this -> "rising"
_AD_FALLING = Decimal("0.67")  # below this -> "falling"
_PCT_BULLISH = Decimal("65")  # % above EMA200 above this -> "bullish"
_PCT_BEARISH = Decimal("35")  # below this -> "bearish"
_NHL_STRONG = Decimal("2.0")  # new-high/new-low ratio above this -> "strong"
_NHL_WEAK = Decimal("0.5")  # below this -> "weak"
_BREADTH_RISKOFF_PCT = Decimal("30")  # < this % above EMA200 forces risk-off
_HL_NEAR = Decimal("0.98")  # within 2% of 52w high (close >= max*0.98)
_HL_NEAR_LOW = Decimal("1.02")  # within 2% of 52w low (close <= min*1.02)
_HL_LOOKBACK = 252  # trading days in the 52-week window

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


def classify_vix(value: Decimal | None) -> str:
    """India VIX fear level: stable (<15) / elevated (15-20) / spike (>20)."""
    if value is None:
        return "unknown"
    if value < _VIX_STABLE_MAX:
        return "stable"
    if value <= _VIX_ELEVATED_MAX:
        return "elevated"
    return "spike"


def advance_decline_signal(advancing: int, declining: int) -> tuple[Decimal, str]:
    """Advancing/declining ratio + signal. Div-by-zero (no decliners) -> 1.0."""
    ratio = Decimal(1) if declining == 0 else Decimal(advancing) / Decimal(declining)
    if ratio > _AD_RISING:
        sig = "rising"
    elif ratio < _AD_FALLING:
        sig = "falling"
    else:
        sig = "stable"
    return ratio, sig


def pct_above_ema200_signal(above: int, total: int) -> tuple[Decimal, str]:
    """% of stocks above EMA200 + signal. Empty universe -> 0%."""
    pct = Decimal(0) if total == 0 else Decimal(above) / Decimal(total) * 100
    if pct > _PCT_BULLISH:
        sig = "bullish"
    elif pct < _PCT_BEARISH:
        sig = "bearish"
    else:
        sig = "neutral"
    return pct, sig


def new_high_low_signal(near_high: int, near_low: int) -> tuple[Decimal, str]:
    """52w near-high/near-low ratio + signal. Div-by-zero (no lows) -> 1.0."""
    ratio = Decimal(1) if near_low == 0 else Decimal(near_high) / Decimal(near_low)
    if ratio > _NHL_STRONG:
        sig = "strong"
    elif ratio < _NHL_WEAK:
        sig = "weak"
    else:
        sig = "neutral"
    return ratio, sig


def compute_regime(readings: dict[str, MacroReading]) -> str:
    """Derive the market regime from nifty / crude / usd_inr / vix signals (pure).

    A VIX spike (>20) overrides ALL other signals and forces risk-off,
    regardless of where Nifty sits versus its 200-day MA — high fear dominates.
    Likewise, breadth below 30% above EMA200 (very few stocks participating)
    forces risk-off regardless of where the Nifty index level sits.
    """
    breadth = readings.get(PCT_EMA200)
    if (
        breadth is not None
        and breadth.value is not None
        and breadth.value < _BREADTH_RISKOFF_PCT
    ):
        log.info(
            "macro.regime.breadth_override", pct_above_ema200=float(breadth.value)
        )
        return "risk-off"

    vix = readings[INDIA_VIX].signal if INDIA_VIX in readings else "unknown"
    if vix == "spike":
        return "risk-off"

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


def pct_change_30d(closes: list[Decimal]) -> float | None:
    """% change over ~30 sessions: (latest - ref) / ref * 100, ref = close 30
    sessions back (or the earliest available). None if insufficient/zero data.
    Pure — used to feed `detect_active_event` (Chunk 4.13)."""
    if len(closes) < 2:
        return None
    latest = closes[-1]
    ref = closes[-31] if len(closes) >= 31 else closes[0]
    if ref == 0:
        return None
    return float((latest - ref) / ref * 100)


# ---------------------------------------------------------------------------
# Market breadth (Chunk 4.12) — derived from existing DB tables, no external
# source. These are internal-participation signals, not price levels.
# ---------------------------------------------------------------------------
# Advancing vs declining: compare adj_close on the two most recent distinct
# trading dates for every active stock.
_SQL_ADVANCE_DECLINE = text(
    """
    WITH latest AS (
        SELECT DISTINCT trade_date
        FROM prices_eod_adjusted
        ORDER BY trade_date DESC
        LIMIT 2
    ),
    dates AS (
        SELECT max(trade_date) AS d1, min(trade_date) AS d0 FROM latest
    ),
    moves AS (
        SELECT cur.isin, cur.adj_close AS c1, prev.adj_close AS c0
        FROM prices_eod_adjusted cur
        JOIN dates ON cur.trade_date = dates.d1
        JOIN prices_eod_adjusted prev
          ON prev.isin = cur.isin AND prev.trade_date = dates.d0
        JOIN stocks s ON s.isin = cur.isin AND s.delisted_on IS NULL
        WHERE cur.adj_close IS NOT NULL AND prev.adj_close IS NOT NULL
    )
    SELECT
        count(*) FILTER (WHERE c1 > c0) AS advancing,
        count(*) FILTER (WHERE c1 < c0) AS declining
    FROM moves
    """
)

# % above EMA200: latest technical_signals row per active stock. The column is
# a TEXT enum {'above','below','at',NULL}; the denominator is the non-null set.
_SQL_PCT_ABOVE_EMA200 = text(
    """
    WITH latest AS (
        SELECT DISTINCT ON (t.isin) t.isin, t.price_vs_ema200
        FROM technical_signals t
        JOIN stocks s ON s.isin = t.isin AND s.delisted_on IS NULL
        ORDER BY t.isin, t.computed_date DESC
    )
    SELECT
        count(*) FILTER (WHERE price_vs_ema200 = 'above') AS above,
        count(*) FILTER (WHERE price_vs_ema200 IN ('above','below','at')) AS total
    FROM latest
    """
)

# 52-week high/low: for each active stock, the 252-day rolling max/min of
# adj_close anchored at its latest trade date; count near-high vs near-low.
_SQL_NEW_HIGH_LOW = text(
    """
    WITH windowed AS (
        SELECT
            p.isin,
            p.trade_date,
            p.adj_close,
            max(p.adj_close) OVER (
                PARTITION BY p.isin ORDER BY p.trade_date DESC
                ROWS BETWEEN CURRENT ROW AND :lookback FOLLOWING
            ) AS hi,
            min(p.adj_close) OVER (
                PARTITION BY p.isin ORDER BY p.trade_date DESC
                ROWS BETWEEN CURRENT ROW AND :lookback FOLLOWING
            ) AS lo,
            row_number() OVER (
                PARTITION BY p.isin ORDER BY p.trade_date DESC
            ) AS rn
        FROM prices_eod_adjusted p
        JOIN stocks s ON s.isin = p.isin AND s.delisted_on IS NULL
        WHERE p.adj_close IS NOT NULL
    )
    SELECT
        count(*) FILTER (WHERE adj_close >= hi * :near_high) AS near_high,
        count(*) FILTER (WHERE adj_close <= lo * :near_low) AS near_low
    FROM windowed
    WHERE rn = 1
    """
)


async def _fetch_counts(
    session: AsyncSession, stmt: Any, params: dict[str, Any] | None = None
) -> tuple[int, int]:
    row = (await session.execute(stmt, params or {})).one()
    return int(row[0] or 0), int(row[1] or 0)


async def compute_breadth(session: AsyncSession) -> dict[str, MacroReading]:
    """Three market-breadth readings from existing DB tables (no external I/O).

    advance_decline_ratio, pct_above_ema200, new_high_low_ratio — each derived
    by pure SQL then classified by the unit-tested pure helpers above.
    """
    advancing, declining = await _fetch_counts(session, _SQL_ADVANCE_DECLINE)
    ad_ratio, ad_sig = advance_decline_signal(advancing, declining)

    above, total = await _fetch_counts(session, _SQL_PCT_ABOVE_EMA200)
    pct, pct_sig = pct_above_ema200_signal(above, total)

    near_high, near_low = await _fetch_counts(
        session,
        _SQL_NEW_HIGH_LOW,
        {
            "lookback": _HL_LOOKBACK - 1,
            "near_high": _HL_NEAR,
            "near_low": _HL_NEAR_LOW,
        },
    )
    nhl_ratio, nhl_sig = new_high_low_signal(near_high, near_low)

    return {
        ADV_DECL: MacroReading(
            ADV_DECL, ad_ratio, ad_sig, _WEIGHTS[ADV_DECL], "internal_db"
        ),
        PCT_EMA200: MacroReading(
            PCT_EMA200, pct, pct_sig, _WEIGHTS[PCT_EMA200], "internal_db"
        ),
        NEW_HIGH_LOW: MacroReading(
            NEW_HIGH_LOW, nhl_ratio, nhl_sig, _WEIGHTS[NEW_HIGH_LOW], "internal_db"
        ),
    }


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

    async def fetch_india_vix(self) -> MacroReading:
        latest, _closes = await self._yahoo("^INDIAVIX", INDIA_VIX)
        if latest is None:
            return self._unknown(INDIA_VIX, "yahoo")
        return MacroReading(
            INDIA_VIX, latest, classify_vix(latest), _WEIGHTS[INDIA_VIX], "yahoo"
        )

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

    async def crude_30d_change(self) -> float | None:
        """30-day % change in Brent (for scenario detection). None on any issue."""
        _latest, closes = await self._yahoo("BZ=F", CRUDE)
        return pct_change_30d(closes)

    async def usd_inr_30d_change(self) -> float | None:
        """30-day % change in USD/INR (for scenario detection). None on any issue."""
        end = today_ist()
        start = end - timedelta(days=45)  # ~31 sessions of buffer over weekends
        url = f"{_FRANKFURTER}/{start.isoformat()}..{end.isoformat()}?from=USD&to=INR"
        try:
            body, _meta = await fetch_bytes(url, cache_ttl=0)
            series = parse_frankfurter_timeseries(body.decode())
        except (DataSourceError, ValueError) as exc:
            log.warning("macro.usd_inr_change.failed", error=str(exc))
            return None
        return pct_change_30d(series)

    async def run(self, *, dry_run: bool = False) -> dict[str, MacroReading]:
        from backend.db.repositories import macro as macro_repo
        from backend.db.session import SessionLocal

        readings = {
            USD_INR: await self.fetch_usd_inr(),
            CRUDE: await self.fetch_crude(),
            NIFTY: await self.fetch_nifty(),
            BOND: await self.fetch_bond_yield(),
            INDIA_VIX: await self.fetch_india_vix(),
        }

        # Breadth is computed from the DB (read-only), so it runs even in
        # dry_run; it feeds the regime override below.
        async with SessionLocal() as session:
            readings.update(await compute_breadth(session))

            regime = compute_regime(readings)
            readings[REGIME] = MacroReading(
                REGIME, _REGIME_VALUE[regime], regime, _WEIGHTS[REGIME], "macro_agent"
            )

            # Scenario event detection (Chunk 4.13). rbi_action / us_fed_action are
            # None for now (manual detection deferred). If no event is detected we
            # store no row — fetch_active_event then returns None and the ranker
            # applies a 0 tilt (error-handling: never crash macro run on this).
            vix_reading = readings[INDIA_VIX].value
            event = detect_active_event(
                india_vix=float(vix_reading) if vix_reading is not None else None,
                crude_30d_change_pct=await self.crude_30d_change(),
                usd_inr_30d_change_pct=await self.usd_inr_30d_change(),
                rbi_action=None,
                us_fed_action=None,
            )
            if event is not None:
                log.info("macro.scenario_event.detected", event=event)
                # value is a stable, cosmetic placeholder (the signal string is the
                # real payload). crc32 is deterministic across processes, unlike
                # the spec's hash() which is PYTHONHASHSEED-salted — see lesson.
                placeholder = Decimal(zlib.crc32(event.encode()) % 1000) / Decimal(100)
                readings[SCENARIO_EVENT] = MacroReading(
                    SCENARIO_EVENT,
                    placeholder,
                    event,
                    _WEIGHTS[SCENARIO_EVENT],
                    "macro_agent",
                )

            if not dry_run:
                payload = [_to_dict(r, today_ist()) for r in readings.values()]
                await macro_repo.bulk_upsert(session, payload)
                await session.commit()

        log.info(
            "macro.run.done",
            regime=regime,
            scenario_event=event,
            dry_run=dry_run,
            **{k: v.signal for k, v in readings.items() if k not in (REGIME, SCENARIO_EVENT)},
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
