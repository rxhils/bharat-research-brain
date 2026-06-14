"""Per-date score reconstructor — momentum + trend filter (FIX 3+4).

mle no-lookahead invariant: every score is computed from `closes`/`volumes` whose
last bar is the simulation date D. The caller MUST pass series ending at D and
nothing past it; the engine cannot tell the difference, so the runner enforces
this with `WHERE trade_date <= :as_of` in the SQL fetch.

Primary signal (60% weight):
    52-week relative strength vs Nifty 50 proxy
    Stock return over 252 days minus Nifty return over 252 days
    Higher relative strength = higher score

Secondary signal (40% weight):
    Existing technicals (RSI zone, EMA200 position, EMA cross, MACD, volume)

Hard filter (FIX 4):
    Price < 200-day EMA → score = 0 (never buy downtrends)

Only stocks in TOP 20% by 52-week relative strength can score above 50.
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

# Weights (kept as floats; the composite is float math)
_W_MOMENTUM = 0.60
_W_TECH = 0.40

# Nifty 50 proxy — same 10 ISINs as runner.py for consistency
_NIFTY_PROXY_ISINS = {
    "INE002A01018",  # RELIANCE
    "INE467B01029",  # TCS
    "INE040A01034",  # HDFCBANK
    "INE009A01021",  # INFY
    "INE090A01021",  # ICICIBANK
    "INE030A01027",  # HINDUNILVR
    "INE238A01034",  # AXISBANK
    "INE237A01036",  # KOTAKBANK
    "INE296A01032",  # BAJFINANCE
    "INE062A01020",  # SBIN
}


def _compute_nifty_return(closes_by_isin: dict[str, list[float]]) -> float | None:
    """Equal-weighted 252-day return of the Nifty 50 proxy basket.

    Returns None if fewer than 3 proxy ISINs have data.
    """
    returns: list[float] = []
    for isin, series in closes_by_isin.items():
        if isin not in _NIFTY_PROXY_ISINS or len(series) < _W52 + 1:
            continue
        ret = (series[-1] - series[-_W52]) / series[-_W52]
        returns.append(ret)
    if len(returns) < 3:
        return None
    return sum(returns) / len(returns)


def compute_score_from_history(
    closes: list[float],
    volumes: list[int] | None = None,
    *,
    all_closes: dict[str, list[float]] | None = None,
) -> Decimal | None:
    """Decimal 0..100 with momentum-primary scoring.

    Inputs are series ENDING at the simulation date — the caller guarantees no
    future bars are included.

    Signature compatible with the runner's existing call site. The optional
    `all_closes` parameter provides the full isin->closes map so the Nifty
    proxy return can be computed; when omitted (legacy call), momentum ranking
    is approximated from the 52-week return of a synthetic "market average".

    FIX 4 — Hard trend filter: if price < 200-day EMA, score = 0.
    """
    if len(closes) < 200:  # need at least 200 bars for EMA200
        return None

    # ---- FIX 4: Trend filter (non-negotiable) -------------------------------
    ema200 = ema(closes, 200)
    if ema200 is None or closes[-1] < ema200:
        return Decimal("0")
    # -------------------------------------------------------------------------

    rsi_14 = rsi(closes, 14)
    if rsi_14 is None:
        return None

    # ---- Momentum score (60% weight) ----------------------------------------
    # 52-week return of this stock
    stock_ret = (closes[-1] - closes[-_W52]) / closes[-_W52] if len(closes) > _W52 else 0.0

    # 52-week return of the Nifty proxy (or fallback to mean of all stocks)
    nifty_ret = _compute_nifty_return(all_closes) if all_closes is not None else None
    if nifty_ret is None:
        # Fallback: use the average 52-week return of all available stocks as
        # a pseudo-benchmark (not as good as Nifty, but still relative).
        stock_returns: list[float] = []
        if all_closes:
            for s in all_closes.values():
                if len(s) >= _W52 + 1:
                    stock_returns.append((s[-1] - s[-_W52]) / s[-_W52])
        if not stock_returns:
            stock_returns = [stock_ret]
        nifty_ret = sum(stock_returns) / len(stock_returns)

    # Relative strength alpha
    rs_alpha = stock_ret - nifty_ret

    # Map relative strength to a 0..100 momentum score
    # rs_alpha of +50% → 100, 0% → 50, -50% → 0 (linear map)
    momentum_score = 50.0 + (rs_alpha * 100.0)
    momentum_score = max(0.0, min(100.0, momentum_score))
    # -------------------------------------------------------------------------

    # ---- Secondary: technical score (40% weight) ----------------------------
    # 1) RSI zone base
    if rsi_14 < 30:
        tech_score = 20.0
    elif rsi_14 < 45:
        tech_score = 40.0
    elif rsi_14 < 55:
        tech_score = 50.0
    elif rsi_14 < 65:
        tech_score = 70.0
    elif rsi_14 < 75:
        tech_score = 60.0
    else:
        tech_score = 30.0

    # 2) EMA200 position (+15 above / -10 below)
    if ema200 > 0:
        last = closes[-1]
        if last > ema200 * 1.005:
            tech_score += 15.0
        elif last < ema200 * 0.995:
            tech_score -= 10.0

    # 3) EMA 20/200 cross (+10 golden / -10 death)
    cross = ema_cross_signal(closes, short=20, long=200, lookback=20)
    if cross == "golden":
        tech_score += 10.0
    elif cross == "death":
        tech_score -= 10.0

    # 4) MACD histogram (+5 positive / -5 negative)
    _line, _sig, hist = macd(closes)
    if hist is not None:
        if hist > 0:
            tech_score += 5.0
        elif hist < 0:
            tech_score -= 5.0

    # 5) 52-week proximity
    window = closes[-_W52:]
    if window:
        hi = max(window)
        lo = min(window)
        last = closes[-1]
        if hi > 0 and last / hi >= 0.97:
            if 55.0 <= rsi_14 <= 70.0:
                tech_score += 8.0
            elif rsi_14 > 70.0:
                tech_score += 3.0
        if lo > 0 and last / lo <= 1.05:
            tech_score -= 8.0

    # 6) Volume trend
    if volumes and len(volumes) >= _AVG_VOL_DAYS + 1:
        current = volumes[-1]
        avg30 = sum(volumes[-(_AVG_VOL_DAYS + 1): -1]) / _AVG_VOL_DAYS
        if avg30 > 0:
            ratio = current / avg30
            if ratio >= 3:
                tech_score += 10.0
            elif ratio >= 1.5:
                tech_score += 5.0
            elif ratio <= 0.5:
                tech_score -= 5.0

    tech_score = max(0.0, min(100.0, tech_score))
    # -------------------------------------------------------------------------

    # Composite: 60% momentum + 40% technical
    composite = float(momentum_score * _W_MOMENTUM + tech_score * _W_TECH)
    composite = max(0.0, min(100.0, composite))

    # FIX 4 bonus: only stocks in TOP 20% relative strength can score above 50.
    # This ensures we're really picking the strongest, not lucky stocks.
    if all_closes is not None and len(all_closes) > 5:
        # Compute percentile of this stock's relative strength
        all_alphas: list[float] = []
        for isin, s in all_closes.items():
            if len(s) >= _W52 + 1 and isin not in _NIFTY_PROXY_ISINS:
                r = (s[-1] - s[-_W52]) / s[-_W52]
                all_alphas.append(r - nifty_ret)
        if all_alphas:
            # How does this stock rank? Top 20% = alpha >= 80th percentile
            all_alphas.sort(reverse=True)
            threshold_idx = max(1, int(len(all_alphas) * 0.20))
            threshold = all_alphas[threshold_idx - 1]
            if rs_alpha < threshold:
                composite = min(composite, 50.0)

    return Decimal(str(round(composite, 2)))


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
_W_TECH_FT = Decimal("0.35")
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
    composite = t * _W_TECH_FT + f * _W_FUND + m * _W_MACRO
    composite += _SECTOR_TILT.get(sig, Decimal("0"))
    composite = max(Decimal("0"), min(Decimal("100"), composite))
    return composite.quantize(_Q2, rounding=ROUND_HALF_EVEN)
