"""Per-date technical-only score reconstructor (Chunk 5.2 STEP 2b).

mle no-lookahead invariant: every score is computed from `closes`/`volumes` whose
last bar is the simulation date D. The caller MUST pass series ending at D and
nothing past it; the engine cannot tell the difference, so the runner enforces
this with `WHERE trade_date <= :as_of` in the SQL fetch.

Mirrors `score_technical` from `backend.agents.ranking`: RSI zone base + EMA200
position + EMA cross + MACD histogram + 52-week proximity + volume ratio. We do
NOT use any signal that requires data not stored historically per-date
(fundamentals/FII/sector/sentiment/macro/delivery/vcp) — those are simply absent
from this proxy and the result is honestly a technical-only score.
"""
from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.ranking import FundInputs, score_fundamental
from backend.agents.technical_indicators import ema, ema_cross_signal, macd, rsi

# Volume window sizes (sessions).
_AVG_VOL_DAYS = 30
_W52 = 252  # ~52-week trading days


def compute_score_from_history(
    closes: list[float], volumes: list[int] | None = None
) -> Decimal | None:
    """Decimal 0..100 mirroring `score_technical`. None if `closes` is too short.

    Inputs are series ENDING at the simulation date — the caller guarantees no
    future bars are included. The score is the same shape as the live ranking
    technical component so a comparison is meaningful; the absolute numbers will
    differ because the live composite adds fundamentals/macro/sentiment.
    """
    if len(closes) < 26 + 9:  # MACD slow + signal minimum
        return None

    rsi_14 = rsi(closes, 14)
    if rsi_14 is None:
        return None

    # 1) RSI zone base (matches ranking.py score_technical exactly).
    if rsi_14 < 30:
        score = 20.0
    elif rsi_14 < 45:
        score = 40.0
    elif rsi_14 < 55:
        score = 50.0
    elif rsi_14 < 65:
        score = 70.0
    elif rsi_14 < 75:
        score = 60.0
    else:
        score = 30.0

    # 2) EMA200 position (+15 above / -10 below; "at" = ±0.5% band).
    ema200 = ema(closes, 200)
    if ema200 is not None and ema200 > 0:
        last = closes[-1]
        if last > ema200 * 1.005:
            score += 15.0
        elif last < ema200 * 0.995:
            score -= 10.0
        # within 0.5% band -> "at", no change

    # 3) EMA 20/200 cross (+10 golden / -10 death).
    cross = ema_cross_signal(closes, short=20, long=200, lookback=20)
    if cross == "golden":
        score += 10.0
    elif cross == "death":
        score -= 10.0

    # 4) MACD histogram (+5 positive / -5 negative).
    _line, _sig, hist = macd(closes)
    if hist is not None:
        if hist > 0:
            score += 5.0
        elif hist < 0:
            score -= 5.0

    # 5) 52-week proximity (matches ranking.py thresholds).
    window = closes[-_W52:]
    if window:
        hi = max(window)
        lo = min(window)
        last = closes[-1]
        if hi > 0 and last / hi >= 0.97:
            if 55.0 <= rsi_14 <= 70.0:
                score += 8.0  # near high + healthy momentum
            elif rsi_14 > 70.0:
                score += 3.0  # extended but still strong
        if lo > 0 and last / lo <= 1.05:
            score -= 8.0  # near 52w low — value trap

    # 6) Volume trend (current vs 30d average).
    if volumes and len(volumes) >= _AVG_VOL_DAYS + 1:
        current = volumes[-1]
        avg30 = sum(volumes[-(_AVG_VOL_DAYS + 1) : -1]) / _AVG_VOL_DAYS
        if avg30 > 0:
            ratio = current / avg30
            if ratio >= 3:
                score += 10.0
            elif ratio >= 1.5:
                score += 5.0
            elif ratio <= 0.5:
                score -= 5.0

    score = max(0.0, min(100.0, score))
    return Decimal(str(round(score, 2)))


# ===========================================================================
# Week 2 — full F+T+M composite reconstruction (Chunk 5.2b).
#
# Mirrors the LIVE ranking weights (F 0.40 / T 0.35 / M 0.25) + a ±5 sector-
# momentum tilt. mle no-lookahead: fundamentals read by publication_date <= as_of
# (reporting-lag availability date); macro/sector by computed_date <= as_of
# (same-day observable). EVERY fetch asserts the row's date <= as_of. FII flows
# and news sentiment have NO per-date history, so they are held NEUTRAL (omitted)
# and documented — never fabricated.
# ===========================================================================
_Q2 = Decimal("0.01")
_NEUTRAL = Decimal("50")
_W_FUND = Decimal("0.40")
_W_TECH = Decimal("0.35")
_W_MACRO = Decimal("0.25")
_SECTOR_TILT = {
    "leading": Decimal("5"),
    "lagging": Decimal("-5"),
    "neutral": Decimal("0"),
}
_MACRO_INDICATORS = ("advance_decline_ratio", "pct_above_ema200", "new_high_low_ratio")

_SQL_FUND_ASOF = text(
    """
    SELECT f.publication_date, f.pe_ratio, f.roe, f.debt_to_equity,
           f.fcf, f.revenue_growth_yoy, s.sector
    FROM fundamental_signals_historical f
    JOIN stocks s ON s.isin = f.isin
    WHERE f.isin = :isin AND f.publication_date <= :as_of
    ORDER BY f.publication_date DESC
    LIMIT 1
    """
)
_SQL_MACRO_ASOF = text(
    """
    SELECT computed_date, value
    FROM macro_signals_historical
    WHERE indicator = :indicator AND computed_date <= :as_of
    ORDER BY computed_date DESC
    LIMIT 1
    """
)
_SQL_SECTOR_ASOF = text(
    """
    SELECT h.computed_date, h.classification
    FROM sector_signals_historical h
    JOIN stocks s ON s.sector = h.sector
    WHERE s.isin = :isin AND h.computed_date <= :as_of
    ORDER BY h.computed_date DESC
    LIMIT 1
    """
)


def _ad_subscore(v: Decimal) -> Decimal:
    """advance/decline ratio (>1 = more advancers) -> 0..100 breadth sub-score."""
    if v >= Decimal("2.0"):
        return Decimal("80")
    if v >= Decimal("1.5"):
        return Decimal("70")
    if v >= Decimal("1.0"):
        return Decimal("55")
    if v >= Decimal("0.7"):
        return Decimal("45")
    if v >= Decimal("0.4"):
        return Decimal("35")
    return Decimal("20")


def _pct_above_subscore(v: Decimal) -> Decimal:
    """% of stocks above EMA200 is already a 0..100 reading — clamp and use as-is."""
    return max(Decimal("0"), min(Decimal("100"), v))


def _nhl_subscore(v: Decimal) -> Decimal:
    """new-high / new-low ratio (>1 = more highs) -> 0..100 breadth sub-score."""
    if v >= Decimal("3.0"):
        return Decimal("80")
    if v >= Decimal("1.5"):
        return Decimal("65")
    if v >= Decimal("1.0"):
        return Decimal("55")
    if v >= Decimal("0.5"):
        return Decimal("40")
    return Decimal("25")


_SUBSCORE = {
    "advance_decline_ratio": _ad_subscore,
    "pct_above_ema200": _pct_above_subscore,
    "new_high_low_ratio": _nhl_subscore,
}


async def reconstruct_fundamental_score(
    session: AsyncSession, isin: str, as_of: date
) -> Decimal | None:
    """Latest pre-cutoff fundamental score (0..100), or None if no row exists.

    Reuses the LIVE `score_fundamental` so the reconstruction is identical to what
    the ranker would have produced (sector-fair-PE path included). Stored units
    are converted to the live contract: `debt_to_equity` is a RATIO historically
    but the live formula expects yfinance percent (divides by 100), so it is
    multiplied by 100 here; `roe`/`revenue_growth` are fractions and `pe_ratio`
    is absolute, matching live. no-lookahead: SQL `publication_date <= as_of` +
    a defensive assert.
    """
    row = (
        await session.execute(_SQL_FUND_ASOF, {"isin": isin, "as_of": as_of})
    ).first()
    if row is None:
        return None
    pub, pe, roe, de, fcf, rev, sector = row
    assert pub <= as_of, f"lookahead: fundamentals pub {pub} > as_of {as_of}"
    fund = FundInputs(
        pe_ratio=None if pe is None else Decimal(pe),
        roe=None if roe is None else Decimal(roe),
        debt_to_equity=None if de is None else Decimal(de) * 100,
        revenue_growth=None if rev is None else Decimal(rev),
        fcf_positive=None if fcf is None else (Decimal(fcf) > 0),
        sector=sector or "",
    )
    return score_fundamental(fund)


async def reconstruct_macro_score(session: AsyncSession, as_of: date) -> Decimal:
    """Breadth-derived macro score (0..100): mean of three 1/3-weight breadth
    sub-scores (advance/decline, % above EMA200, new-high/low ratio).

    FII flows and news sentiment have NO per-date history, so they are held
    NEUTRAL (omitted) rather than fabricated — this is an honest breadth-only
    macro proxy. A missing indicator row falls back to neutral 50. no-lookahead:
    SQL `computed_date <= as_of` + a defensive assert per indicator.
    """
    subs: list[Decimal] = []
    for ind in _MACRO_INDICATORS:
        row = (
            await session.execute(
                _SQL_MACRO_ASOF, {"indicator": ind, "as_of": as_of}
            )
        ).first()
        if row is None:
            subs.append(_NEUTRAL)
            continue
        cd, val = row
        assert cd <= as_of, f"lookahead: macro {ind} {cd} > as_of {as_of}"
        subs.append(_NEUTRAL if val is None else _SUBSCORE[ind](Decimal(val)))
    macro = sum(subs, Decimal("0")) / Decimal(len(subs))
    return max(Decimal("0"), min(Decimal("100"), macro)).quantize(
        _Q2, rounding=ROUND_HALF_EVEN
    )


async def reconstruct_sector_signal(
    session: AsyncSession, isin: str, as_of: date
) -> str:
    """Latest pre-cutoff sector-momentum class for the stock's sector.

    Returns 'leading' | 'neutral' | 'lagging'; 'neutral' when no row exists (very
    early dates before sector history begins). no-lookahead: SQL
    `computed_date <= as_of` + a defensive assert.
    """
    row = (
        await session.execute(_SQL_SECTOR_ASOF, {"isin": isin, "as_of": as_of})
    ).first()
    if row is None:
        return "neutral"
    cd, classification = row
    assert cd <= as_of, f"lookahead: sector {cd} > as_of {as_of}"
    return classification or "neutral"


async def compute_full_composite(
    session: AsyncSession,
    isin: str,
    as_of: date,
    closes: list[float],
    volumes: list[int] | None = None,
    *,
    macro_score: Decimal | None = None,
    sector_signal: str | None = None,
) -> Decimal | None:
    """Full F+T+M composite (0..100) for one stock at `as_of`.

    Mirrors the live ranking weights (F 0.40 / T 0.35 / M 0.25) plus a ±5
    sector-momentum tilt, clamped 0..100. Returns None when the technical score is
    None (insufficient price history / warmup) — the runner then skips the stock,
    exactly as the technical-only baseline does; we never fabricate a score for a
    stock we cannot technically rate. Missing fundamentals fall back to neutral 50
    (the live ranker's base).

    `macro_score` / `sector_signal` may be supplied pre-computed (the runner
    fetches macro once per date and sector classes in one batched query per date,
    avoiding N identical queries); when omitted they are fetched here.
    """
    t = compute_score_from_history(closes, volumes)
    if t is None:
        return None
    f = await reconstruct_fundamental_score(session, isin, as_of)
    if f is None:
        f = _NEUTRAL
    m = (
        macro_score
        if macro_score is not None
        else await reconstruct_macro_score(session, as_of)
    )
    sig = (
        sector_signal
        if sector_signal is not None
        else await reconstruct_sector_signal(session, isin, as_of)
    )
    composite = t * _W_TECH + f * _W_FUND + m * _W_MACRO
    composite += _SECTOR_TILT.get(sig, Decimal("0"))
    composite = max(Decimal("0"), min(Decimal("100"), composite))
    return composite.quantize(_Q2, rounding=ROUND_HALF_EVEN)
